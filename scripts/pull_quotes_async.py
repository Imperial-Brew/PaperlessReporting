"""
Asynchronous puller for quote and quote item data from the API.

This script fetches quote data from the API and transforms it into two structured formats:
1. Quote-level data saved to quotes.csv
2. Quote item-level data saved to quote_items.csv
It supports fetching a specific range of quote IDs.
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

class QuotesPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for quote and quote item data.

    This class extends AsyncPuller to fetch quote data from the API
    and transform it into two structured formats:
    1. Quote-level data with selected fields
    2. Quote item-level data with selected fields
    It supports fetching a specific range of quote IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the QuotesPuller.

        Args:
            start_id: Optional starting ID for range of quotes to fetch
            end_id: Optional ending ID for range of quotes to fetch
        """
        super().__init__(
            endpoint="quotes/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=20  # Process 20 quotes at a time
        )
        self.start_id = start_id
        self.end_id = end_id
        self.quote_items = []  # Store quote items separately

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw quote data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested customer, salesperson, pricing, and payment information.
        Also extracts quote item data and stores it separately.

        Args:
            data: Raw quote data from the API

        Returns:
            Transformed quote data with selected fields
        """
        # Process quote items if they exist
        if "quote_items" in data and isinstance(data["quote_items"], list):
            quote_items_count = len(data["quote_items"])
            logger.debug(f"Quote {data.get('number')} has {quote_items_count} quote items")
            quote_number = data.get("number")

            for item in data["quote_items"]:
                # Extract the root component
                root = next((c for c in item.get("components", []) if c.get("is_root_component")), {})
                part_number = root.get("part_number", "")
                part_uuid = root.get("part_uuid", "")
                description = root.get("description", "")
                revision = root.get("revision", "")
                material = safe_get(root, "material", "name") or ""
                process = safe_get(root, "process", "name") or ""
                is_fully_configured = all([part_number, description, material, process])

                # Create base row with common fields
                base_row = {
                    "quote_number": quote_number,
                    "item_id": item.get("id"),
                    "workflow_status": item.get("workflow_status"),
                    "part_number": part_number,
                    "revision": revision,
                    "description": description,
                    "type": root.get("type", ""),
                    "material": material,
                    "process": process,
                    "is_fully_configured": is_fully_configured,
                    "part_uuid": part_uuid,
                    "export_controlled": item.get("export_controlled")
                }

                # Handle quantities - each quantity creates a separate row
                quantities = root.get("quantities", [])
                if quantities:
                    for q in quantities:
                        row = base_row.copy()
                        row.update({
                            "quantity": q.get("quantity"),
                            "unit_price": q.get("unit_price"),
                            "total_price": q.get("total_price"),
                            "total_price_with_add_ons": q.get("total_price_with_required_add_ons"),
                            "lead_time": q.get("lead_time")
                        })
                        self.quote_items.append(row)
                else:
                    # If no quantities, still add the base row
                    self.quote_items.append(base_row)
        elif "quote_items" in data:
            logger.warning(f"Quote {data.get('number')} has 'quote_items' but it's not a list: {type(data['quote_items'])}")

        # Return quote-level data
        return {
            "quote_number": data.get("number"),
            "status": data.get("status"),
            "created": data.get("created"),
            "due_date": data.get("due_date"),
            "sent_date": data.get("sent_date"),
            "expired_date": data.get("expired_date"),
            "expired": data.get("expired"),
            "rfq_number": data.get("rfq_number"),
            "priority": data.get("priority"),
            "private_notes": data.get("private_notes"),
            "authenticated_pdf_quote_url": data.get("authenticated_pdf_quote_url"),
            "contact_name": (safe_get(data, "contact", "first_name") or "") + " " + (
                    safe_get(data, "contact", "last_name") or ""),
            "contact_email": safe_get(data, "contact", "email"),
            "customer_name": safe_get(data, "contact", "account", "name"),
            "estimator_email": safe_get(data, "estimator", "email"),
            "salesperson_email": safe_get(data, "salesperson", "email")
        }

    def get_quotes_output_path(self) -> str:
        """
        Generate the output path for the quotes CSV file.

        Returns a path based on the range of quotes being fetched.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/quotes/quotes_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/quotes/quotes_all.csv")

    def get_quote_items_output_path(self) -> str:
        """
        Generate the output path for the quote items CSV file.

        Returns a path based on the range of quotes being fetched.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/quote_items/quote_items_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/quote_items/quote_items_all.csv")

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        This is required by the AsyncPuller base class but we'll override
        the save_to_csv method to handle both output files.

        Returns:
            Path to the quotes output CSV file
        """
        return self.get_quotes_output_path()

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of quote IDs to process.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all quote IDs to process when no range is specified.

        This implementation uses pagination to fetch all quote IDs from the API.

        Returns:
            List of all quote IDs to process
        """
        # This is a placeholder implementation
        # In a real implementation, you would fetch all quote IDs from the API
        # using pagination
        logger.warning("Fetching all quotes is not yet implemented")
        logger.warning("Please specify a range using --start-id and --end-id")
        return []

    async def run(self) -> None:
        """
        Run the puller to fetch and process all quotes in the specified range.

        This method overrides the base class run method to save both
        quotes and quote items to separate CSV files.
        """
        # Reset quote items list
        self.quote_items = []

        # Run the standard pull process
        await super().run()

        # Save quote items to CSV
        if self.quote_items:
            quote_items_path = self.get_quote_items_output_path()

            # Ensure output directory exists
            Path(quote_items_path).parent.mkdir(parents=True, exist_ok=True)

            # Get fieldnames from the first item
            fieldnames = list(self.quote_items[0].keys())

            with open(quote_items_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.quote_items)

            logger.info(f"Saved {len(self.quote_items)} quote items to {quote_items_path}")
        else:
            logger.warning("No quote items found in the quotes data")

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a QuotesPuller instance,
    and runs it to fetch quote and quote item data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch quote and quote item data from the API")
    parser.add_argument("--start-id", type=int, help="Starting quote ID", default=7500)
    parser.add_argument("--end-id", type=int, help="Ending quote ID", default=7550)
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    # Fetch quotes and extract quote items
    quotes_puller = QuotesPuller(start_id, end_id)
    logger.info(f"Starting quote pull job: {start_id} to {end_id}")

    try:
        await quotes_puller.run()
        logger.info("Quote pull job completed successfully")
    except Exception as e:
        logger.error(f"Quote pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
