from flask import Flask, request, jsonify, Response
import requests
import csv
import os
import logging
import hmac
import hashlib
import json
from scripts.utils.config_loader import get
from scripts.utils.s3_helpers import upload_to_s3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebhookServer:
    """
    Webhook server class that handles incoming webhook events.
    This class is used by the tests in test_webhook_server.py.
    """

    def __init__(self, webhook_secret=None, app=None):
        """Initialize the webhook server with the given secret."""
        self.app = app
        self.webhook_secret = webhook_secret or os.getenv(
            "WEBHOOK_SECRET",
            get("webhook_secret", "supersecret")
        )

        # Event handlers
        if self.app:
            self.app.config['event_handlers'] = {}

    def index(self):
        """Root endpoint that returns basic information about the API."""
        return jsonify({
            "name": "Paperless Parts Webhook Server",
            "version": "1.0.0",
            "endpoints": ["/", "/health", "/webhook"]
        })

    def health(self):
        """Health check endpoint for monitoring."""
        return "OK"

    def webhook(self):
        """
        Webhook endpoint that processes events from Paperless Parts.
        Supports authentication via token parameter or X-Webhook-Signature header.
        """
        logger.info("=== New Webhook Request ===")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Args: {dict(request.args)}")

        # Authentication - support both methods
        is_authenticated = False

        # Method 1: Check token parameter (URL query parameter)
        token = request.args.get('token')
        if token == self.webhook_secret:
            is_authenticated = True
            logger.info("✅ Authenticated via token parameter")

        # Method 2: Check X-Webhook-Signature header
        signature = request.headers.get('X-Webhook-Signature')
        if signature and not is_authenticated:
            # Verify the signature
            if request.data:
                expected_signature = hmac.new(
                    self.webhook_secret.encode(),
                    request.data,
                    hashlib.sha256
                ).hexdigest()

                if signature == expected_signature:
                    is_authenticated = True
                    logger.info("✅ Authenticated via X-Webhook-Signature header")

        # If not authenticated by either method, return 401
        if not is_authenticated:
            logger.warning(f"⚠️ Invalid webhook token. Received: {token}")
            return Response("Unauthorized", status=401)

        # Parse the request body
        try:
            if not request.data:
                logger.warning("⚠️ Empty request body")
                return Response("Empty request body", status=400)

            data = request.json
            if not data:
                logger.warning("⚠️ Invalid JSON in request body")
                return Response("Invalid JSON", status=400)

            # Check for event type
            event_type = data.get('type')
            if not event_type:
                logger.warning("⚠️ Missing event type in webhook payload")
                return Response("Missing event type", status=400)

            logger.info(f"📥 Received webhook event: {event_type}")

            # Check if we have a handler for this event type
            event_handlers = {}
            if self.app:
                event_handlers = self.app.config.get('event_handlers', {})

            if event_type in event_handlers:
                # Use the registered handler
                try:
                    handler = event_handlers[event_type]
                    handler(data)
                    return Response("OK", status=200)
                except Exception as e:
                    logger.error(f"❌ Error in event handler: {str(e)}")
                    return Response("Internal server error", status=500)

            # Handle different event types with default handlers
            if event_type == 'quote.status_changed':
                handle_quote_status_changed(data.get('data', {}))
            elif event_type == 'quote.created':
                # Handle quote.created events the same way as quote.status_changed
                logger.info(f"Processing quote creation: {data}")
                handle_quote_status_changed(data.get('data', {}))
            elif event_type == 'order.status_changed':
                handle_order_status_changed(data.get('data', {}))
            elif event_type == 'order.created':
                # Handle order.created events the same way as order.status_changed
                logger.info(f"Processing order creation: {data}")
                handle_order_status_changed(data.get('data', {}))
            else:
                logger.warning(f"⚠️ Unsupported event type: {event_type}")
                return Response("Unsupported event type", status=400)

            return Response("OK", status=200)

        except Exception as e:
            logger.error(f"❌ Error processing webhook: {str(e)}")
            return Response("Internal server error", status=500)

# Create the webhook server instance without a Flask app
# The Flask app will be created in app.py and passed to the webhook server
webhook_server = WebhookServer()

