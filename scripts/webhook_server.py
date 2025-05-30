from flask import Flask, request, jsonify
import requests
import csv
import os
import logging
from scripts.utils.config_loader import get
from utils.s3_helpers import upload_to_s3

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
# Use platform-independent paths relative to project root
from pathlib import Path
import sys

# Determine the project root directory
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

# === Remaining handlers and routes unchanged ===

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
