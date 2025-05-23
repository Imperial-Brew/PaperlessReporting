import requests
import csv
import time
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from utils.config_loader import config
from utils.token_bucket import TokenBucket
from utils.utils import safe_get, log_failures

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token " + API_TOKEN}

# === QUOTE RANGE TO PROCESS
START = 7500
END = 8000
quote_ids = list(range(START, END + 1))

THREADS = 4
bucket = TokenBucket(rate=1.8, capacity=5)

# === Shared request counter and lock
request_counter = 0
counter_lock = threading.Lock()


# === Fetch a single quote
def fetch_quote(quote_id, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/quotes/public/{quote_id}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                q = res.json()
                return {
                    "quote_number": q.get("number"),
                    "revision_number": q.get("revision_number"),
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
                print(f"⏳ Rate limit hit for quote {quote_id}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Failed to fetch quote {quote_id}: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching quote {quote_id} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return None


# === Rate-limited wrapper
def rate_limited_fetch(quote_id):
    while not bucket.consume():
        time.sleep(0.05)
    global request_counter
    with counter_lock:
        request_counter += 1
    return quote_id, fetch_quote(quote_id)


# === Main batch loop
def main():
    all_quotes = []
    failed = []

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(rate_limited_fetch, qid): qid for qid in quote_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Quotes {START}-{END}"):
            try:
                qid, result = future.result()
                if result:
                    all_quotes.append(result)
                else:
                    failed.append(qid)
            except Exception as e:
                print(f"❌ Quote {qid} crashed: {e}")
                failed.append(qid)

    # === Write to CSV
    output_path = rf"P:\WORK\PaperlessReporting\data_raw\quotes\quotes_{START}_{END}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_quotes:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_quotes[0].keys())
            writer.writeheader()
            writer.writerows(all_quotes)
        print(f"✅ Wrote {len(all_quotes)} quotes to {output_path}")
    else:
        print("⚠️ No quotes found.")

    # === Log failures
    log_failures("P:/WORK/PaperlessReporting/logs/errors/failed_quotes.txt", failed)


if __name__ == "__main__":
    main()
