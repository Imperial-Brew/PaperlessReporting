"""
Script to pull users (salespeople/estimators) from Paperless API.

This script fetches user data from the API and displays the first 5 responses in full detail.
"""

import requests
import json
import time
import csv
from pathlib import Path
from utils.config_loader import config_loader

API_TOKEN = config_loader["api_key"]
BASE_URL = config_loader["api_base_url"]
HEADERS = {"Authorization": f"API-Token {API_TOKEN}"}

def fetch_users():
    users = []
    url = f"{BASE_URL}/users/public"

    while url:
        print(f"Fetching users from {url}...")
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()

        # Check if the response is a list or has a 'results' field
        if isinstance(data, list):
            users.extend(data)
            url = None  # No pagination for list responses
        else:
            users.extend(data.get("results", []))
            url = data.get("next")  # Get the next page URL if available

        # Add a small delay to avoid rate limiting
        if url:
            time.sleep(0.2)

    return users

def main():
    try:
        users = fetch_users()

        # Get the total number of users
        total_users = len(users)
        print(f"✅ Found {total_users} users")

        # Display the first 5 users in full detail
        print("\n=== First 5 Users (Full Data) ===")
        for i, user in enumerate(users[:5], 1):
            print(f"\n--- User {i}/{min(5, total_users)} ---")
            print(json.dumps(user, indent=2))

        # Display a summary of all users
        print("\n=== All Users (Summary) ===")
        for i, user in enumerate(users, 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            email = user.get('email', 'No email')
            role = user.get('role', 'Unknown role')
            print(f"{i}. {name} ({email}) - {role}")

        # Save users to CSV
        output_dir = Path("data_raw/users/public")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "users_all.csv"

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            if users:
                writer = csv.DictWriter(f, fieldnames=users[0].keys())
                writer.writeheader()
                writer.writerows(users)
                print(f"✅ Wrote {len(users)} users to {output_path}")
            else:
                print("⚠️ No users to write to CSV")

    except Exception as e:
        print(f"❌ Failed to fetch users: {e}")

if __name__ == "__main__":
    main()
