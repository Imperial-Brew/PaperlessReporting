"""
Asynchronous puller for revised quote data from the API.

This script fetches revised quotes (quotes with revision > 0) from the API and transforms them
into a structured format, saving the results to a CSV file.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

import aiohttp

from utils.async_puller import AsyncPuller
from utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class RevQuotesPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for revised quote data.

    This class extends AsyncPuller to fetch revised quotes from the API
    and transform them into a structured format with selected fields.
    It uses the quotes/public/new endpoint to get quote/revision pairs,
    then fetches each quote with its revision.
    """

    def __init__(self, batch_start: Optional[int] = None, batch_end: Optional[int] = None):
        """
        Initialize the RevQuotesPuller.

        Args:
            batch_start: Optional starting index for batch processing
            batch_end: Optional ending index for batch processing
        """
        super().__init__(
            endpoint="quotes/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=20  # Process 20 quotes at a time
        )
        self.batch_start = batch_start
        self.batch_end = batch_end
        self.quote_revision_pairs = []

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

                    # Apply batch limits if specified
                    if self.batch_start is not None and self.batch_end is not None:
                        return pairs[self.batch_start:self.batch_end + 1]
                    return pairs
                else:
                    logger.error(f"Failed to fetch quote revisions: {response.status}")
                    return []

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw quote data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested contact, customer, and salesperson information.

        Args:
            data: Raw quote data from the API

        Returns:
            Transformed quote data with selected fields
        """
        # Extract the revision from the URL parameters
        revision = self.current_revision

        return {
            "quote_id": f"{data.get('number')}-{revision}",
            "quote_number": data.get("number"),
            "revision_number": revision,
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

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on the batch range if specified.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.batch_start is not None and self.batch_end is not None:
            return str(project_root / f"data_raw/quotes/quotes_revised_{self.batch_start}_{self.batch_end}.csv")
        return str(project_root / "data_raw/quotes/quotes_revised.csv")

    async def fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single quote with its revision.

        This method is overridden to handle the special case of fetching quotes with revisions.
        The item_id is actually a tuple index into the quote_revision_pairs list.

        Args:
            session: aiohttp client session
            item_id: Index into the quote_revision_pairs list

        Returns:
            Dict containing quote data or None if failed after retries
        """
        if item_id >= len(self.quote_revision_pairs):
            logger.error(f"Item ID {item_id} out of range")
            return None

        quote_number, revision = self.quote_revision_pairs[item_id]
        self.current_revision = revision  # Store for use in transform_data

        url = f"{self.base_url}/{self.endpoint}/{quote_number}?revision={revision}"
        delay = 1  # Initial delay for exponential backoff

        for attempt in range(self.max_retries):
            try:
                # Wait for rate limiting token
                async with self.bucket:
                    async with session.get(url, headers=self.headers, timeout=10) as response:
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

    async def run(self) -> None:
        """
        Run the puller to fetch and process all revised quotes.

        This method overrides the base class method to handle the special case
        of fetching quotes with revisions.
        """
        # Get all quote/revision pairs
        self.quote_revision_pairs = await self.get_all_revisions()
        if not self.quote_revision_pairs:
            logger.warning("No revised quotes found")
            return

        logger.info(f"Found {len(self.quote_revision_pairs)} revised quotes")

        # Create item IDs as indices into the quote_revision_pairs list
        item_ids = list(range(len(self.quote_revision_pairs)))

        all_items = []

        # Process in batches
        for i in range(0, len(item_ids), self.batch_size):
            batch = item_ids[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(item_ids) + self.batch_size - 1) // self.batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches}, items {i} to {i + len(batch) - 1}")
            batch_items = await self.process_batch(batch)
            all_items.extend(batch_items)

            # Log progress
            logger.info(f"Batch {batch_num}/{total_batches} complete. "
                        f"Processed {self.processed_count}/{len(item_ids)} items "
                        f"({self.processed_count/len(item_ids)*100:.1f}%)")

        # Save results
        if all_items:
            self.save_to_csv(all_items, self.get_output_path())

        # Log failures
        if self.failed_ids:
            # Convert failed indices back to quote-revision pairs for logging
            failed_pairs = [f"{self.quote_revision_pairs[idx][0]}-{self.quote_revision_pairs[idx][1]}" 
                           for idx in self.failed_ids if idx < len(self.quote_revision_pairs)]
            # Use absolute path to project root directory
            project_root = Path(__file__).parent.parent
            log_path = str(project_root / "logs/errors/failed_revised_quotes.txt")
            with open(log_path, "w") as f:
                for pair in failed_pairs:
                    f.write(f"{pair}\n")
            logger.warning(f"Failed to process {len(failed_pairs)} quotes")

        logger.info(f"Pull complete. Processed {self.processed_count} quotes, "
                   f"failed {len(self.failed_ids)} quotes.")

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a RevQuotesPuller instance,
    and runs it to fetch revised quote data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch revised quote data from the API")
    parser.add_argument("--batch-start", type=int, help="Starting index for batch processing")
    parser.add_argument("--batch-end", type=int, help="Ending index for batch processing")
    args = parser.parse_args()

    batch_start = args.batch_start
    batch_end = args.batch_end

    # Validate arguments
    if (batch_start is not None and batch_end is None) or (batch_start is None and batch_end is not None):
        logger.error("Both --batch-start and --batch-end must be specified together")
        return

    puller = RevQuotesPuller(batch_start, batch_end)
    batch_range = f"{batch_start} to {batch_end}" if batch_start is not None else "all"
    logger.info(f"Starting revised quote pull job: batch {batch_range}")

    try:
        await puller.run()
        logger.info("Revised quote pull job completed successfully")
    except Exception as e:
        logger.error(f"Revised quote pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
