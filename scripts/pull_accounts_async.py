"""
Asynchronous puller for account data from the API.

This script fetches account data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching all accounts or a specific range.
"""

import asyncio
import logging
import argparse
import aiohttp
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

from utils.async_puller import AsyncPuller
from utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class AccountsPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for account data.

    This class extends AsyncPuller to fetch account data from the API
    and transform it into a structured format with selected fields.
    It supports fetching all accounts or a specific range of account IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the AccountsPuller.

        Args:
            start_id: Optional starting ID for range of accounts to fetch
            end_id: Optional ending ID for range of accounts to fetch
        """
        super().__init__(
            endpoint="accounts/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=50  # Process 50 accounts at a time
        )
        self.start_id = start_id
        self.end_id = end_id

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw account data into the desired format.

        Extracts and structures selected fields from the raw API response,
        including nested address information.

        Args:
            data: Raw account data from the API

        Returns:
            Transformed account data with selected fields
        """
        return {
            "name": data.get("name"),
            "id": data.get("id"),
            "phone": data.get("phone"),
            "erp_code": data.get("erp_code"),
            "type": data.get("type"),
            "url": data.get("url")
        }

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on whether a specific range is being fetched
        or all accounts.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/accounts/public/accounts_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/accounts/public/accounts_all.csv")

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of account IDs to process.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all account IDs to process when no range is specified.

        This implementation uses pagination to fetch all account IDs from the API.
        Explicitly requests a large page size (100) to reduce the number of API calls needed.

        Returns:
            List of all account IDs to process
        """
        account_ids = []
        # Add page_size=100 parameter to request more accounts per page
        url = f"{self.base_url}/{self.endpoint}?page_size=100"

        logger.info(f"Fetching all account IDs from {url}")

        async with aiohttp.ClientSession() as session:
            while url:
                try:
                    async with self.bucket:  # Respect rate limiting
                        async with session.get(url, headers=self.headers, timeout=30) as response:
                            if response.status != 200:
                                logger.error(f"Error {response.status} fetching accounts list")
                                break

                            data = await response.json()

                            # Extract account IDs from the results
                            for account in data.get("results", []):
                                if "id" in account:
                                    account_ids.append(account["id"])

                            # Get the next page URL if available
                            next_url = data.get("next")

                            if next_url:
                                # Extract just the path and query parameters from the next URL
                                # This ensures we use our base URL with the correct authentication
                                parsed_url = urlparse(next_url)
                                url = f"{self.base_url}{parsed_url.path}?{parsed_url.query}"
                                logger.info(f"Found {len(account_ids)} accounts so far, fetching next page...")
                                await asyncio.sleep(0.2)  # Small delay to avoid rate limiting
                            else:
                                url = None
                                logger.info(f"No more pages to fetch. Last page contained {len(data.get('results', []))} accounts.")

                except Exception as e:
                    logger.error(f"Error fetching accounts list: {str(e)}")
                    break

        logger.info(f"Found {len(account_ids)} accounts in total")
        return account_ids

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates an AccountsPuller instance,
    and runs it to fetch account data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch account data from the API")
    parser.add_argument("--start-id", type=int, help="Starting account ID")
    parser.add_argument("--end-id", type=int, help="Ending account ID")
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if (start_id is None and end_id is not None) or (start_id is not None and end_id is None):
        logger.error("Both --start-id and --end-id must be specified together")
        return

    puller = AccountsPuller(start_id, end_id)
    logger.info(f"Starting account pull job: {start_id or 'all'} to {end_id or 'end'}")

    try:
        await puller.run()
        logger.info("Account pull job completed successfully")
    except Exception as e:
        logger.error(f"Account pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
