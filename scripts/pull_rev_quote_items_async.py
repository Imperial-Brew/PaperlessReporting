"""
Asynchronous puller for revised quote item data from the API.

This script fetches revised quote items (from quotes with revision > 0) from the API
and transforms them into a structured format, saving the results to a CSV file.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple

import aiohttp

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class RevQuoteItemsPuller(AsyncPuller[List[Dict[str, Any]]]):
    """
    Asynchronous puller for revised quote item data.

    This class extends AsyncPuller to fetch revised quotes from the API,
    extract the quote items, and transform them into a structured format.
    It uses the quotes/public/new endpoint to get quote/revision pairs,
    then fetches each quote with its revision and extracts its items.
    """

    def __init__(self, batch_start: Optional[int] = None, batch_end: Optional[int] = None):
        """
        Initialize the RevQuoteItemsPuller.

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

    def transform_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform raw quote data into quote items.

        Extracts quote items from the quote data and transforms each item
        into a structured format with selected fields.

        Args:
            data: Raw quote data from the API

        Returns:
            List of transformed quote items
        """
        quote_number = data.get("number")
        revision = self.current_revision
        quote_items = data.get("quote_items", [])
        rows = []

        for item in quote_items:
            root = next((c for c in item.get("components", []) if c.get("is_root_component")), {})
            part_number = root.get("part_number", "")
            part_uuid = root.get("part_uuid", "")
            description = root.get("description", "")
            revision_id = root.get("revision", "")
            material = safe_get(root, "material", "name") or ""
            process = safe_get(root, "process", "name") or ""
            is_fully_configured = all([part_number, description, material, process])

            base_row = {
                "quote_number": quote_number,
                "quote_revision": revision,
                "item_id": item.get("id"),
                "workflow_status": item.get("workflow_status"),
                "part_number": part_number,
                "revision": revision_id,
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
                    rows.append(row)
            else:
                # If no quantities, still add the base row
                rows.append(base_row)

        return rows

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on the batch range if specified.

        Returns:
            Path to the output CSV file
        """
        if self.batch_start is not None and self.batch_end is not None:
            return f"data_raw/quote_items/quote_items_revised_{self.batch_start}_{self.batch_end}.csv"
        return "data_raw/quote_items/quote_items_revised.csv"

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

    async def process_batch(self, batch_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Process a batch of quotes concurrently and extract their quote items.

        This method overrides the base class method to handle the special case
        of transform_data returning a list of items instead of a single item.

        Args:
            batch_ids: List of indices into the quote_revision_pairs list

        Returns:
            List of all quote items from the processed quotes
        """
        all_items = []

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_item(session, item_id) for item_id in batch_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item_id, result in zip(batch_ids, results):
                if isinstance(result, Exception):
                    logger.error(f"Exception processing quote {item_id}: {result}")
                    self.failed_ids.append(item_id)
                elif result is None:
                    self.failed_ids.append(item_id)
                else:
                    try:
                        # transform_data returns a list of items for this quote
                        quote_items = self.transform_data(result)
                        all_items.extend(quote_items)
                        # Count the quote as processed if we successfully extracted its items
                        self.processed_count += 1
                        
                        if item_id < len(self.quote_revision_pairs):
                            quote_number, revision = self.quote_revision_pairs[item_id]
                            logger.info(f"Extracted {len(quote_items)} items from quote {quote_number}-r{revision}")
                    except Exception as e:
                        if item_id < len(self.quote_revision_pairs):
                            quote_number, revision = self.quote_revision_pairs[item_id]
                            logger.error(f"Error transforming quote {quote_number}-r{revision}: {str(e)}")
                        else:
                            logger.error(f"Error transforming quote at index {item_id}: {str(e)}")
                        self.failed_ids.append(item_id)

        return all_items

    async def run(self) -> None:
        """
        Run the puller to fetch and process all revised quote items.

        This method overrides the base class method to handle the special case
        of fetching quotes with revisions and extracting multiple items per quote.
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

            logger.info(f"Processing batch {batch_num}/{total_batches}, quotes {i} to {i + len(batch) - 1}")
            batch_items = await self.process_batch(batch)
            all_items.extend(batch_items)

            # Log progress
            logger.info(f"Batch {batch_num}/{total_batches} complete. "
                        f"Processed {self.processed_count}/{len(item_ids)} quotes "
                        f"({self.processed_count/len(item_ids)*100:.1f}%), "
                        f"extracted {len(batch_items)} items")

        # Save results
        if all_items:
            self.save_to_csv(all_items, self.get_output_path())
            logger.info(f"Saved {len(all_items)} quote items to {self.get_output_path()}")
        else:
            logger.warning("No quote items found to save")

        # Log failures
        if self.failed_ids:
            # Convert failed indices back to quote-revision pairs for logging
            failed_pairs = [f"{self.quote_revision_pairs[idx][0]}-{self.quote_revision_pairs[idx][1]}" 
                           for idx in self.failed_ids if idx < len(self.quote_revision_pairs)]
            log_path = "logs/errors/failed_revised_quote_items.txt"
            with open(log_path, "w") as f:
                for pair in failed_pairs:
                    f.write(f"{pair}\n")
            logger.warning(f"Failed to process {len(failed_pairs)} quotes")

        logger.info(f"Pull complete. Processed {self.processed_count} quotes, "
                   f"failed {len(self.failed_ids)} quotes, "
                   f"extracted {len(all_items)} quote items.")

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a RevQuoteItemsPuller instance,
    and runs it to fetch revised quote item data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch revised quote item data from the API")
    parser.add_argument("--batch-start", type=int, help="Starting index for batch processing")
    parser.add_argument("--batch-end", type=int, help="Ending index for batch processing")
    args = parser.parse_args()

    batch_start = args.batch_start
    batch_end = args.batch_end

    # Validate arguments
    if (batch_start is not None and batch_end is None) or (batch_start is None and batch_end is not None):
        logger.error("Both --batch-start and --batch-end must be specified together")
        return

    puller = RevQuoteItemsPuller(batch_start, batch_end)
    batch_range = f"{batch_start} to {batch_end}" if batch_start is not None else "all"
    logger.info(f"Starting revised quote items pull job: batch {batch_range}")

    try:
        await puller.run()
        logger.info("Revised quote items pull job completed successfully")
    except Exception as e:
        logger.error(f"Revised quote items pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())