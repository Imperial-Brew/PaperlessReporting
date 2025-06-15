import requests
import json
import os
from scripts.utils.config_loader import config

# Configuration
WEBHOOK_URL = "http://localhost:5000/webhook"  # Use local server for testing
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    config.get("webhook_secret", "supersecret")
)

def test_quote_created_webhook():
    """Test the webhook with a sample quote.created event using the actual data structure."""
    url = f"{WEBHOOK_URL}?token={WEBHOOK_SECRET}"

    # Sample webhook payload for quote.created event with the actual data structure
    payload = {
        "type": "quote.created",
        "data": {
            "uuid": "608d41a4-8f92-49a9-8d53-5bef17be3131",
            "number": 7838,
            "status": "draft",
            "created": "2025-05-31T13:04:39.219587Z",
            "expired": False,
            "due_date": "2025-06-03T13:04:39.212787Z",
            "erp_code": None,
            "metadata": {},
            "priority": None,
            "tax_rate": "0.000",
            "estimator": "5425218a-6230-4efe-9b7c-57b8d2635a5e",
            "sent_date": None,
            "contact_id": 34689,
            "rfq_number": "test",
            "quote_items": ["72e03e22-414a-4667-b27f-3321307faad6"],
            "quote_notes": "Thank you for the opportunity to quote...",
            "salesperson": "5425218a-6230-4efe-9b7c-57b8d2635a5e",
            "expired_date": "2025-06-30T13:04:39.209792Z",
            "private_notes": "File Location here.",
            "revision_number": 3,
            "supporting_files": [],
            "export_controlled": False,
            "send_from_facility": "6282346e-6ab9-4834-81e7-cabba049f398",
            "request_for_quote_id": None,
            "digital_last_viewed_on": None,
            "manual_rfq_received_date": "2025-05-23T21:11:18.205000Z",
            "authenticated_pdf_quote_url": None
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"Sending test quote.created webhook to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            print("✅ Test successful! The server accepted the quote.created event.")
        else:
            print("❌ Test failed! The server rejected the quote.created event.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_quote_created_webhook()