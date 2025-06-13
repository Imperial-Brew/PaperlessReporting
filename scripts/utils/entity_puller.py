"""
EntityPuller: A generic base class for pulling entity data from the API.

This module defines an EntityPuller class that extends AsyncPuller to provide
common functionality for fetching different types of entities (accounts, contacts, etc.)
from the API. It implements common patterns like pagination, output path generation,
and range handling.
"""

import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, TypeVar, Generic
from urllib.parse import urlparse

from scripts.utils.async_puller import AsyncPuller

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for the entity type
T = TypeVar('T')

class EntityPuller(AsyncPuller[T], Generic[T]):
    """
    Generic base class for entity pullers.
    
    This class extends AsyncPuller to provide common functionality for
    fetching different types of entities from the API. Subclasses should
    implement entity-specific logic like transform_data.
    """
    
    def __init__(
        self,
        entity_type: str,
        endpoint: str,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        rate: float = 1.8,
        capacity: int = 5,
        batch_size: int = 50,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize the entity puller.
        
        Args:
            entity_type: Type of entity being pulled (e.g., "accounts", "contacts")
            endpoint: API endpoint to pull from (without base URL)
            start_id: Optional starting ID for range of entities to fetch
            end_id: Optional ending ID for range of entities to fetch
            rate: Rate limit in requests per second
            capacity: Maximum burst capacity for rate limiting
            batch_size: Number of items to process in parallel
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Timeout for API requests in seconds
        """
        super().__init__(
            endpoint=endpoint,
            rate=rate,
            capacity=capacity,
            batch_size=batch_size,
            max_retries=max_retries
        )
        self.entity_type = entity_type
        self.start_id = start_id
        self.end_id = end_id
        self.timeout = timeout
    
    async def fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single item with retry logic and configurable timeout.
        
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
                    # Use the configured timeout
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            logger.warning(f"{self.entity_type.capitalize()} {item_id} not found")
                            return None
                        elif response.status == 429:
                            logger.warning(f"Rate limit hit for {self.entity_type} {item_id}, pausing")
                            await asyncio.sleep(15)  # Longer pause for rate limiting
                        else:
                            logger.error(f"Error {response.status} fetching {self.entity_type} {item_id}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {self.entity_type} {item_id} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Error fetching {self.entity_type} {item_id} (attempt {attempt + 1}): {str(e)}")
            
            # Don't sleep after the last attempt
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff
        
        return None
    
    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.
        
        Returns a path based on whether a specific range is being fetched
        or all entities.
        
        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/{self.entity_type}/{self.entity_type}_{self.start_id}_{self.end_id}.csv")
        return str(project_root / f"data_raw/{self.entity_type}/{self.entity_type}_all.csv")
    
    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of item IDs to process.
        
        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id
    
    async def get_all_item_ids(self) -> List[int]:
        """
        Get all item IDs to process when no range is specified.
        
        This implementation uses pagination to fetch all item IDs from the API.
        Explicitly requests a large page size (100) to reduce the number of API calls needed.
        
        Returns:
            List of all item IDs to process
        """
        item_ids = []
        # Add page_size=100 parameter to request more items per page
        url = f"{self.base_url}/{self.endpoint}?page_size=100"
        
        logger.info(f"Fetching all {self.entity_type} IDs from {url}")
        
        async with aiohttp.ClientSession() as session:
            while url:
                try:
                    async with self.bucket:  # Respect rate limiting
                        async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                            if response.status != 200:
                                logger.error(f"Error {response.status} fetching {self.entity_type} list")
                                break
                            
                            data = await response.json()
                            
                            # Extract item IDs from the results
                            for item in data.get("results", []):
                                if "id" in item:
                                    item_ids.append(item["id"])
                            
                            # Get the next page URL if available
                            next_url = data.get("next")
                            logger.info(f"Next URL from API: {next_url}")
                            
                            if next_url:
                                # Extract just the path and query parameters from the next URL
                                # This ensures we use our base URL with the correct authentication
                                parsed_url = urlparse(next_url)
                                url = f"{self.base_url}{parsed_url.path}?{parsed_url.query}"
                                logger.info(f"Found {len(item_ids)} {self.entity_type} so far, fetching next page...")
                                await asyncio.sleep(0.2)  # Small delay to avoid rate limiting
                            else:
                                url = None
                                logger.info(f"No more pages to fetch. Last page contained {len(data.get('results', []))} {self.entity_type}.")
                
                except Exception as e:
                    logger.error(f"Error fetching {self.entity_type} list: {str(e)}")
                    break
        
        logger.info(f"Found {len(item_ids)} {self.entity_type} in total")
        return item_ids