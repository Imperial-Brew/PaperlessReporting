"""
Asynchronous puller for order and order item data from the API.

This script fetches order data from the API and transforms it into two structured formats:
1. Order-level data saved to orders.csv
2. Order item-level data saved to order_items.csv
It supports fetching a specific range of order IDs.
"""

import asyncio
import logging
import argparse
import csv
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from utils.async_puller import AsyncPuller
from utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class OrdersPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for order and order item data.

    This class extends AsyncPuller to fetch order data from the API
    and transform it into two structured formats:
    1. Order-level data with selected fields
    2. Order item-level data with selected fields
    It supports fetching a specific range of order IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the OrdersPuller.

        Args:
            start_id: Optional starting ID for range of orders to fetch
            end_id: Optional ending ID for range of orders to fetch
        """
        super().__init__(
            endpoint="orders/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=20  # Process 20 orders at a time (orders have more data)
        )
        self.start_id = start_id
        self.end_id = end_id
        self.order_items = []  # Store order items separately

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw order data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested payment and shipping information.
        Also extracts order item data and stores it separately.

        Args:
            data: Raw order data from the API

        Returns:
            Transformed order data with selected fields
        """
        # Process order items if they exist
        order_number = data.get("number")
        items = data.get("order_items", [])

        if items and isinstance(items, list):
            items_count = len(items)
            logger.debug(f"Order {order_number} has {items_count} order items")

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

                self.order_items.append({
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
        elif "order_items" in data:
            logger.warning(f"Order {order_number} has 'order_items' but it's not a list: {type(data['order_items'])}")

        # Return order-level data
        return {
            "order_number": order_number,
            "quote_number": data.get("quote_number"),
            "quote_revision_number": data.get("quote_revision_number"),
            "status": data.get("status"),
            "created": data.get("created"),
            "deliver_by": data.get("deliver_by"),
            "ships_on": data.get("ships_on"),
            "payment_terms": safe_get(data, "payment_details", "payment_terms"),
            "purchase_order_number": safe_get(data, "payment_details", "purchase_order_number"),
            "salesperson_email": safe_get(data, "salesperson", "email"),
            "customer_name": safe_get(data, "shipping_info", "business_name")
        }

    def get_orders_output_path(self) -> str:
        """
        Generate the output path for the orders CSV file.

        Returns a path based on the range of orders being fetched.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/orders/orders_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/orders/orders_all.csv")

    def get_order_items_output_path(self) -> str:
        """
        Generate the output path for the order items CSV file.

        Returns a path based on the range of orders being fetched.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/order_items/order_items_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/order_items/order_items_all.csv")

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        This is required by the AsyncPuller base class but we'll override
        the save_to_csv method to handle both output files.

        Returns:
            Path to the orders output CSV file
        """
        return self.get_orders_output_path()

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

    async def run(self) -> None:
        """
        Run the puller to fetch and process all orders in the specified range.

        This method overrides the base class run method to save both
        orders and order items to separate CSV files.
        """
        # Reset order items list
        self.order_items = []

        # Run the standard pull process
        await super().run()

        # Save order items to CSV
        if self.order_items:
            order_items_path = self.get_order_items_output_path()

            # Ensure output directory exists
            Path(order_items_path).parent.mkdir(parents=True, exist_ok=True)

            # Get fieldnames from the first item
            fieldnames = list(self.order_items[0].keys())

            with open(order_items_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.order_items)

            logger.info(f"Saved {len(self.order_items)} order items to {order_items_path}")
        else:
            logger.warning("No order items found in the orders data")

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates an OrdersPuller instance,
    and runs it to fetch order and order item data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch order and order item data from the API")
    parser.add_argument("--start-id", type=int, help="Starting order ID", default=520)
    parser.add_argument("--end-id", type=int, help="Ending order ID", default=560)
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    # Fetch orders and extract order items
    orders_puller = OrdersPuller(start_id, end_id)
    logger.info(f"Starting order pull job: {start_id} to {end_id}")

    try:
        await orders_puller.run()
        logger.info("Order pull job completed successfully")
    except Exception as e:
        logger.error(f"Order pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
