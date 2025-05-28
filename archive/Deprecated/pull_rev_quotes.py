import requests
import csv
import json
import time
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from scripts.utils.config_loader import config
from scripts.utils.utils import safe_get

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token " + API_TOKEN}
THREADS = 4


# === Step 1: Get quote/revision pairs (first 5, excluding rev 0)
def get_all_revisions():
    url = f"{BASE_URL}/quotes/public/new"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    data = res.json()
    return [(q["quote"], q["revision"]) for q in data if q["revision"] not in (None, 0)]


# === Fetch quote with revision
def fetch_quote(quote_number, revision, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/quotes/public/{quote_number}?revision={revision}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                q = res.json()
                return {
                    "quote_id": f"{q.get('number')}-{revision}",
                    "quote_number": q.get("number"),
                    "revision_number": revision,
                    "status": q.get("status"),
                    "created": q.get("created"),
                    "due_date": q.get("due_date"),
                    "sent_date": q.get("sent_date"),
                    "expired_date": q.get("expired_date"),
                    "expired": q.get("expired"),
                    "rfq_number": q.get("rfq_number"),
                    "priority": q.get("priority"),
                    "private_notes": q.get("private_notes"),
                    "authenticated_pdf_quote_url": q.get("authenticated_pdf_quote_url"),
                    "contact_name": (safe_get(q, "contact", "first_name") or "") + " " + (
                                safe_get(q, "contact", "last_name") or ""),
                    "contact_email": safe_get(q, "contact", "email"),
                    "customer_name": safe_get(q, "contact", "account", "name"),
                    "estimator_email": safe_get(q, "estimator", "email"),
                    "salesperson_email": safe_get(q, "salesperson", "email")
                }
            elif res.status_code == 429:
                print(f"⏳ Rate limit hit for quote {quote_number}-r{revision}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Failed to fetch quote {quote_number}-r{revision}: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching quote {quote_number}-r{revision} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return None


# === Threaded wrapper
def fetch_pair(pair):
    return pair, fetch_quote(*pair)


# === Main
def main():
    all_quotes = []
    failed = []

    quote_revs = get_all_revisions()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(fetch_pair, pair): pair for pair in quote_revs}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Revised Quotes"):
            try:
                pair, result = future.result()
                if result:
                    all_quotes.append(result)
                else:
                    failed.append(pair)
            except Exception as e:
                print(f"❌ Quote {pair} crashed: {e}")
                failed.append(pair)

    output_path = r"P:/WORK/PaperlessReporting/data_raw/quotes/quotes_revised.csv"
    if all_quotes:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_quotes[0].keys())
            writer.writeheader()
            writer.writerows(all_quotes)
        print(f"✅ Wrote {len(all_quotes)} revised quotes to {output_path}")
    else:
        print("⚠️ No revised quotes found.")


if __name__ == "__main__":
    main()
