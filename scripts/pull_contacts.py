import requests
import csv
import json
from pathlib import Path
from scripts.utils.config_loader import config

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token " + API_TOKEN}


def fetch_contacts():
    url = f"{BASE_URL}/contacts/public"
    contacts = []

    while url:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        contacts.extend(data["results"])
        url = data.get("next")  # Continue until no more pages

    return contacts


def main():
    contacts = fetch_contacts()
    processed = []

    for c in contacts:
        processed.append({
            "id": c.get("id"),
            "first_name": c.get("first_name"),
            "last_name": c.get("last_name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "phone_ext": c.get("phone_ext"),
            "notes": c.get("notes"),
            "account_id": c.get("account_id"),
        })

    out_path = Path(r"P:/WORK/PaperlessReporting/data_raw/contacts/contacts.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=processed[0].keys())
        writer.writeheader()
        writer.writerows(processed)
    print(f"✅ Saved {len(processed)} contacts to {out_path}")


if __name__ == "__main__":
    main()
