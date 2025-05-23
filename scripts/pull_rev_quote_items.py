import requests
import csv
import time
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from utils.config_loader import config
from utils.utils import safe_get, log_failures

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token " + API_TOKEN}
THREADS = 4

# Set the range of the batch
BATCH_START = 0
BATCH_END = 999


def get_all_revisions():
    url = f"{BASE_URL}/quotes/public/new"
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    data = res.json()
    filtered = [(q["quote"], q["revision"]) for q in data if q["revision"] not in (None, 0)]
    return filtered[BATCH_START:BATCH_END + 1]


def fetch_quote_items(quote_number, revision, max_retries=3):
    delay = 1
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/quotes/public/{quote_number}?revision={revision}"
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
                    revision_id = root.get("revision", "")
                    material = safe_get(root, "material", "name") or ""
                    process = safe_get(root, "process", "name") or ""
                    is_fully_configured = all([part_number, description, material, process])

                    base_row = {
                        "quote_number": quote_number,
                        "quote_revision": revision,
                        "item_id": item.get("id"),
                        "workflow_status": item.get("workflow_status"),
                        "part_number": part_number,
                        "revision": revision_id,
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
                print(f"⏳ Rate limit hit for quote {quote_number}-r{revision}, pausing 15s")
                time.sleep(15)
            else:
                print(f"⚠️ Failed to fetch quote {quote_number}-r{revision}: {res.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching quote {quote_number}-r{revision} (attempt {attempt + 1}): {e}")
        time.sleep(delay)
        delay *= 2
    return []


def fetch_pair(pair):
    return pair, fetch_quote_items(*pair)


def main():
    all_items = []
    failed = []

    quote_revs = get_all_revisions()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        futures = {executor.submit(fetch_pair, pair): pair for pair in quote_revs}
        for future in tqdm(as_completed(futures), total=len(futures),
                           desc=f"Quote Revisions {BATCH_START}-{BATCH_END}"):
            try:
                pair, result = future.result()
                if result:
                    all_items.extend(result)
                else:
                    failed.append(pair)
            except Exception as e:
                print(f"❌ Quote {pair} crashed: {e}")
                failed.append(pair)

    output_path = fr"P:\WORK\PaperlessReporting\data_raw\quote_items\quote_items_revised_{BATCH_START}_{BATCH_END}.csv"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_items:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_items[0].keys())
            writer.writeheader()
            writer.writerows(all_items)
        print(f"✅ Wrote {len(all_items)} quote items to {output_path}")
    else:
        print("⚠️ No quote items found.")

    log_failures("P:/WORK/PaperlessReporting/logs/errors/failed_revised_quote_items.txt", failed)


if __name__ == "__main__":
    main()
