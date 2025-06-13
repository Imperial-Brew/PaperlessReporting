"""
PaperlessPartsClient: A client for interacting with the Paperless Parts API.

This module provides a client class for making requests to the Paperless Parts API
with support for authentication, rate limiting, pagination, and error handling.
All API endpoint URLs are centralized in this client to ensure consistency.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Union, Callable, TypeVar, Generic
from urllib.parse import urlparse, parse_qs

from .config_loader import config
from .async_token_bucket import AsyncTokenBucket

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic methods
T = TypeVar('T')


class PaperlessPartsClient:
    """
    Client for interacting with the Paperless Parts API.

    This class encapsulates all API interactions, providing methods for
    authentication, rate limiting, pagination, and error handling.
    All API endpoint URLs are centralized here to ensure consistency.
    """

    # API Endpoints
    ENDPOINT_ACCOUNTS = "accounts/public"
    ENDPOINT_ACCOUNT_BY_ID = "accounts/public/{account_id}"
    ENDPOINT_CONTACTS = "contacts/public"
    ENDPOINT_CONTACT_BY_ID = "contacts/public/{contact_id}"
    ENDPOINT_QUOTES = "quotes/public"
    ENDPOINT_QUOTE_BY_ID = "quotes/public/{quote_id}"
    ENDPOINT_QUOTE_ITEMS = "quotes/public/{quote_id}/quote-items"
    ENDPOINT_QUOTE_REVISIONS = "quotes/public/new"
    ENDPOINT_ORDERS = "orders/public"
    ENDPOINT_ORDER_BY_ID = "orders/public/{order_id}"
    ENDPOINT_ORDER_ITEMS = "orders/public/{order_id}/order-items"

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        rate: float = 1.8,
        capacity: int = 5,
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        Initialize the Paperless Parts API client.

        Args:
            base_url: Base URL for the API (defaults to config["api_base_url"])
            api_key: API key for authentication (defaults to config["api_key"])
            rate: Rate limit in requests per second
            capacity: Maximum burst capacity for rate limiting
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Default timeout for API requests in seconds
        """
        self.base_url = base_url or config()["api_base_url"]
        self.api_key = api_key or config()["api_key"]
        self.headers = {"Authorization": f"API-Token {self.api_key}"}
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize rate limiter
        self.bucket = AsyncTokenBucket(rate=rate, capacity=capacity)

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to the API.

        Args:
            endpoint: API endpoint to request (without base URL)
            params: Query parameters to include in the request
            timeout: Request timeout in seconds (overrides default)

        Returns:
            Response data as a dictionary or None if the request failed
        """
        url = f"{self.base_url}/{endpoint}"
        request_timeout = timeout or self.timeout
        delay = 1  # Initial delay for exponential backoff

        for attempt in range(self.max_retries):
            try:
                # Wait for rate limiting token
                async with self.bucket:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url,
                            headers=self.headers,
                            params=params,
                            timeout=request_timeout
                        ) as response:
                            if response.status == 200:
                                return await response.json()
                            elif response.status == 404:
                                logger.warning(f"Resource not found: {url}")
                                return None
                            elif response.status == 429:
                                logger.warning(f"Rate limit hit for {url}, pausing")
                                await asyncio.sleep(15)  # Longer pause for rate limiting
                            else:
                                logger.error(f"Error {response.status} fetching {url}")
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Error fetching {url} (attempt {attempt + 1}): {str(e)}")

            # Don't sleep after the last attempt
            if attempt < self.max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 2  # Exponential backoff

        return None

    async def get_by_id(
        self,
        endpoint: str,
        item_id: Union[int, str],
        timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single item by ID.

        Note: This is a legacy method. It's recommended to use the specialized methods
        like get_account, get_quote, etc. instead, which use the centralized endpoint constants.

        Args:
            endpoint: API endpoint (without base URL)
            item_id: ID of the item to fetch
            timeout: Request timeout in seconds (overrides default)

        Returns:
            Item data as a dictionary or None if not found or request failed
        """
        return await self.get(f"{endpoint}/{item_id}", timeout=timeout)

    async def get_paginated(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
        max_pages: Optional[int] = None,
        extract_items: Optional[Callable[[Dict[str, Any]], List[T]]] = None,
        timeout: Optional[int] = None
    ) -> List[T]:
        """
        Get all items from a paginated endpoint.

        Args:
            endpoint: API endpoint (without base URL)
            params: Additional query parameters
            page_size: Number of items per page
            max_pages: Maximum number of pages to fetch (None for all)
            extract_items: Function to extract items from the response
                           (defaults to extracting the "results" field)
            timeout: Request timeout in seconds (overrides default)

        Returns:
            List of items from all pages
        """
        all_items = []
        page_count = 0

        # Initialize query parameters
        query_params = params.copy() if params else {}
        query_params["page_size"] = page_size

        # Default extractor function
        if extract_items is None:
            extract_items = lambda response: response.get("results", [])

        # Start with the first page
        url = f"{endpoint}"

        logger.info(f"Fetching paginated data from {url}")

        while url and (max_pages is None or page_count < max_pages):
            page_count += 1
            logger.info(f"Fetching page {page_count}...")

            response = await self.get(url, params=query_params, timeout=timeout)

            if not response:
                logger.error(f"Failed to fetch page {page_count} from {url}")
                break

            # Extract items from the response
            items = extract_items(response)
            all_items.extend(items)
            logger.info(f"Retrieved {len(items)} items from page {page_count}")

            # Clear query params for subsequent requests (they're included in the next URL)
            query_params = {}

            # Get the next page URL if available
            next_url = response.get("next")

            if next_url:
                # Extract just the path and query parameters from the next URL
                parsed_url = urlparse(next_url)
                url = parsed_url.path.lstrip('/')  # Remove leading slash

                # Extract query parameters from the next URL
                query_params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}

                logger.info(f"Next page available, continuing to page {page_count + 1}")
                # Add a small delay to avoid rate limiting
                await asyncio.sleep(0.2)
            else:
                url = None
                logger.info(f"No more pages available")

        logger.info(f"Retrieved a total of {len(all_items)} items from {page_count} pages")
        return all_items

    # Specialized methods for common endpoints

    async def get_accounts(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Get all accounts.

        Args:
            page_size: Number of accounts per page

        Returns:
            List of account data
        """
        return await self.get_paginated(self.ENDPOINT_ACCOUNTS, page_size=page_size)

    async def get_account(self, account_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get a single account by ID.

        Args:
            account_id: ID of the account to fetch

        Returns:
            Account data or None if not found
        """
        endpoint = self.ENDPOINT_ACCOUNT_BY_ID.format(account_id=account_id)
        return await self.get(endpoint)

    async def get_contacts(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Get all contacts.

        Args:
            page_size: Number of contacts per page

        Returns:
            List of contact data
        """
        return await self.get_paginated(self.ENDPOINT_CONTACTS, page_size=page_size)

    async def get_contact(self, contact_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get a single contact by ID.

        Args:
            contact_id: ID of the contact to fetch

        Returns:
            Contact data or None if not found
        """
        endpoint = self.ENDPOINT_CONTACT_BY_ID.format(contact_id=contact_id)
        return await self.get(endpoint)

    async def get_quotes(
        self,
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get quotes, optionally filtered by ID range.

        Args:
            start_id: Optional starting ID for range of quotes to fetch
            end_id: Optional ending ID for range of quotes to fetch
            page_size: Number of quotes per page

        Returns:
            List of quote data
        """
        params = {}
        if start_id is not None and end_id is not None:
            # If a range is specified, fetch quotes within that range
            # This is a simplified approach; the actual implementation
            # would depend on the API's filtering capabilities
            params["min_id"] = start_id
            params["max_id"] = end_id

        return await self.get_paginated(self.ENDPOINT_QUOTES, params=params, page_size=page_size)

    async def get_quote(self, quote_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get a single quote by ID.

        Args:
            quote_id: ID of the quote to fetch

        Returns:
            Quote data or None if not found
        """
        endpoint = self.ENDPOINT_QUOTE_BY_ID.format(quote_id=quote_id)
        return await self.get(endpoint)

    async def get_quote_with_revision(self, quote_id: Union[int, str], revision: int) -> Optional[Dict[str, Any]]:
        """
        Get a single quote with a specific revision.

        Args:
            quote_id: ID of the quote to fetch
            revision: Revision number to fetch

        Returns:
            Quote data or None if not found
        """
        endpoint = self.ENDPOINT_QUOTE_BY_ID.format(quote_id=quote_id)
        return await self.get(endpoint, params={"revision": revision})

    async def get_quote_revisions(self) -> List[Dict[str, Any]]:
        """
        Get all quote revisions.

        Returns:
            List of quote revision data
        """
        return await self.get(self.ENDPOINT_QUOTE_REVISIONS)

    async def get_quote_items(self, quote_id: Union[int, str]) -> List[Dict[str, Any]]:
        """
        Get all items for a specific quote.

        Args:
            quote_id: ID of the quote

        Returns:
            List of quote item data
        """
        endpoint = self.ENDPOINT_QUOTE_ITEMS.format(quote_id=quote_id)
        return await self.get_paginated(endpoint)

    async def get_orders(self, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Get all orders.

        Args:
            page_size: Number of orders per page

        Returns:
            List of order data
        """
        return await self.get_paginated(self.ENDPOINT_ORDERS, page_size=page_size)

    async def get_order(self, order_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get a single order by ID.

        Args:
            order_id: ID of the order to fetch

        Returns:
            Order data or None if not found
        """
        endpoint = self.ENDPOINT_ORDER_BY_ID.format(order_id=order_id)
        return await self.get(endpoint)

    async def get_order_items(self, order_id: Union[int, str]) -> List[Dict[str, Any]]:
        """
        Get all items for a specific order.

        Args:
            order_id: ID of the order

        Returns:
            List of order item data
        """
        endpoint = self.ENDPOINT_ORDER_ITEMS.format(order_id=order_id)
        return await self.get_paginated(endpoint)
