# Script to pull users (salespeople/estimatorsimport requests
from utils.config_loader import config

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token {API_TOKEN}"}

def main():
    url = f"{BASE_URL}/quotes/public/new"
    try:
        res = requests.get(url, headers=HEADERS)
        res.raise_for_status()
        data = res.json()

        print("✅ Revised quotes:")
        for item in data:
            quote = item["quote"]
            revision = item.get("revision")
            if revision and revision > 0:
                print(f"{quote}-{revision}")

    except Exception as e:
        print(f"❌ Failed to fetch quote list: {e}")

if __name__ == "__main__":
    main()) from Paperless