import requests
import csv
import json
import time
from pathlib import Path

# Load config from config.json
with open("config.json") as f:
    config = json.load(f)

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token {API_TOKEN}"}


def fetch_accounts():
    accounts = []
    url = f"{BASE_URL}/accounts/public"
    while url:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        data = res.json()
        accounts.extend(data.get("results", []))
        url = data.get("next")
        time.sleep(0.2)
    return accounts


def main():
    accounts = fetch_accounts()
    # Test run: print first 5 accounts
    for i, acct in enumerate(accounts[:5], start=1):
        print(f"--- Account {i} ---")
        print(json.dumps(acct, indent=2))
    # Write full list to CSV
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "accounts.csv"
    if accounts:
        with open(output_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=accounts[0].keys())
            writer.writeheader()
            writer.writerows(accounts)
        print(f"Wrote {len(accounts)} accounts to {output_path}")
    else:
        print("⚠️ No accounts fetched.")


if __name__ == "__main__":
    main()
