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
from scripts.utils.paperless_client import PaperlessPartsClient

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
        timeout: int = 30,
        client: Optional[PaperlessPartsClient] = None
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
            client: Optional PaperlessPartsClient instance to use for API calls
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

        # Initialize client if not provided
        self.client = client or PaperlessPartsClient(
            rate=rate,
            capacity=capacity,
            max_retries=max_retries,
            timeout=timeout
        )

    async def fetch_item(self, session: aiohttp.ClientSession, item_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single item with retry logic and configurable timeout.

        Args:
            session: aiohttp client session (not used with client, kept for backward compatibility)
            item_id: ID of the item to fetch

        Returns:
            Dict containing item data or None if failed after retries
        """
        # Use the client to fetch the item
        result = await self.client.get_by_id(self.endpoint, item_id, timeout=self.timeout)

        if result is None:
            logger.warning(f"{self.entity_type.capitalize()} {item_id} not found")

        return result

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

        This implementation uses the client's get_paginated method to fetch all items
        and extract their IDs.

        Returns:
            List of all item IDs to process
        """
        logger.info(f"Fetching all {self.entity_type} IDs")

        # Define a function to extract IDs from items
        def extract_ids(items: List[Dict[str, Any]]) -> List[int]:
            return [item["id"] for item in items if "id" in item]

        # Use the client to fetch all items and extract their IDs
        items = await self.client.get_paginated(
            self.endpoint,
            page_size=100,
            timeout=self.timeout
        )

        item_ids = extract_ids(items)
        logger.info(f"Found {len(item_ids)} {self.entity_type} in total")
        return item_ids
