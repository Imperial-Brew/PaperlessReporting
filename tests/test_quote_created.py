import requests
import json
import os
from scripts.utils.config_loader import config

# Configuration
WEBHOOK_URL = "https://paperlessreporting.onrender.com/webhook"
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    config.get("webhook_secret", "supersecret")
)

def test_quote_created_webhook():
    """Test the webhook with a sample quote.created event."""
    url = f"{WEBHOOK_URL}?token={WEBHOOK_SECRET}"

    # Sample webhook payload for quote.created event
    payload = {
        "type": "quote.created",
        "data": {
            "quote_number": "Q-2024-0002",
            "revision_number": "1",
            "status": "draft",
            "created": "2025-05-31T13:04:39Z",
            "due_date": "2025-06-07T13:04:39Z",
            "rfq_number": "RFQ-2024-0002",
            "priority": "normal",
            "private_notes": "Test quote created via webhook",
            "contact_name": "John Doe",
            "contact_email": "john.doe@example.com",
            "customer_name": "Example Company",
            "estimator_email": "estimator@example.com",
            "salesperson_email": "sales@example.com"
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