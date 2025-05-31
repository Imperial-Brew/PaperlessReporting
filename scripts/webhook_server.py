from flask import Flask, request, jsonify, Response
import requests
import csv
import os
import hmac
import hashlib
import json
import traceback
from scripts.utils.config_loader import get
from scripts.utils.s3_helpers import upload_to_s3
from scripts.utils.utils import safe_get
from scripts.utils.logging_config import get_logger, with_correlation_id, LogContext
from scripts.utils.exceptions import (
    WebhookError, WebhookAuthenticationError, WebhookValidationError,
    S3Error, S3UploadError, DataProcessingError
)

# Get logger for this module
logger = get_logger(__name__)

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

    @with_correlation_id
    def webhook(self):
        """
        Webhook endpoint that processes events from Paperless Parts.
        Supports authentication via token parameter or X-Webhook-Signature header.
        """
        # Create a context with webhook-specific information
        with LogContext(endpoint="webhook"):
            logger.info("=== New Webhook Request ===")
            logger.debug(f"Headers: {dict(request.headers)}")
            logger.debug(f"Args: {dict(request.args)}")

            try:
                # Authenticate the request
                self._authenticate_webhook()

                # Parse and validate the request body
                data = self._parse_webhook_payload()

                # Process the webhook event
                return self._process_webhook_event(data)

            except WebhookAuthenticationError as e:
                logger.warning(f"Authentication failed: {e.message}", extra={"details": e.details})
                return Response("Unauthorized", status=401)

            except WebhookValidationError as e:
                logger.warning(f"Validation failed: {e.message}", extra={"details": e.details})
                return Response(e.message, status=400)

            except WebhookError as e:
                logger.error(f"Webhook processing error: {e.message}", extra={"details": e.details})
                return Response("Error processing webhook", status=500)

            except Exception as e:
                # Catch any unexpected exceptions
                error_details = {
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
                logger.error(f"Unexpected error processing webhook: {str(e)}", extra={"details": error_details})
                return Response("Internal server error", status=500)

    def _authenticate_webhook(self):
        """
        Authenticate the webhook request using token or signature.

        Raises:
            WebhookAuthenticationError: If authentication fails
        """
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

        # If not authenticated by either method, raise exception
        if not is_authenticated:
            details = {
                "received_token": token[:4] + "..." if token else None,
                "has_signature": bool(signature)
            }
            raise WebhookAuthenticationError("Invalid webhook authentication", details=details)

    def _parse_webhook_payload(self):
        """
        Parse and validate the webhook payload.

        Returns:
            dict: The parsed webhook data

        Raises:
            WebhookValidationError: If the payload is invalid
        """
        if not request.data:
            raise WebhookValidationError("Empty request body")

        try:
            data = request.json
        except Exception as e:
            raise WebhookValidationError(f"Invalid JSON in request body: {str(e)}")

        if not data:
            raise WebhookValidationError("Empty JSON payload")

        # Check for event type
        event_type = data.get('type')
        if not event_type:
            raise WebhookValidationError("Missing event type in webhook payload")

        logger.info(f"📥 Received webhook event: {event_type}")
        return data

    def _process_webhook_event(self, data):
        """
        Process the webhook event based on its type.

        Args:
            data: The parsed webhook data

        Returns:
            Response: HTTP response

        Raises:
            WebhookError: If processing fails
        """
        event_type = data.get('type')

        # Add event type to logging context
        with LogContext(event_type=event_type):
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
                    error_details = {
                        "exception": str(e),
                        "traceback": traceback.format_exc()
                    }
                    raise WebhookError(f"Error in event handler: {str(e)}", details=error_details)

            # Handle different event types with default handlers
            try:
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
                    raise WebhookValidationError(f"Unsupported event type: {event_type}")

                return Response("OK", status=200)

            except WebhookValidationError:
                # Re-raise validation errors
                raise
            except Exception as e:
                # Wrap other exceptions in WebhookError
                error_details = {
                    "exception": str(e),
                    "traceback": traceback.format_exc(),
                    "event_type": event_type,
                    "data": data
                }
                raise WebhookError(f"Error processing webhook event: {str(e)}", details=error_details)

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
@with_correlation_id
def update_csv(row, csv_file=CSV_FILE):
    """
    Update the CSV file with new data and upload to S3.

    Args:
        row: Quote data to write
        csv_file: Path to the CSV file

    Raises:
        DataProcessingError: If there's an error processing the data
        S3UploadError: If there's an error uploading to S3
    """
    try:
        # Add context information to logs
        with LogContext(operation="update_csv", quote_number=row.get("quote_number"), revision=row.get("revision_number")):
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

            # Validate required fields
            for field in ["quote_number", "revision_number"]:
                if not row.get(field):
                    raise DataProcessingError(f"Missing required field: {field}", details={"row": row})

            # Read existing data
            existing = []
            try:
                if os.path.isfile(csv_file):
                    with open(csv_file, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        existing = [
                            r for r in reader
                            if r["quote_number"] != row["quote_number"]
                            or r["revision_number"] != row["revision_number"]
                        ]
                    logger.debug(f"Read {len(existing)} existing quotes from {csv_file}")
            except Exception as e:
                raise DataProcessingError(f"Error reading existing quotes: {str(e)}", 
                                         details={"file": csv_file, "exception": str(e)})

            # Write updated data
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(csv_file), exist_ok=True)

                with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in existing:
                        writer.writerow(r)
                    writer.writerow(row)

                logger.info(
                    f"✅ Quote {row['quote_number']} Rev {row['revision_number']} written to CSV."
                )
            except Exception as e:
                raise DataProcessingError(f"Error writing quote to CSV: {str(e)}", 
                                         details={"file": csv_file, "row": row, "exception": str(e)})

            # Upload to S3
            try:
                upload_to_s3(csv_file)
            except Exception as e:
                raise S3UploadError(f"Error uploading quote CSV to S3: {str(e)}", 
                                   details={"file": csv_file, "exception": str(e)})

    except (DataProcessingError, S3UploadError):
        # Re-raise these exceptions to be handled by the caller
        raise
    except Exception as e:
        # Catch any unexpected exceptions and wrap them
        error_details = {
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "file": csv_file,
            "row": row
        }
        raise DataProcessingError(f"Unexpected error updating quote CSV: {str(e)}", details=error_details)

# === Helper: Write order to CSV ===
@with_correlation_id
def update_order_csv(row):
    """
    Update the orders CSV file with new data and upload to S3.

    Args:
        row: Order data to write

    Raises:
        DataProcessingError: If there's an error processing the data
        S3UploadError: If there's an error uploading to S3
    """
    try:
        # Add context information to logs
        with LogContext(operation="update_order_csv", order_number=row.get("order_number")):
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

            # Validate required fields
            if not row.get("order_number"):
                raise DataProcessingError("Missing required field: order_number", details={"row": row})

            # Read existing data
            existing = []
            try:
                if os.path.isfile(ORDERS_CSV_FILE):
                    with open(ORDERS_CSV_FILE, newline='', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        existing = [
                            r for r in reader
                            if r["order_number"] != row["order_number"]
                        ]
                    logger.debug(f"Read {len(existing)} existing orders from {ORDERS_CSV_FILE}")
            except Exception as e:
                raise DataProcessingError(f"Error reading existing orders: {str(e)}", 
                                         details={"file": ORDERS_CSV_FILE, "exception": str(e)})

            # Write updated data
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(ORDERS_CSV_FILE), exist_ok=True)

                with open(ORDERS_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for r in existing:
                        writer.writerow(r)
                    writer.writerow(row)

                logger.info(f"✅ Order {row['order_number']} written to CSV.")
            except Exception as e:
                raise DataProcessingError(f"Error writing order to CSV: {str(e)}", 
                                         details={"file": ORDERS_CSV_FILE, "row": row, "exception": str(e)})

            # Upload to S3
            try:
                upload_to_s3(ORDERS_CSV_FILE)
            except Exception as e:
                raise S3UploadError(f"Error uploading order CSV to S3: {str(e)}", 
                                   details={"file": ORDERS_CSV_FILE, "exception": str(e)})

    except (DataProcessingError, S3UploadError):
        # Re-raise these exceptions to be handled by the caller
        raise
    except Exception as e:
        # Catch any unexpected exceptions and wrap them
        error_details = {
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "file": ORDERS_CSV_FILE,
            "row": row
        }
        raise DataProcessingError(f"Unexpected error updating order CSV: {str(e)}", details=error_details)

# === Handler functions for WebhookServer ===
# Note: Routes are registered in app.py

@with_correlation_id
def handle_quote_status_changed(data):
    """
    Handle quote.status_changed and quote.created events.

    Args:
        data: Quote data from the webhook payload

    Raises:
        WebhookValidationError: If required fields are missing
        DataProcessingError: If there's an error processing the data
        S3UploadError: If there's an error uploading to S3
    """
    try:
        # Add context information to logs
        with LogContext(handler="handle_quote_status_changed"):
            logger.info(f"Processing quote status change")
            logger.debug(f"Quote data: {data}")

            # Extract quote data - handle both quote.status_changed and quote.created formats
            quote_number = data.get('quote_number') or str(data.get('number', ''))
            revision_number = data.get('revision_number')
            status = data.get('status')

            # Validate required fields
            missing_fields = []
            if not quote_number:
                missing_fields.append("quote_number/number")
            if not revision_number:
                missing_fields.append("revision_number")
            if not status:
                missing_fields.append("status")

            if missing_fields:
                error_msg = f"Missing required fields in quote data: {', '.join(missing_fields)}"
                logger.warning(f"⚠️ {error_msg}")
                raise WebhookValidationError(error_msg, details={
                    "missing_fields": missing_fields,
                    "data": data
                })

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
                "contact_name": (safe_get(data, "contact", "first_name") or "") + " " + (
                        safe_get(data, "contact", "last_name") or ""),
                "contact_email": safe_get(data, "contact", "email"),
                "customer_name": safe_get(data, "contact", "account", "name"),
                "estimator_email": safe_get(data, "estimator", "email"),
                "salesperson_email": safe_get(data, "salesperson", "email")
            }

            # Log the extracted data
            logger.debug(f"Extracted quote data: {row}")

            # Update CSV and upload to S3
            update_csv(row)

            logger.info(f"Successfully processed quote {quote_number} revision {revision_number}")

    except (WebhookValidationError, DataProcessingError, S3UploadError):
        # Re-raise these exceptions to be handled by the caller
        raise
    except Exception as e:
        # Catch any unexpected exceptions and wrap them
        error_details = {
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "data": data
        }
        raise WebhookError(f"Unexpected error handling quote status change: {str(e)}", details=error_details)

@with_correlation_id
def handle_order_status_changed(data):
    """
    Handle order.status_changed and order.created events.

    Args:
        data: Order data from the webhook payload

    Raises:
        WebhookValidationError: If required fields are missing
        DataProcessingError: If there's an error processing the data
        S3UploadError: If there's an error uploading to S3
    """
    try:
        # Add context information to logs
        with LogContext(handler="handle_order_status_changed"):
            logger.info(f"Processing order status change")
            logger.debug(f"Order data: {data}")

            # Extract order data
            order_number = data.get('order_number')
            status = data.get('status')

            # Validate required fields
            missing_fields = []
            if not order_number:
                missing_fields.append("order_number")
            if not status:
                missing_fields.append("status")

            if missing_fields:
                error_msg = f"Missing required fields in order data: {', '.join(missing_fields)}"
                logger.warning(f"⚠️ {error_msg}")
                raise WebhookValidationError(error_msg, details={
                    "missing_fields": missing_fields,
                    "data": data
                })

            # Update CSV with order data
            row = {
                "order_number": order_number,
                "status": status,
                "created": data.get('created', ''),
                "due_date": data.get('due_date', ''),
                "quote_number": data.get('quote_number', ''),
                "quote_revision": data.get('quote_revision', ''),
                "customer_name": safe_get(data, "contact", "account", "name"),
                "contact_name": (safe_get(data, "contact", "first_name") or "") + " " + (
                        safe_get(data, "contact", "last_name") or ""),
                "contact_email": safe_get(data, "contact", "email"),
                "salesperson_email": safe_get(data, "salesperson", "email")
            }

            # Log the extracted data
            logger.debug(f"Extracted order data: {row}")

            # Update CSV and upload to S3
            update_order_csv(row)

            logger.info(f"Successfully processed order {order_number}")

    except (WebhookValidationError, DataProcessingError, S3UploadError):
        # Re-raise these exceptions to be handled by the caller
        raise
    except Exception as e:
        # Catch any unexpected exceptions and wrap them
        error_details = {
            "exception_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "data": data
        }
        raise WebhookError(f"Unexpected error handling order status change: {str(e)}", details=error_details)

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
