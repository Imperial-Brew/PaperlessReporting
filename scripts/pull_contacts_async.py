"""
Asynchronous puller for contact data from the API.

This script fetches contact data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching all contacts or a specific range.
"""

import asyncio
import logging
import argparse
import aiohttp
from typing import Dict, Any, Optional, List, Tuple

from utils.async_puller import AsyncPuller

# Configure logging
logger = logging.getLogger(__name__)

class ContactsPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for contact data.

    This class extends AsyncPuller to fetch contact data from the API
    and transform it into a structured format with selected fields.
    It supports fetching all contacts or a specific range of contact IDs.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None):
        """
        Initialize the ContactsPuller.

        Args:
            start_id: Optional starting ID for range of contacts to fetch
            end_id: Optional ending ID for range of contacts to fetch
        """
        super().__init__(
            endpoint="contacts/public",
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=50  # Process 50 contacts at a time
        )
        self.start_id = start_id
        self.end_id = end_id

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw contact data into the desired format.

        Extracts and structures selected fields from the raw API response.

        Args:
            data: Raw contact data from the API

        Returns:
            Transformed contact data with selected fields
        """
        return {
            "id": data.get("id"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "phone_ext": data.get("phone_ext"),
            "notes": data.get("notes"),
            "account_id": data.get("account_id")
        }

    def get_output_path(self) -> str:
        """
        Generate the output path for the CSV file.

        Returns a path based on whether a specific range is being fetched
        or all contacts.

        Returns:
            Path to the output CSV file
        """
        # Use absolute path to project root directory
        project_root = Path(__file__).parent.parent
        if self.start_id is not None and self.end_id is not None:
            return str(project_root / f"data_raw/contacts/contacts_{self.start_id}_{self.end_id}.csv")
        return str(project_root / "data_raw/contacts/contacts_all.csv")

    def get_item_range(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Get the range of contact IDs to process.

        Returns:
            Tuple of (start_id, end_id), where None means no limit
        """
        return self.start_id, self.end_id

    async def get_all_item_ids(self) -> List[int]:
        """
        Get all contact IDs to process when no range is specified.

        This implementation uses pagination to fetch all contact IDs from the API.

        Returns:
            List of all contact IDs to process
        """
        contact_ids = []
        url = f"{self.base_url}/{self.endpoint}"

        logger.info(f"Fetching all contact IDs from {url}")

        async with aiohttp.ClientSession() as session:
            while url:
                try:
                    async with self.bucket:  # Respect rate limiting
                        async with session.get(url, headers=self.headers, timeout=30) as response:
                            if response.status != 200:
                                logger.error(f"Error {response.status} fetching contacts list")
                                break

                            data = await response.json()

                            # Extract contact IDs from the results
                            for contact in data.get("results", []):
                                if "id" in contact:
                                    contact_ids.append(contact["id"])

                            # Get the next page URL if available
                            url = data.get("next")

                            if url:
                                logger.info(f"Found {len(contact_ids)} contacts so far, fetching next page...")
                                await asyncio.sleep(0.2)  # Small delay to avoid rate limiting

                except Exception as e:
                    logger.error(f"Error fetching contacts list: {str(e)}")
                    break

        logger.info(f"Found {len(contact_ids)} contacts in total")
        return contact_ids

async def main():
    """
    Main entry point for the script.

    Parses command line arguments, creates a ContactsPuller instance,
    and runs it to fetch contact data from the API.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Fetch contact data from the API")
    parser.add_argument("--start-id", type=int, help="Starting contact ID")
    parser.add_argument("--end-id", type=int, help="Ending contact ID")
    args = parser.parse_args()

    start_id = args.start_id
    end_id = args.end_id

    # Validate arguments
    if (start_id is None and end_id is not None) or (start_id is not None and end_id is None):
        logger.error("Both --start-id and --end-id must be specified together")
        return

    puller = ContactsPuller(start_id, end_id)
    logger.info(f"Starting contact pull job: {start_id or 'all'} to {end_id or 'end'}")

    try:
        await puller.run()
        logger.info("Contact pull job completed successfully")
    except Exception as e:
        logger.error(f"Contact pull job failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Configure logging at the script level
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    asyncio.run(main())
