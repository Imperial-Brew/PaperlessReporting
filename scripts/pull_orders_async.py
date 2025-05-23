import asyncio
import aiohttp
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

from scripts.utils.config_loader import config
from scripts.utils.async_token_bucket import AsyncTokenBucket
from scripts.utils.utils import safe_get, log_failures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

API_TOKEN = config["api_key"]
BASE_URL = config["api_base_url"]
HEADERS = {"Authorization": f"API-Token {API_TOKEN}"}

# === ORDER RANGE TO PROCESS
START = 520
END = 560
order_ids = list(range(START, END + 1))

# Rate limiting
bucket = AsyncTokenBucket(rate=1.8, capacity=5)

async def fetch_order(session: aiohttp.ClientSession, order_id: int, max_retries: int = 3) -> Optional[Dict]:
    """
    Fetch a single order with retry logic.
    
    Args:
        session: aiohttp client session
        order_id: ID of the order to fetch
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dict containing order data or None if failed
    """
    delay = 1
    for attempt in range(max_retries):
        try:
            async with bucket:  # This will automatically acquire a token
                url = f"{BASE_URL}/orders/public/{order_id}"
                async with session.get(url, headers=HEADERS, timeout=10) as response:
                    if response.status == 200:
                        o = await response.json()
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
                    elif response.status == 429:
                        logger.warning(f"⏳ Rate limit hit for order {order_id}, pausing 15s")
                        await asyncio.sleep(15)
                    else:
                        logger.error(f"⚠️ Failed to fetch order {order_id}: {response.status}")
        except Exception as e:
            logger.error(f"⚠️ Error fetching order {order_id} (attempt {attempt + 1}): {e}")
        
        await asyncio.sleep(delay)
        delay *= 2
    return None

async def process_orders(order_ids: List[int], output_path: str) -> None:
    """
    Process a batch of orders concurrently.
    
    Args:
        order_ids: List of order IDs to process
        output_path: Path to write the CSV output
    """
    all_orders = []
    failed = []
    
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_order(session, oid) for oid in order_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for oid, result in zip(order_ids, results):
            if isinstance(result, Exception):
                logger.error(f"❌ Order {oid} crashed: {result}")
                failed.append(oid)
            elif result:
                all_orders.append(result)
            else:
                failed.append(oid)
    
    # Write to CSV
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if all_orders:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_orders[0].keys())
            writer.writeheader()
            writer.writerows(all_orders)
        logger.info(f"✅ Wrote {len(all_orders)} orders to {output_path}")
    else:
        logger.warning("⚠️ No orders found.")

    # Log failures
    log_failures("logs/errors/failed_orders.txt", failed)

async def main():
    """Main entry point for the script."""
    output_path = f"data_raw/orders/orders_{START}_{END}.csv"
    await process_orders(order_ids, output_path)

if __name__ == "__main__":
    asyncio.run(main()) 