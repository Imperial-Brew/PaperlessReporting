import csv
import json
import time
from pathlib import Path

import requests

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

    # If nothing was fetched, bail out immediately
    if not accounts:
        print("⚠️ No accounts fetched.")
        return

    # Otherwise, write the CSV
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "accounts.csv"

    with open(output_path, "w", newline="", encoding="utf-8") as libwriter:
        writer = csv.DictWriter(libwriter, fieldnames=accounts[0].keys())
        writer.writeheader()
        writer.writerows(accounts)
    print(f"Wrote {len(accounts)} accounts to {output_path}")



if __name__ == "__main__":
    main()
