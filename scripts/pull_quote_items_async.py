"""
Asynchronous puller for quote item data from the API.

This script fetches quote item data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching a specific range of quote item IDs.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class QuoteItemsPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for quote item data.

    This class extends AsyncPuller to fetch quote item data from the API
    and transform it into a structured format with selected fields.
    It supports fetching a specific range of quote item IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the QuoteItemsPuller.

        Args:
            start_id: Optional starting ID for range of quote items to fetch
            end_id: Optional ending ID for range of quote items to fetch
        """
        super().__init__(
            endpoint="quote-items/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=50  # Process 50 quote items at a time
        )
        self.start_id = start_id
        self.end_id = end_id

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw quote item data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested quote, pricing, material, and finish information.

        Args:
            data: Raw quote item data from the API

        Returns:
            Transformed quote item data with selected fields
        """
        return {
            "quote_item_id": data.get("id"),
            "quote_number": safe_get(data, "quote", "number"),
            "part_number": data.get("part_number"),
            "description": data.get("description"),
            "quantity": data.get("quantity"),
            "unit_price": safe_get(data, "pricing", "unit_price"),
            "total_price": safe_get(data, "pricing", "total_price"),
            "currency": safe_get(data, "pricing", "currency"),
            "material": safe_get(data, "material", "name"),
            "finish": safe_get(data, "finish", "name"),
            "lead_time_days": data.get("lead_time_days"),
            "notes": data.get("notes")
        }

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on the range of quote items being fetched.

        Returns:
            Path to the output CSV file
        """
        if self.start_id is not None and self.end_id is not None:
            return f"data_raw/quote_items/quote_items_{self.start_id}_{self.end_id}.csv"
        return "data_raw/quote_items/quote_items_all.csv"

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of quote item IDs to process.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all quote item IDs to process when no range is specified.

        This implementation uses pagination to fetch all quote item IDs from the API.

        Returns:
            List of all quote item IDs to process
        """
        # This is a placeholder implementation
        # In a real implementation, you would fetch all quote item IDs from the API
        # using pagination
        logger.warning("Fetching all quote items is not yet implemented")
        logger.warning("Please specify a range using --start-id and --end-id")
        return []

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a QuoteItemsPuller instance,
    and runs it to fetch quote item data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch quote item data from the API")
    parser.add_argument("--start-id", type=int, help="Starting quote item ID", default=1)
    parser.add_argument("--end-id", type=int, help="Ending quote item ID", default=100)
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    puller = QuoteItemsPuller(start_id, end_id)
    logger.info(f"Starting quote item pull job: {start_id} to {end_id}")

    try:
        await puller.run()
        logger.info("Quote item pull job completed successfully")
    except Exception as e:
        logger.error(f"Quote item pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
