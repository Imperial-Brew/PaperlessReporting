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
START = 520
END = 560
order_ids = list(range(START, END + 1))

THREADS = 4
bucket = TokenBucket(rate=1.8, capacity=5)

# === Shared request counter and lock
request_counter = 0
counter_lock = threading.Lock()


# === Fetch one order
def fetch_order(order_id, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/orders/public/{order_id}"
            res = requests.get(url, headers=HEADERS, timeout=10)
            if res.status_code == 200:
                o = res.json()
                return {
                    "order_number": o.get("number"),
                    "quote_number": o.get("quote_number"),
                    "quote_revision_number": o.get("quote_revision_number"),
                    "status": o.get("status"),
                    "created": o.get("created"),
                    "deliver_by": o.get("deliver_by"),
                    "ships_on": o.get("ships_on"),
                    "payment_terms": safe_get(o, "payment_details", "payment_terms"),
                    "purchase_order_number": safe_get(o, "payment_details", "purchase_order_number"),
                    "salesperson_email": safe_get(o, "salesperson", "email"),
                    "customer_name": safe_get(o, "shipping_info", "business_name")
                }
            elif res.status_code == 429:
                print(f"⏳ Rate limit hit for order {order_id}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Failed to fetch order {order_id}: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching order {order_id} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return None


# === Rate-limited wrapper
def rate_limited_fetch_order(order_id):
    while not bucket.consume():
        time.sleep(0.05)
    global request_counter
    with counter_lock:
        request_counter += 1
    return order_id, fetch_order(order_id)


# === Main batch loop
def main():
    all_orders = []
    failed = []

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(rate_limited_fetch_order, oid): oid for oid in order_ids}
        for future in tqdm(as_completed(futures), total=len(futures), desc=f"Orders {START}-{END}"):
            oid = futures[future]
            try:
                oid, result = future.result()
                if result:
                    all_orders.append(result)
                else:
                    failed.append(oid)
            except Exception as e:
                print(f"❌ Order {oid} crashed: {e}")
                failed.append(oid)
            time.sleep(0.5)

    # === Write to CSV
    output_path = rf"P:\WORK\PaperlessReporting\data_raw\orders\orders_{START}_{END}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_orders:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_orders[0].keys())
            writer.writeheader()
            writer.writerows(all_orders)
        print(f"✅ Wrote {len(all_orders)} orders to {output_path}")
    else:
        print("⚠️ No orders found.")

    # === Log failures
    log_failures("P:/WORK/PaperlessReporting/logs/errors/failed_orders.txt", failed)


if __name__ == "__main__":
    main()
