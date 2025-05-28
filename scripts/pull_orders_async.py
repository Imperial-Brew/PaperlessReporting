"""
Asynchronous puller for order data from the API.

This script fetches order data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching a specific range of order IDs.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class OrdersPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for order data.

    This class extends AsyncPuller to fetch order data from the API
    and transform it into a structured format with selected fields.
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

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw order data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested payment and shipping information.

        Args:
            data: Raw order data from the API

        Returns:
            Transformed order data with selected fields
        """
        return {
            "order_number": data.get("number"),
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

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on the range of orders being fetched.

        Returns:
            Path to the output CSV file
        """
        if self.start_id is not None and self.end_id is not None:
            return f"data_raw/orders/orders_{self.start_id}_{self.end_id}.csv"
        return "data_raw/orders/orders_all.csv"

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

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates an OrdersPuller instance,
    and runs it to fetch order data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch order data from the API")
    parser.add_argument("--start-id", type=int, help="Starting order ID", default=520)
    parser.add_argument("--end-id", type=int, help="Ending order ID", default=560)
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    puller = OrdersPuller(start_id, end_id)
    logger.info(f"Starting order pull job: {start_id} to {end_id}")

    try:
        await puller.run()
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
