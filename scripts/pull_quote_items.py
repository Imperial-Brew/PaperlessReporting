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


# === Fetch and flatten quote_items using root component from components[]
def fetch_quote_items(quote_id, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/quotes/public/{quote_id}"
            res = requests.get(url, headers=HEADERS, timeout=20)
            if res.status_code == 200:
                quote = res.json()
                quote_number = quote.get("number")
                quote_items = quote.get("quote_items", [])
                rows = []

                for item in quote_items:
                    root = next((c for c in item.get("components", []) if c.get("is_root_component")), {})
                    part_number = root.get("part_number", "")
                    part_uuid = root.get("part_uuid", "")
                    description = root.get("description", "")
                    revision = root.get("revision", "")
                    material = safe_get(root, "material", "name") or ""
                    process = safe_get(root, "process", "name") or ""
                    is_fully_configured = all([part_number, description, material, process])

                    base_row = {
                        "quote_number": quote_number,
                        "item_id": item.get("id"),
                        "workflow_status": item.get("workflow_status"),
                        "part_number": part_number,
                        "revision": revision,
                        "description": description,
                        "type": root.get("type", ""),
                        "material": material,
                        "process": process,
                        "is_fully_configured": is_fully_configured,
                        "part_uuid": part_uuid,
                        "export_controlled": item.get("export_controlled")
                    }

                    for q in root.get("quantities", []):
                        row = base_row.copy()
                        row.update({
                            "quantity": q.get("quantity"),
                            "unit_price": q.get("unit_price"),
                            "total_price": q.get("total_price"),
                            "total_price_with_add_ons": q.get("total_price_with_required_add_ons"),
                            "lead_time": q.get("lead_time")
                        })
                        rows.append(row)
                return rows
            elif res.status_code == 429:
                print(f"⏳ Rate limit hit for quote {quote_id}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Failed to fetch quote {quote_id}: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching quote {quote_id} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return []


# === Rate-limited wrapper
def rate_limited_fetch_items(qid):
    while not bucket.consume():
        time.sleep(0.05)
    global request_counter
    with counter_lock:
        request_counter += 1
    return qid, fetch_quote_items(qid)


# === Main batch loop
def main():
    all_items = []
    failed = []

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(rate_limited_fetch_items, qid): qid for qid in quote_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Quote Items {START}-{END}"):
            qid = futures[future]
            try:
                qid, result = future.result()
                if result:
                    all_items.extend(result)
                else:
                    failed.append(qid)
            except Exception as e:
                print(f"❌ Quote {qid} crashed: {e}")
                failed.append(qid)
            time.sleep(0.4)

    # === Write to CSV
    output_path = rf"P:\WORK\PaperlessReporting\data_raw\quote_items\quote_items_{START}_{END}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_items:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_items[0].keys())
            writer.writeheader()
            writer.writerows(all_items)
        print(f"✅ Wrote {len(all_items)} quote items to {output_path}")
    else:
        print("⚠️ No quote items found.")

    # === Log failures
    log_failures("P:/WORK/PaperlessReporting/logs/errors/failed_quote_items.txt", failed)


if __name__ == "__main__":
    main()