# === Configuration ===
API_TOKEN = os.getenv(
    "PAPERLESS_API_TOKEN",
    get("api_key", "SET_ME")
)
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    get("webhook_secret", "supersecret")
)
# Use platform-independent paths relative to project root
from pathlib import Path
import sys

# Determine project root directory
try:
    project_root = Path(__file__).parent.parent
    logger.info(f"Script directory: {Path(__file__).parent}")
    logger.info(f"Calculated project root: {project_root}")

    data_dir = project_root / "data_raw"
    logger.info(f"Checking if data directory exists: {data_dir}")

    if not data_dir.exists() and not data_dir.parent.exists():
        project_root = Path.cwd()
        logger.info(f"Using current working directory as project root: {project_root}")
    else:
        logger.info(f"Using script location as project root: {project_root}")
except Exception as e:
    logger.error(f"Error determining project root: {str(e)}")
    project_root = Path.cwd()
    logger.info(f"Using current working directory as project root: {project_root}")

logger.info(f"Project root before path construction: {project_root}")
logger.info(f"Project root type: {type(project_root)}")

if not isinstance(project_root, Path):
    logger.warning(f"project_root is not a Path object, converting from {type(project_root)}")
    project_root = Path(str(project_root))

data_raw_dir = os.path.join(str(project_root), "data_raw")
CSV_FILE = os.path.join(data_raw_dir, "quotes_live.csv")
ORDERS_CSV_FILE = os.path.join(data_raw_dir, "orders_live.csv")

logger.info(f"Data raw directory: {data_raw_dir}")
logger.info(f"CSV file path: {CSV_FILE}")
logger.info(f"Orders CSV file path: {ORDERS_CSV_FILE}")

try:
    csv_dir = os.path.dirname(CSV_FILE)
    orders_dir = os.path.dirname(ORDERS_CSV_FILE)

    logger.info(f"CSV directory path: {csv_dir}")
    logger.info(f"Orders directory path: {orders_dir}")

    if not csv_dir or csv_dir == "":
        logger.warning(f"CSV directory path is empty, using current directory")
        csv_dir = "."
        CSV_FILE = os.path.join(csv_dir, "quotes_live.csv")
        logger.info(f"Updated CSV file path: {CSV_FILE}")

    if not orders_dir or orders_dir == "":
        logger.warning(f"Orders directory path is empty, using current directory")
        orders_dir = "."
        ORDERS_CSV_FILE = os.path.join(orders_dir, "orders_live.csv")
        logger.info(f"Updated Orders CSV file path: {ORDERS_CSV_FILE}")

    try:
        if csv_dir and csv_dir != "":
            os.makedirs(csv_dir, exist_ok=True)
            logger.info(f"Created directory: {csv_dir}")
        else:
            logger.warning("Skipping creation of CSV directory as path is empty")
    except Exception as csv_dir_error:
        logger.error(f"Error creating CSV directory: {str(csv_dir_error)}")
        CSV_FILE = "quotes_live.csv"
        logger.info(f"Falling back to current directory for CSV file: {CSV_FILE}")

    try:
        if orders_dir and orders_dir != "":
            os.makedirs(orders_dir, exist_ok=True)
            logger.info(f"Created directory: {orders_dir}")
        else:
            logger.warning("Skipping creation of Orders directory as path is empty")
    except Exception as orders_dir_error:
        logger.error(f"Error creating Orders directory: {str(orders_dir_error)}")
        ORDERS_CSV_FILE = "orders_live.csv"
        logger.info(f"Falling back to current directory for Orders CSV file: {ORDERS_CSV_FILE}")

except Exception as e:
    logger.error(f"Error in directory setup: {str(e)}")
    CSV_FILE = "quotes_live.csv"
    ORDERS_CSV_FILE = "orders_live.csv"
    logger.info(f"Falling back to current directory for CSV files: {CSV_FILE} and {ORDERS_CSV_FILE}")

logger.info("=== Webhook Server Starting ===")
logger.info(f"Webhook Secret: {WEBHOOK_SECRET[:4]}...")
logger.info(f"API Token: {API_TOKEN[:4]}...")
logger.info(f"API Base URL: {get('api_base_url', 'Not Set')}")
logger.info("=============================")

