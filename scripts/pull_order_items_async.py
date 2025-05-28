"""
Asynchronous puller for order item data from the API.

This script fetches order item data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching a specific range of order IDs.
"""

import asyncio
import logging
import argparse
import aiohttp
from typing import Dict, Any, Optional, List, Tuple

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class OrderItemsPuller(AsyncPuller[List[Dict[str, Any]]]):
    """
    Asynchronous puller for order item data.

    This class extends AsyncPuller to fetch order data from the API,
    extract the order items, and transform them into a structured format.
    It supports fetching a specific range of order IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the OrderItemsPuller.

        Args:
            start_id: Optional starting ID for range of orders to fetch
            end_id: Optional ending ID for range of orders to fetch
        """
        super().__init__(
            endpoint="orders/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=20  # Process 20 orders at a time
        )
        self.start_id = start_id
        self.end_id = end_id

    def transform_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform raw order data into order items.

        Extracts order items from the order data and transforms each item
        into a structured format with selected fields.

        Args:
            data: Raw order data from the API

        Returns:
            List of transformed order items
        """
        order_number = data.get("number")
        items = data.get("order_items", [])
        transformed_items = []

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

            transformed_items.append({
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

        return transformed_items

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on the range of orders being fetched.

        Returns:
            Path to the output CSV file
        """
        if self.start_id is not None and self.end_id is not None:
            return f"data_raw/order_items/order_items_{self.start_id}_{self.end_id}.csv"
        return "data_raw/order_items/order_items_all.csv"

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of order IDs to process.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all order IDs to process when no range is specified.

        This implementation uses pagination to fetch all order IDs from the API.

        Returns:
            List of all order IDs to process
        """
        # This is a placeholder implementation
        # In a real implementation, you would fetch all order IDs from the API
        # using pagination
        logger.warning("Fetching all orders is not yet implemented")
        logger.warning("Please specify a range using --start-id and --end-id")
        return []

    async def process_batch(self, batch_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Process a batch of orders concurrently and extract their order items.

        This method overrides the base class method to handle the special case
        of transform_data returning a list of items instead of a single item.

        Args:
            batch_ids: List of order IDs to process

        Returns:
            List of all order items from the processed orders
        """
        all_items = []

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_item(session, item_id) for item_id in batch_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item_id, result in zip(batch_ids, results):
                if isinstance(result, Exception):
                    logger.error(f"Exception processing order {item_id}: {result}")
                    self.failed_ids.append(item_id)
                elif result is None:
                    self.failed_ids.append(item_id)
                else:
                    try:
                        # transform_data returns a list of items for this order
                        order_items = self.transform_data(result)
                        all_items.extend(order_items)
                        # Count the order as processed if we successfully extracted its items
                        self.processed_count += 1
                        logger.info(f"Extracted {len(order_items)} items from order {item_id}")
                    except Exception as e:
                        logger.error(f"Error transforming order {item_id}: {str(e)}")
                        self.failed_ids.append(item_id)

        return all_items


async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates an OrderItemsPuller instance,
    and runs it to fetch order item data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch order item data from the API")
    parser.add_argument("--start-id", type=int, help="Starting order ID", default=540)
    parser.add_argument("--end-id", type=int, help="Ending order ID", default=560)
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    puller = OrderItemsPuller(start_id, end_id)
    logger.info(f"Starting order item pull job: {start_id} to {end_id}")

    try:
        await puller.run()
        logger.info("Order item pull job completed successfully")
    except Exception as e:
        logger.error(f"Order item pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
