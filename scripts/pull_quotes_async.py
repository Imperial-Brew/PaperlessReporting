"""
Asynchronous puller for quote and quote item data from the API.

This script fetches quote data from the API and transforms it into two structured formats:
1. Quote-level data saved to quotes.csv
2. Quote item-level data saved to quote_items.csv
It supports fetching a specific range of quote IDs and includes revised quotes.
"""

import asyncio
import logging
import argparse
import csv
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import aiohttp

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

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None, include_revisions: bool = True):
        """
        Initialize the QuotesPuller.

        Args:
            start_id: Optional starting ID for range of quotes to fetch
            end_id: Optional ending ID for range of quotes to fetch
            include_revisions: Whether to include revised quotes (quotes with revision > 0)
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
        self.include_revisions = include_revisions
        self.current_revision = None  # For revised quotes
        self.quote_revision_pairs = []  # For storing quote/revision pairs

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
                    "quote_revision": self.current_revision,  # Will be None for regular quotes
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
            "revision_number": self.current_revision,  # Will be None for regular quotes
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

    async def get_all_revisions(self) -> List[Tuple[int, int]]:
        """
        Get all quote/revision pairs with revision > 0.

        Returns:
            List of tuples containing (quote_number, revision_number)
        """
        url = f"{self.base_url}/quotes/public/new"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    pairs = [(q["quote"], q["revision"]) for q in data if q["revision"] not in (None, 0)]

                    logger.info(f"Found {len(pairs)} revised quotes")

                    return pairs
                else:
                    logger.error(f"Failed to fetch quote revisions: {response.status}")
                    return []

    async def fetch_item_with_revision(self, session: aiohttp.ClientSession, quote_number: int, revision: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single quote with its revision.

        Args:
            session: aiohttp client session
            quote_number: Quote number to fetch
            revision: Revision number to fetch

        Returns:
            Dict containing quote data or None if failed after retries
        """
        self.current_revision = revision  # Store for use in transform_data

        url = f"{self.base_url}/{self.endpoint}/{quote_number}?revision={revision}"
        delay = 1  # Initial delay for exponential backoff

        for attempt in range(self.max_retries):
            try:
                # Wait for rate limiting token
                async with self.bucket:
                    async with session.get(url, headers=self.headers, timeout=20) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            logger.warning(f"Quote {quote_number}-r{revision} not found")
                            return None
                        elif response.status == 429:
                            logger.warning(f"Rate limit hit for quote {quote_number}-r{revision}, pausing")
                            await asyncio.sleep(15)  # Longer pause for rate limiting
                        else:
                            logger.error(f"Error {response.status} fetching quote {quote_number}-r{revision}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching quote {quote_number}-r{revision} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Error fetching quote {quote_number}-r{revision} (attempt {attempt + 1}): {str(e)}")

            # Don't sleep after the last attempt
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        return None

    async def process_revised_quotes(self) -> List[Dict[str, Any]]:
        """
        Process revised quotes.

        Fetches and processes all revised quotes, extracting both quote-level data
        and quote item data.

        Returns:
            List of transformed quote data
        """
        logger.info("Processing revised quotes")

        # Get all quote/revision pairs
        self.quote_revision_pairs = await self.get_all_revisions()
        if not self.quote_revision_pairs:
            logger.warning("No revised quotes found")
            return []

        logger.info(f"Found {len(self.quote_revision_pairs)} revised quotes")

        all_quotes = []

        # Process in batches
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(self.quote_revision_pairs), self.batch_size):
                batch = self.quote_revision_pairs[i:i + self.batch_size]
                batch_num = i // self.batch_size + 1
                total_batches = (len(self.quote_revision_pairs) + self.batch_size - 1) // self.batch_size

                logger.info(f"Processing batch {batch_num}/{total_batches} of revised quotes")

                batch_quotes = []
                for quote_number, revision in batch:
                    quote_data = await self.fetch_item_with_revision(session, quote_number, revision)
                    if quote_data:
                        try:
                            transformed_data = self.transform_data(quote_data)
                            batch_quotes.append(transformed_data)
                            logger.debug(f"Processed revised quote {quote_number}-r{revision}")
                        except Exception as e:
                            logger.error(f"Error transforming revised quote {quote_number}-r{revision}: {str(e)}")

                all_quotes.extend(batch_quotes)
                logger.info(f"Processed {len(batch_quotes)} revised quotes in batch {batch_num}/{total_batches}")

        logger.info(f"Processed {len(all_quotes)} revised quotes in total")
        return all_quotes

    async def run(self) -> None:
        """
        Run the puller to fetch and process all quotes in the specified range.

        This method overrides the base class run method to save both
        quotes and quote items to separate CSV files, and to include revised quotes.
        """
        # Reset quote items list
        self.quote_items = []
        all_quotes = []

        # Process regular quotes if a range is specified
        if self.start_id is not None and self.end_id is not None:
            logger.info(f"Processing regular quotes from {self.start_id} to {self.end_id}")

            # Set current_revision to None for regular quotes
            self.current_revision = None

            # Run the standard pull process for regular quotes
            # We'll override the save_to_csv method to collect the quotes instead of saving them
            original_save_to_csv = self.save_to_csv

            def collect_quotes(items, output_path):
                nonlocal all_quotes
                all_quotes.extend(items)
                logger.info(f"Collected {len(items)} regular quotes")

            # Replace save_to_csv with our collector function
            self.save_to_csv = collect_quotes

            # Run the standard pull process
            await super().run()

            # Restore the original save_to_csv method
            self.save_to_csv = original_save_to_csv

        # Process revised quotes if enabled
        if self.include_revisions:
            revised_quotes = await self.process_revised_quotes()
            all_quotes.extend(revised_quotes)

        # Save all quotes to CSV
        if all_quotes:
            quotes_path = self.get_quotes_output_path()

            # Ensure output directory exists
            Path(quotes_path).parent.mkdir(parents=True, exist_ok=True)

            # Get fieldnames from the first item
            fieldnames = list(all_quotes[0].keys())

            with open(quotes_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_quotes)

            logger.info(f"Saved {len(all_quotes)} quotes to {quotes_path}")
        else:
            logger.warning("No quotes found to save")

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
    parser.add_argument("--no-revisions", action="store_true", help="Exclude revised quotes")
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id
    include_revisions = not args.no_revisions

    # Validate arguments
    if start_id > end_id:
        logger.error(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")
        return

    # Fetch quotes and extract quote items
    quotes_puller = QuotesPuller(start_id, end_id, include_revisions)
    logger.info(f"Starting quote pull job: {start_id} to {end_id}, include_revisions={include_revisions}")

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
