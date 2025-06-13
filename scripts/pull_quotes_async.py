"""
Asynchronous puller for quote and quote item data from the API.

This script fetches quote data from the API and transforms it into two structured formats:
1. Quote-level data saved to quotes.csv
2. Quote item-level data saved to quote_items.csv
It supports fetching a specific range of quote IDs and includes revised quotes.
"""

import asyncio
import argparse
import csv
import os
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

import aiohttp

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get
from scripts.utils.logging_config import configure_logging, get_logger, with_correlation_id, LogContext
from scripts.utils.exceptions import (
    APIError, RateLimitError, DataProcessingError, PaperlessError
)

# Get logger for this module
logger = get_logger(__name__)

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
                    "quote_number": str(quote_number),  # Convert to string
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
                        # Convert numeric fields to appropriate types
                        try:
                            unit_price = float(q.get("unit_price", 0))
                            total_price = float(q.get("total_price", 0))
                            total_price_with_add_ons = float(q.get("total_price_with_required_add_ons", 0))
                        except (ValueError, TypeError):
                            # If conversion fails, use default values
                            unit_price = 0.0
                            total_price = 0.0
                            total_price_with_add_ons = 0.0

                        row.update({
                            "quantity": q.get("quantity"),
                            "unit_price": unit_price,
                            "total_price": total_price,
                            "total_price_with_add_ons": total_price_with_add_ons,
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
        # Use the PaperlessPartsClient to fetch quote revisions
        from scripts.utils.paperless_client import PaperlessPartsClient

        client = PaperlessPartsClient(
            rate=self.bucket.rate,
            capacity=self.bucket.capacity,
            max_retries=self.max_retries
        )

        try:
            data = await client.get_quote_revisions()
            if data:
                pairs = [(q["quote"], q["revision"]) for q in data if q["revision"] not in (None, 0)]
                logger.info(f"Found {len(pairs)} revised quotes")
                return pairs
            else:
                logger.error("Failed to fetch quote revisions")
                return []
        except Exception as e:
            logger.error(f"Error fetching quote revisions: {str(e)}")
            return []

    @with_correlation_id
    async def fetch_item_with_revision(self, session: aiohttp.ClientSession, quote_number: int, revision: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single quote with its revision.

        Args:
            session: aiohttp client session (not used with client, kept for backward compatibility)
            quote_number: Quote number to fetch
            revision: Revision number to fetch

        Returns:
            Dict containing quote data or None if failed after retries

        Raises:
            APIError: If there's an error communicating with the API
            RateLimitError: If the API rate limit is exceeded
        """
        # Add context information to logs
        with LogContext(operation="fetch_quote", quote_number=quote_number, revision=revision):
            self.current_revision = revision  # Store for use in transform_data

            # Use the PaperlessPartsClient to fetch quote with revision
            from scripts.utils.paperless_client import PaperlessPartsClient

            client = PaperlessPartsClient(
                rate=self.bucket.rate,
                capacity=self.bucket.capacity,
                max_retries=self.max_retries,
                timeout=20  # Use the same timeout as before
            )

            try:
                logger.debug(f"Fetching quote {quote_number}-r{revision}")
                data = await client.get_quote_with_revision(quote_number, revision)

                if data:
                    logger.debug(f"Successfully fetched quote {quote_number}-r{revision}")
                    return data
                else:
                    logger.warning(f"Quote {quote_number}-r{revision} not found")
                    return None
            except Exception as e:
                error_msg = f"Error fetching quote {quote_number}-r{revision}: {str(e)}"
                logger.error(error_msg, extra={"exception": str(e), "traceback": traceback.format_exc()})

                # Re-raise as APIError for consistent error handling
                raise APIError(
                    error_msg,
                    details={
                        "quote_number": quote_number,
                        "revision": revision,
                        "exception": str(e),
                        "exception_type": type(e).__name__
                    }
                )

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

@with_correlation_id
async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a QuotesPuller instance,
    and runs it to fetch quote and quote item data from the API.
    """
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description="Fetch quote and quote item data from the API")
        parser.add_argument("--start-id", type=int, help="Starting quote ID", default=7500)
        parser.add_argument("--end-id", type=int, help="Ending quote ID", default=7550)
        parser.add_argument("--no-revisions", action="store_true", help="Exclude revised quotes")
        parser.add_argument("--log-level", type=str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                           help="Logging level", default=os.getenv("LOG_LEVEL", "INFO"))
        parser.add_argument("--log-file", type=str, help="Log file path", default=os.getenv("LOG_FILE"))
        parser.add_argument("--json-logs", action="store_true", help="Output logs in JSON format")
        args = parser.parse_args()

        start_id = args.start_id
        end_id = args.end_id
        include_revisions = not args.no_revisions

        # Add context information to logs
        with LogContext(operation="pull_quotes", start_id=start_id, end_id=end_id, include_revisions=include_revisions):
            # Validate arguments
            if start_id > end_id:
                raise ValueError(f"Start ID ({start_id}) must be less than or equal to End ID ({end_id})")

            # Fetch quotes and extract quote items
            quotes_puller = QuotesPuller(start_id, end_id, include_revisions)
            logger.info(f"Starting quote pull job: {start_id} to {end_id}, include_revisions={include_revisions}")

            try:
                await quotes_puller.run()
                logger.info("Quote pull job completed successfully")
            except APIError as e:
                logger.error(f"API error during quote pull job: {e.message}", extra={"details": e.details})
                raise
            except DataProcessingError as e:
                logger.error(f"Data processing error during quote pull job: {e.message}", extra={"details": e.details})
                raise
            except PaperlessError as e:
                logger.error(f"Error during quote pull job: {e.message}", extra={"details": e.details})
                raise
            except Exception as e:
                # Catch any unexpected exceptions
                error_details = {
                    "exception_type": type(e).__name__,
                    "traceback": traceback.format_exc()
                }
                logger.error(f"Unexpected error during quote pull job: {str(e)}", extra={"details": error_details})
                raise
    except Exception as e:
        # Log any exceptions that weren't caught earlier
        if not isinstance(e, PaperlessError):
            logger.error(f"Unhandled exception: {str(e)}", extra={"traceback": traceback.format_exc()})
        # Re-raise to ensure non-zero exit code
        raise

if __name__ == "__main__":
    # Configure centralized logging
    configure_logging(
        level=os.getenv("LOG_LEVEL", "INFO"),
        use_json=os.getenv("LOG_FORMAT", "").lower() == "json",
        log_file=os.getenv("LOG_FILE")
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Quote pull job interrupted by user")
    except Exception:
        # Exception details already logged in main()
        import sys
        sys.exit(1)
