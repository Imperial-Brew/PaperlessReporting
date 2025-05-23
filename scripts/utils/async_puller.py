import asyncio
import aiohttp
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any, TypeVar, Generic, Union, AsyncIterator
from datetime import datetime
from tqdm import tqdm

from scripts.utils.config_loader import config
from scripts.utils.async_token_bucket import AsyncTokenBucket
from scripts.utils.utils import safe_get, log_failures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

T = TypeVar('T')  # Type variable for the data being pulled

class AsyncPuller(Generic[T]):
    """Base class for async data pulling with rate limiting and error handling."""
    
    def __init__(
        self,
        endpoint: str,
        rate: float = 1.8,
        capacity: int = 5,
        max_retries: int = 3,
        timeout: int = 10,
        batch_size: int = 100,
        max_concurrent: int = 10
    ):
        """
        Initialize the async puller.
        
        Args:
            endpoint: API endpoint to pull from
            rate: Rate limit tokens per second
            capacity: Maximum number of tokens
            max_retries: Maximum number of retry attempts
            timeout: Request timeout in seconds
            batch_size: Number of items to process in parallel
            max_concurrent: Maximum number of concurrent requests
        """
        self.endpoint = endpoint
        self.bucket = AsyncTokenBucket(rate=rate, capacity=capacity)
        self.max_retries = max_retries
        self.timeout = timeout
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.api_token = config["api_key"]
        self.base_url = config["api_base_url"]
        self.headers = {"Authorization": f"API-Token {self.api_token}"}
        
    async def fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[T]:
        """
        Fetch a single item with retry logic.
        
        Args:
            session: aiohttp client session
            item_id: ID of the item to fetch
            
        Returns:
            Item data or None if failed
        """
        delay = 1
        for attempt in range(self.max_retries):
            try:
                async with self.bucket:  # This will automatically acquire a token
                    url = f"{self.base_url}/{self.endpoint}/{item_id}"
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            return self.transform_data(data)
                        elif response.status == 429:
                            logger.warning(f"⏳ Rate limit hit for {self.endpoint} {item_id}, pausing 15s")
                            await asyncio.sleep(15)
                        else:
                            logger.error(f"⚠️ Failed to fetch {self.endpoint} {item_id}: {response.status}")
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Timeout fetching {self.endpoint} {item_id} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"⚠️ Error fetching {self.endpoint} {item_id} (attempt {attempt + 1}): {e}")
            
            await asyncio.sleep(delay)
            delay *= 2
        return None
    
    async def fetch_all_paginated(self, session: aiohttp.ClientSession) -> AsyncIterator[T]:
        """
        Fetch all items using pagination.
        
        Args:
            session: aiohttp client session
            
        Yields:
            Transformed items
        """
        url = f"{self.base_url}/{self.endpoint}"
        while url:
            try:
                async with self.bucket:
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        if response.status == 200:
                            data = await response.json()
                            for item in data.get("results", []):
                                yield self.transform_data(item)
                            url = data.get("next")
                        elif response.status == 429:
                            logger.warning(f"⏳ Rate limit hit, pausing 15s")
                            await asyncio.sleep(15)
                        else:
                            logger.error(f"⚠️ Failed to fetch page: {response.status}")
                            break
            except Exception as e:
                logger.error(f"⚠️ Error fetching page: {e}")
                break
    
    def transform_data(self, data: Dict[str, Any]) -> T:
        """
        Transform raw API data into the desired format.
        Override this method in subclasses.
        
        Args:
            data: Raw data from the API
            
        Returns:
            Transformed data
        """
        raise NotImplementedError("Subclasses must implement transform_data")
    
    async def process_items(self, item_ids: List[int], output_path: str) -> None:
        """
        Process a batch of items concurrently with progress bar.
        
        Args:
            item_ids: List of item IDs to process
            output_path: Path to write the CSV output
        """
        all_items = []
        failed = []
        
        # Process in batches to control memory usage
        for i in range(0, len(item_ids), self.batch_size):
            batch = item_ids[i:i + self.batch_size]
            
            async with aiohttp.ClientSession() as session:
                # Create tasks with progress bar
                tasks = [self.fetch_item(session, item_id) for item_id in batch]
                results = await asyncio.gather(*tasks)
                
                # Process results with progress bar
                for item_id, result in tqdm(
                    zip(batch, results),
                    total=len(batch),
                    desc=f"Fetching {self.endpoint} batch {i//self.batch_size + 1}"
                ):
                    if result is None:
                        failed.append(item_id)
                    else:
                        all_items.append(result)
        
        # Write to CSV
        if all_items:
            self.write_csv(all_items, output_path)
        else:
            logger.warning(f"⚠️ No {self.endpoint} found.")

        # Log failures
        if failed:
            log_failures(f"logs/errors/failed_{self.endpoint}.txt", failed)
            logger.warning(f"❌ Failed to fetch {len(failed)} {self.endpoint}")
    
    async def process_all_paginated(self, output_path: str) -> None:
        """
        Process all items using pagination.
        
        Args:
            output_path: Path to write the CSV output
        """
        all_items = []
        
        async with aiohttp.ClientSession() as session:
            # Create a progress bar
            pbar = tqdm(desc=f"Fetching all {self.endpoint}")
            
            # Process items as they come in
            async for item in self.fetch_all_paginated(session):
                all_items.append(item)
                pbar.update(1)
            
            pbar.close()
        
        # Write to CSV
        if all_items:
            self.write_csv(all_items, output_path)
        else:
            logger.warning(f"⚠️ No {self.endpoint} found.")
    
    def write_csv(self, items: List[T], output_path: str) -> None:
        """
        Write items to CSV file.
        
        Args:
            items: List of items to write
            output_path: Path to write the CSV
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=items[0].keys())
            writer.writeheader()
            writer.writerows(items)
        logger.info(f"✅ Wrote {len(items)} {self.endpoint} to {output_path}")
    
    async def run(self, start_id: Optional[int] = None, end_id: Optional[int] = None) -> None:
        """
        Run the puller.
        
        Args:
            start_id: Starting ID (if None, fetch all items)
            end_id: Ending ID (if None, fetch all items)
        """
        if start_id is None or end_id is None:
            # Fetch all items using pagination
            output_path = f"data_raw/{self.endpoint}/{self.endpoint}.csv"
            await self.process_all_paginated(output_path)
        else:
            # Fetch specific range
            item_ids = list(range(start_id, end_id + 1))
            output_path = f"data_raw/{self.endpoint}/{self.endpoint}_{start_id}_{end_id}.csv"
            await self.process_items(item_ids, output_path) 