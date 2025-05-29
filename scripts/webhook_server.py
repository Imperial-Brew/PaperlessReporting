from flask import Flask, request, jsonify
import requests
import csv
import os
import logging
from scripts.utils.config_loader import get

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# === Configuration ===
API_TOKEN = os.getenv(
    "PAPERLESS_API_TOKEN",
    get("api_key", "SET_ME")
)
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    get("webhook_secret", "supersecret")
)
# Use absolute paths to project root directory
from pathlib import Path
project_root = Path(__file__).parent.parent
CSV_FILE = str(project_root / "data_raw/quotes_live.csv")
ORDERS_CSV_FILE = str(project_root / "data_raw/orders_live.csv")

# Log configuration on startup
logger.info("=== Webhook Server Starting ===")
logger.info(f"Webhook Secret: {WEBHOOK_SECRET[:4]}...")
logger.info(f"API Token: {API_TOKEN[:4]}...")
logger.info(f"API Base URL: {get('api_base_url', 'Not Set')}")
logger.info("=============================")

# === Helper: Write quote to CSV ===
def update_csv(row, csv_file=CSV_FILE):
    """Update the CSV file with new data."""
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

# === Helper: Write order to CSV ===
def update_order_csv(row):
    """Update the orders CSV file with new data."""
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

# === Helper: Call Paperless API for full quote info ===
def fetch_and_save_quote(quote_number, revision_number):
    """Fetch quote details from Paperless API and save to CSV."""
    url = f"{get('api_base_url')}/quotes/public/{quote_number}?revision={revision_number}"
    headers = {"Authorization": f"API-Token {API_TOKEN}"}
    logger.info(f"Fetching quote from: {url}")

    response = requests.get(url, headers=headers)
    logger.info(f"API Response Status: {response.status_code}")

    if response.status_code != 200:
        logger.error(
            f"❌ Failed to fetch quote {quote_number} Rev {revision_number}: "
            f"{response.status_code}"
        )
        logger.error(f"Response content: {response.text}")
        return

    quote = response.json()
    row = {
        "quote_number": quote.get("quote_number"),
        "revision_number": quote.get("revision_number"),
        "status": quote.get("status"),
        "created": quote.get("created"),
        "due_date": quote.get("due_date"),
        "rfq_number": quote.get("rfq_number"),
        "priority": quote.get("priority"),
        "private_notes": quote.get("private_notes"),
        "contact_name": quote.get("contact", {}).get("name", ""),
        "contact_email": quote.get("contact", {}).get("email", ""),
        "customer_name": quote.get("customer", {}).get("name", ""),
        "estimator_email": quote.get("estimator", {}).get("email", ""),
        "salesperson_email": quote.get("salesperson", {}).get("email", "")
    }

    update_csv(row)

# === Helper: Call Paperless API for full order info ===
def fetch_and_save_order(order_number):
    """Fetch order details from Paperless API and save to CSV."""
    url = f"{get('api_base_url')}/orders/public/{order_number}"
    headers = {"Authorization": f"API-Token {API_TOKEN}"}
    logger.info(f"Fetching order from: {url}")

    response = requests.get(url, headers=headers)
    logger.info(f"API Response Status: {response.status_code}")

    if response.status_code != 200:
        logger.error(
            f"❌ Failed to fetch order {order_number}: {response.status_code}"
        )
        logger.error(f"Response content: {response.text}")
        return

    order = response.json()
    row = {
        "order_number": order.get("order_number"),
        "status": order.get("status"),
        "created": order.get("created"),
        "due_date": order.get("due_date"),
        "quote_number": order.get("quote", {}).get("quote_number"),
        "quote_revision": order.get("quote", {}).get("revision_number"),
        "customer_name": order.get("customer", {}).get("name", ""),
        "contact_name": order.get("contact", {}).get("name", ""),
        "contact_email": order.get("contact", {}).get("email", ""),
        "salesperson_email": order.get("salesperson", {}).get("email", "")
    }

    update_order_csv(row)

# === Webhook Event Handlers ===
def handle_quote_created(data):
    """Handle quote.created event."""
    quote_number = data.get("number")
    if not quote_number:
        logger.warning("⚠️ Missing quote_number in created event")
        return False

    # Use a default revision number (1) if not provided
    revision_number = data.get("revision_number")
    if revision_number is None:
        revision_number = 1
        logger.info(f"Using default revision number 1 for quote {quote_number}")

    fetch_and_save_quote(quote_number, revision_number)
    return True

def handle_quote_status_changed(data):
    """Handle quote.status_changed event."""
    quote_number = data.get("quote_number")
    revision_number = data.get("revision_number")
    if not quote_number or not revision_number:
        logger.warning(
            "⚠️ Missing quote_number or revision_number in status_changed event"
        )
        return False
    fetch_and_save_quote(quote_number, revision_number)
    return True

def handle_quote_sent(data):
    """Handle quote.sent event."""
    quote_number = data.get("quote_number")
    revision_number = data.get("revision_number")
    if not quote_number or not revision_number:
        logger.warning(
            "⚠️ Missing quote_number or revision_number in sent event"
        )
        return False
    fetch_and_save_quote(quote_number, revision_number)
    return True

def handle_order_created(data):
    """Handle order.created event."""
    order_number = data.get("order_number")
    if not order_number:
        logger.warning("⚠️ Missing order_number in created event")
        return False
    fetch_and_save_order(order_number)
    return True

def handle_order_status_changed(data):
    """Handle order.status_changed event."""
    order_number = data.get("order_number")
    if not order_number:
        logger.warning("⚠️ Missing order_number in status_changed event")
        return False
    fetch_and_save_order(order_number)
    return True

# === Route: Handle Webhook POST ===
@app.route("/webhook", methods=["POST"])
def webhook():
    """Handle incoming webhook requests."""
    logger.info("=== New Webhook Request ===")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Args: {dict(request.args)}")

    token = request.args.get("token")
    if token != WEBHOOK_SECRET:
        logger.warning(f"⚠️ Invalid webhook token. Received: {token}")
        return "Forbidden", 403

    try:
        data = request.get_json(force=True)
    except Exception as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        logger.error(f"Raw body: {request.data}")
        return "Invalid JSON", 400

    logger.info("📥 Webhook payload received:")
    logger.info(data)

    event_type = data.get("type")
    event_data = data.get("data", {})

    handlers = {
        "quote.created": handle_quote_created,
        "quote.status_changed": handle_quote_status_changed,
        "quote.sent": handle_quote_sent,
        "order.created": handle_order_created,
        "order.status_changed": handle_order_status_changed
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.warning(f"⚠️ Unsupported event type: {event_type}")
        return "Unsupported event type", 400

    success = handler(event_data)
    if not success:
        return "Invalid event data", 400

    logger.info("✅ Webhook processed successfully")
    return jsonify({"status": "OK"}), 200

# === Health Check Endpoint ===
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "OK"}), 200

if __name__ == "__main__":
    # Create data directories if they don't exist
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(ORDERS_CSV_FILE), exist_ok=True)

    # Start the server
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port) 