# === Helper: Write quote to CSV ===
def update_csv(row, csv_file=CSV_FILE):
    """Update the CSV file with new data and upload to S3."""
    file_exists = os.path.isfile(csv_file)
    fieldnames = [
        "quote_number",
        "revision_number",
        "status",
        "created",
        "due_date",
        "rfq_number",
        "priority",
        "private_notes",
        "contact_name",
        "contact_email",
        "customer_name",
        "estimator_email",
        "salesperson_email"
    ]

    existing = []
    if file_exists:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing = [
                r for r in reader
                if r["quote_number"] != row["quote_number"]
                or r["revision_number"] != row["revision_number"]
            ]

    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        writer.writerow(row)

    logger.info(
        f"✅ Quote {row['quote_number']} Rev {row['revision_number']} written to CSV."
    )
    # Upload to S3
    upload_to_s3(csv_file)

# === Helper: Write order to CSV ===
def update_order_csv(row):
    """Update the orders CSV file with new data and upload to S3."""
    file_exists = os.path.isfile(ORDERS_CSV_FILE)
    fieldnames = [
        "order_number",
        "status",
        "created",
        "due_date",
        "quote_number",
        "quote_revision",
        "customer_name",
        "contact_name",
        "contact_email",
        "salesperson_email"
    ]

    existing = []
    if file_exists:
        with open(ORDERS_CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing = [
                r for r in reader
                if r["order_number"] != row["order_number"]
            ]

    with open(ORDERS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        writer.writerow(row)

    logger.info(f"✅ Order {row['order_number']} written to CSV.")
    # Upload to S3
    upload_to_s3(ORDERS_CSV_FILE)

# === Handler functions for WebhookServer ===
# Note: Routes are registered in app.py

def handle_quote_status_changed(data):
    """Handle quote.status_changed events."""
    logger.info(f"Processing quote status change: {data}")

    # Extract quote data
    quote_number = data.get('quote_number')
    revision_number = data.get('revision_number')
    status = data.get('status')

    if not all([quote_number, revision_number, status]):
        logger.warning(f"⚠️ Missing required fields in quote data: {data}")
        return

    # Update CSV with quote data
    row = {
        "quote_number": quote_number,
        "revision_number": revision_number,
        "status": status,
        "created": data.get('created', ''),
        "due_date": data.get('due_date', ''),
        "rfq_number": data.get('rfq_number', ''),
        "priority": data.get('priority', ''),
        "private_notes": data.get('private_notes', ''),
        "contact_name": data.get('contact_name', ''),
        "contact_email": data.get('contact_email', ''),
        "customer_name": data.get('customer_name', ''),
        "estimator_email": data.get('estimator_email', ''),
        "salesperson_email": data.get('salesperson_email', '')
    }

    update_csv(row)

def handle_order_status_changed(data):
    """Handle order.status_changed events."""
    logger.info(f"Processing order status change: {data}")

    # Extract order data
    order_number = data.get('order_number')
    status = data.get('status')

    if not all([order_number, status]):
        logger.warning(f"⚠️ Missing required fields in order data: {data}")
        return

    # Update CSV with order data
    row = {
        "order_number": order_number,
        "status": status,
        "created": data.get('created', ''),
        "due_date": data.get('due_date', ''),
        "quote_number": data.get('quote_number', ''),
        "quote_revision": data.get('quote_revision', ''),
        "customer_name": data.get('customer_name', ''),
        "contact_name": data.get('contact_name', ''),
        "contact_email": data.get('contact_email', ''),
        "salesperson_email": data.get('salesperson_email', '')
    }

    update_order_csv(row)

# Routes are logged in app.py

if __name__ == "__main__":
    # Create a Flask app if running this file directly
    from flask import Flask
    app = Flask(__name__)

    # Register routes
    app.add_url_rule('/', 'index', webhook_server.index)
    app.add_url_rule('/health', 'health', webhook_server.health)
    app.add_url_rule('/webhook', 'webhook', webhook_server.webhook, methods=['POST'])

    # Set the app for the webhook server
    webhook_server.app = app

    # Run the app
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
