import requests
import json
import os
from utils.config_loader import config

# Configuration
WEBHOOK_URL = "https://paperlessreporting.onrender.com/webhook"
WEBHOOK_SECRET = os.getenv(
    "WEBHOOK_SECRET",
    config.get("webhook_secret", "supersecret")
)

def test_order_created_webhook():
    """Test the webhook with a sample order.created event."""
    url = f"{WEBHOOK_URL}?token={WEBHOOK_SECRET}"

    # Sample webhook payload for order.created event
    payload = {
        "type": "order.created",
        "data": {
            "order_number": "O-2024-0001",
            "status": "pending",
            "created": "2025-06-01T10:00:00Z",
            "due_date": "2025-06-15T10:00:00Z",
            "quote_number": "Q-2024-0002",
            "quote_revision": "1",
            "customer_name": "Example Company",
            "contact_name": "John Doe",
            "contact_email": "john.doe@example.com",
            "salesperson_email": "sales@example.com"
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"Sending test order.created webhook to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Test successful! The server accepted the order.created event.")
        else:
            print("❌ Test failed! The server rejected the order.created event.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_order_created_webhook()