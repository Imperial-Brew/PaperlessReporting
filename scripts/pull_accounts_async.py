"""
Asynchronous puller for account data from the API.

This script fetches account data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching all accounts or a specific range.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional

from scripts.utils.entity_puller import EntityPuller
from scripts.utils.utils import safe_get

# Configure logging
logger = logging.getLogger(__name__)

class AccountsPuller(EntityPuller[Dict[str, Any]]):
    """
    Asynchronous puller for account data.

    This class extends EntityPuller to fetch account data from the API
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
            entity_type="accounts",
            endpoint="accounts/public",
            start_id=start_id,
            end_id=end_id,
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=50  # Process 50 accounts at a time
        )

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
        # Override the default output path to maintain backward compatibility
        # with the existing file structure (accounts/public)
        return super().get_output_path().replace("accounts", "accounts/public")

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
