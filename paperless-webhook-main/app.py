from flask import Flask, request, jsonify
import requests
import csv
import os

app = Flask(__name__)

# === Configuration ===
API_TOKEN = os.getenv("PAPERLESS_API_TOKEN", "SET_ME")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "supersecret")
CSV_FILE = "quotes_live.csv"

# === Helper: Write quote to CSV ===
def update_csv(row):
    file_exists = os.path.isfile(CSV_FILE)
    fieldnames = list(row.keys())

    existing = []
    if file_exists:
        with open(CSV_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            existing = [r for r in reader if r["uuid"] != row["uuid"]]

    with open(CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in existing:
            writer.writerow(r)
        writer.writerow(row)

    print(f"Quote {row['quote_number']} written to CSV.")

# === Helper: Call Paperless API for full quote info ===
def fetch_and_save_quote(quote_uuid):
    url = f"https://api.paperlessparts.com/quotes/public/{quote_uuid}"
    headers = {"Authorization": f"API-Token {API_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Failed to fetch quote {quote_uuid}: {response.status_code}")
        return

    quote = response.json()
    row = {
        "quote_number": quote.get("quote_number"),
        "uuid": quote.get("uuid"),
        "status": quote.get("status"),
        "created_at": quote.get("created_at"),
        "updated_at": quote.get("updated_at"),
        "customer_name": quote.get("customer", {}).get("name", ""),
        "estimator_email": quote.get("estimator", {}).get("email", "")
    }

    update_csv(row)

# === Route: Handle Webhook POST ===
@app.route("/webhook", methods=["POST"])
def webhook():
    token = request.args.get("token")
    if token != WEBHOOK_SECRET:
        return "Forbidden", 403

    try:
        data = request.get_json(force=True)
    except Exception as e:
        print(f"Failed to parse JSON: {e}")
        print(f"Raw body: {request.data}")
        return "Invalid JSON", 400

    print("Webhook payload received:")
    print(data)

    quote_uuid = data.get("data", {}).get("uuid")
    if not quote_uuid:
        print("Missing 'data.uuid' key in payload.")
        return "Invalid payload", 400

    print(f"Webhook received for quote UUID: {quote_uuid}")
    fetch_and_save_quote(quote_uuid)
    return jsonify({"status": "OK"}), 200

# === Start Server (local dev only) ===
if __name__ == "__main__":
    app.run(port=5000)
