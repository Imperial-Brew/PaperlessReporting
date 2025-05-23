import requests
import csv
import time
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from scripts.utils.config_loader import config
from scripts.utils.token_bucket import TokenBucket
from scripts.utils.utils import safe_get, log_failures

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token " + API_TOKEN}

# === ORDER RANGE TO PROCESS
START = 540
END = 560
order_ids = list(range(START, END + 1))

THREADS = 4
bucket = TokenBucket(rate=1.8, capacity=5)

# === Shared request counter and lock
request_counter = 0
counter_lock = threading.Lock()


# === Fetch and flatten order items from one order
def fetch_order_items(order_id, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/orders/public/{order_id}"
            res = requests.get(url, headers=HEADERS, timeout=10)

            if res.status_code == 200:
                o = res.json()
                order_number = o.get("number")
                items = o.get("order_items", [])
                rows = []
                for item in items:
                    part_number = revision = material = process = part_uuid = ""
                    for c in item.get("components", []):
                        if c.get("is_root_component"):
                            part_number = c.get("part_number", "")
                            revision = c.get("revision", "")
                            part_uuid = c.get("part_uuid", "")
                            material = safe_get(c, "material", "name") or ""
                            process = safe_get(c, "process", "name") or ""
                            break

                    rows.append({
                        "order_number": order_number,
                        "item_id": item.get("id"),
                        "part_number": part_number,
                        "part_uuid": part_uuid,
                        "revision": revision,
                        "description": item.get("description"),
                        "quantity": item.get("quantity"),
                        "unit_price": item.get("unit_price", ""),
                        "total_price": item.get("total_price", ""),
                        "material": material,
                        "process": process,
                        "export_controlled": item.get("export_controlled", ""),
                        "filename": item.get("filename", ""),
                        "lead_days": item.get("lead_days", ""),
                        "quote_item_id": item.get("quote_item_id", "")
                    })
                return rows, None

            elif res.status_code == 429:
                print(f"⏳ Rate limit hit for order {order_id}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Order {order_id} returned status {res.status_code}")
        except Exception as e:
            print(f"⚠️ Exception fetching order {order_id} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return [], order_id


# === Rate-limited wrapper
def rate_limited_fetch_order_items(order_id):
    while not bucket.consume():
        time.sleep(0.05)
    global request_counter
    with counter_lock:
        request_counter += 1
    return fetch_order_items(order_id)


# === Main batch loop
def main():
    all_rows = []
    failed = []

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(rate_limited_fetch_order_items, oid): oid for oid in order_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Order Items {START}-{END}"):
            result, missing = future.result()
            if missing:
                failed.append(missing)
            all_rows.extend(result)
            time.sleep(0.4)

    # === Write to CSV
    output_path = rf"P:\WORK\PaperlessReporting\data_raw\order_items\order_items_{START}_{END}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_rows:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_rows[0].keys())
            writer.writeheader()
            writer.writerows(all_rows)
        print(f"✅ Saved {len(all_rows)} order items to {output_path}")
    else:
        print("⚠️ No order items written.")

    # === Log failures
    log_failures("P:/WORK/PaperlessReporting/logs/errors/failed_order_items.txt", failed)


if __name__ == "__main__":
    main()
