"""
AsyncPuller: A generic asynchronous data puller with error handling and rate limiting.

This module defines an AsyncPuller class that fetches items from a given API endpoint.
It supports batch processing, retries on failure, rate limiting, and saving results to CSV.
The class is designed to be extended for specific data types with custom transformation logic.
"""

import asyncio
import aiohttp
import logging
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, TypeVar, Generic, Union, Tuple
from abc import ABC, abstractmethod

from scripts.utils.config_loader import config
from scripts.utils.utils import log_failures
from scripts.utils.async_token_bucket import AsyncTokenBucket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Type variable for the data type returned by the puller
T = TypeVar('T')

class AsyncPuller(Generic[T], ABC):
    """
    Abstract base class for asynchronous data pullers with error handling and rate limiting.

    This class provides a framework for fetching data from API endpoints with support for:
    - Rate limiting using token bucket algorithm
    - Automatic retries with exponential backoff
    - Batch processing of requests
    - Error logging and tracking
    - CSV output

    Subclasses must implement the transform_data method to convert raw API data
    to the desired output format.
    """

    def __init__(
            self,
            endpoint: str,
            rate: float = 1.0,
            capacity: int = 5,
            max_retries: int = 3,
            batch_size: int = 50,
            base_url: Optional[str] = None,
            api_key: Optional[str] = None
    ):
        """
        Initialize the async puller.

        Args:
            endpoint: API endpoint to pull from (without base URL)
            rate: Rate limit in requests per second
            capacity: Maximum burst capacity for rate limiting
            max_retries: Maximum number of retry attempts for failed requests
            batch_size: Number of items to process in parallel
            base_url: Base URL for the API (defaults to config["api_base_url"])
            api_key: API key for authentication (defaults to config["api_key"])
        """
        self.base_url = base_url or config["api_base_url"]
        self.api_key = api_key or config["api_key"]
        self.endpoint = endpoint
        self.headers = {"Authorization": f"API-Token {self.api_key}"}
        self.max_retries = max_retries
        self.batch_size = batch_size

        # Initialize rate limiter
        self.bucket = AsyncTokenBucket(rate=rate, capacity=capacity)

        # Statistics
        self.processed_count = 0
        self.failed_ids = []

    async def fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single item with retry logic.

        Args:
            session: aiohttp client session
            item_id: ID of the item to fetch

        Returns:
            Dict containing item data or None if failed after retries
        """
        url = f"{self.base_url}/{self.endpoint}/{item_id}"
        delay = 1  # Initial delay for exponential backoff

        for attempt in range(self.max_retries):
            try:
                # Wait for rate limiting token
                async with self.bucket:
                    async with session.get(url, headers=self.headers, timeout=10) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            logger.warning(f"Item {item_id} not found")
                            return None
                        elif response.status == 429:
                            logger.warning(f"Rate limit hit for item {item_id}, pausing")
                            await asyncio.sleep(15)  # Longer pause for rate limiting
                        else:
                            logger.error(f"Error {response.status} fetching item {item_id}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching item {item_id} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Error fetching item {item_id} (attempt {attempt + 1}): {str(e)}")

            # Don't sleep after the last attempt
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        return None

    @abstractmethod
    def transform_data(self, data: Dict[str, Any]) -> T:
        """
        Transform raw API data into the desired output format.

        This method must be implemented by subclasses to convert the raw API
        response into the format needed for output.

        Args:
            data: Raw data from the API

        Returns:
            Transformed data in the format specified by the type parameter T
        """
        pass

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        By default, saves to data_raw/<endpoint>/<endpoint>.csv
        Subclasses can override this to customize the output path.

        Returns:
            Path to the output CSV file
        """
        endpoint_name = self.endpoint.replace('/', '_')
        return f"data_raw/{endpoint_name}/{endpoint_name}.csv"

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of item IDs to process.

        By default, returns None for both start and end, meaning all items.
        Subclasses can override this to customize the range.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return None, None

    async def process_batch(self, batch_ids: List[int]) -> List[T]:
        """
        Process a batch of items concurrently.

        Args:
            batch_ids: List of item IDs to process

        Returns:
            List of successfully processed items
        """
        batch_items = []

        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_item(session, item_id) for item_id in batch_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for item_id, result in zip(batch_ids, results):
                if isinstance(result, Exception):
                    logger.error(f"Exception processing item {item_id}: {result}")
                    self.failed_ids.append(item_id)
                elif result is None:
                    self.failed_ids.append(item_id)
                else:
                    try:
                        transformed = self.transform_data(result)
                        batch_items.append(transformed)
                        self.processed_count += 1
                    except Exception as e:
                        logger.error(f"Error transforming item {item_id}: {str(e)}")
                        self.failed_ids.append(item_id)

        return batch_items

    def save_to_csv(self, items: List[T], output_path: str) -> None:
        """
        Save items to CSV file.

        Args:
            items: List of items to save
            output_path: Path to the output CSV file
        """
        if not items:
            logger.warning("No items to save")
            return

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Get fieldnames from the first item
        fieldnames = list(items[0].keys())

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(items)

        logger.info(f"Saved {len(items)} items to {output_path}")

    async def run(self) -> None:
        """
        Run the puller to fetch and process all items in the specified range.

        This method orchestrates the entire pull process:
        1. Determines the item IDs to process
        2. Processes items in batches
        3. Saves results to CSV
        4. Logs failures
        """
        start_id, end_id = self.get_item_range()
        output_path = self.get_output_path()

        # Determine item IDs to process
        if start_id is not None and end_id is not None:
            item_ids = list(range(start_id, end_id + 1))
            logger.info(f"Processing items {start_id} to {end_id}")
        else:
            # If no range is specified, fetch all items
            # This would need to be implemented by subclasses for pagination
            logger.info("Processing all items")
            item_ids = await self.get_all_item_ids()

        if not item_ids:
            logger.warning("No items to process")
            return

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
            self.save_to_csv(all_items, output_path)

        # Log failures
        if self.failed_ids:
            endpoint_name = self.endpoint.replace('/', '_')
            log_failures(f"logs/errors/failed_{endpoint_name}.txt", self.failed_ids)
            logger.warning(f"Failed to process {len(self.failed_ids)} items")

        logger.info(f"Pull complete. Processed {self.processed_count} items, "
                   f"failed {len(self.failed_ids)} items.")

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all item IDs to process when no range is specified.

        By default, this method raises NotImplementedError.
        Subclasses should override this method if they support fetching all items.

        Returns:
            List of all item IDs to process

        Raises:
            NotImplementedError: If the subclass doesn't implement this method
        """
        raise NotImplementedError(
            "Fetching all items is not implemented. "
            "Either specify a range using get_item_range() or "
            "override get_all_item_ids() in your subclass."
        )
