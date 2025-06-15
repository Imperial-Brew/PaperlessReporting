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

def test_webhook():
    """Test the webhook with a sample quote status change event."""
    url = f"{WEBHOOK_URL}?token={WEBHOOK_SECRET}"

    # Sample webhook payload
    payload = {
        "type": "quote.status_changed",
        "data": {
            "quote_number": "Q-2024-0001",
            "revision_number": "1",
            "status": "sent"
        }
    }

    headers = {
        "Content-Type": "application/json"
    }

    print(f"Sending test webhook to: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_webhook()