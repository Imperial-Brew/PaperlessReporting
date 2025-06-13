import requests
import json
from pathlib import Path
import sys

# ─── 1) PUT YOUR API KEY HERE ──────────────────────────────────────────────────
API_KEY = "bb2166a05a6aba9341734580af5b901677daa7c2"
if API_KEY.startswith("YOUR_"):
    sys.exit("❌ You must edit dump_two.py and replace API_KEY with your actual key.")
# ────────────────────────────────────────────────────────────────────────────────

# ─── 2) BASE URL (no trailing slash) ──────────────────────────────────────────
API_BASE = "https://api.paperlessparts.com"
# ────────────────────────────────────────────────────────────────────────────────

# ─── 3) TARGET IDs ─────────────────────────────────────────────────────────────
QUOTE_ID = 7529
ORDER_ID = 559
# ────────────────────────────────────────────────────────────────────────────────

# ─── 4) WHERE TO WRITE OUTPUT ──────────────────────────────────────────────────
OUTPUT_DIR = Path(r"F:\Dustin Drab\CURSOR\PaperlessReporting\logs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# ────────────────────────────────────────────────────────────────────────────────

def fetch_and_save(endpoint: str, output_name: str):
    """
    Performs a GET on API_BASE + endpoint (with X-API-Key header)
    and writes the JSON response to OUTPUT_DIR/output_name.
    """
    url = f"{API_BASE.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = { --header 'Authorization: API-Token <bb2166a05a6aba9341734580af5b901677daa7c2>'
    }
    print(f"→ Fetching: {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    if resp.status_code == 200:
        data = resp.json()
        out_path = OUTPUT_DIR / output_name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"✅ Saved JSON → {out_path}")
    else:
        print(f"❌ Failed to fetch {endpoint!r}: {resp.status_code} → {resp.text}")
        sys.exit(1)

if __name__ == "__main__":
    # Fetch quote 7529
    quote_endpoint = f"quotes/public/{QUOTE_ID}"
    fetch_and_save(quote_endpoint, f"quote_{QUOTE_ID}.json")

    # Fetch order 559
    order_endpoint = f"orders/public/{ORDER_ID}"
    fetch_and_save(order_endpoint, f"order_{ORDER_ID}.json")
