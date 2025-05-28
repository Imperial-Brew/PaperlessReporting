"""
Script to pull users (salespeople/estimators) from Paperless API.

This script fetches user data from the API and displays the first 5 responses in full detail.
"""

import requests
import json
from scripts.utils.config_loader import config

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token {API_TOKEN}"}

def main():
    # Endpoint for users (salespeople/estimators)
    url = f"{BASE_URL}/users"

    try:
        print(f"Fetching users from {url}...")
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        # Get the total number of users
        total_users = len(data)
        print(f"✅ Found {total_users} users")

        # Display the first 5 users in full detail
        print("\n=== First 5 Users (Full Data) ===")
        for i, user in enumerate(data[:5], 1):
            print(f"\n--- User {i}/{min(5, total_users)} ---")
            print(json.dumps(user, indent=2))

        # Display a summary of all users
        print("\n=== All Users (Summary) ===")
        for i, user in enumerate(data, 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            email = user.get('email', 'No email')
            role = user.get('role', 'Unknown role')
            print(f"{i}. {name} ({email}) - {role}")

    except Exception as e:
        print(f"❌ Failed to fetch users: {e}")

if __name__ == "__main__":
    main()
