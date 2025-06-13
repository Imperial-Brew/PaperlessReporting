"""
Asynchronous puller for contact data from the API.

This script fetches contact data from the API and transforms it into a structured format,
saving the results to a CSV file. It supports fetching all contacts or a specific range.
"""

import asyncio
import logging
import argparse
from typing import Dict, Any, Optional

from scripts.utils.entity_puller import EntityPuller

# Configure logging
logger = logging.getLogger(__name__)

class ContactsPuller(EntityPuller[Dict[str, Any]]):
    """
    Asynchronous puller for contact data.

    This class extends EntityPuller to fetch contact data from the API
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
            entity_type="contacts",
            endpoint="contacts/public",
            start_id=start_id,
            end_id=end_id,
            rate=1.8,  # Requests per second
            capacity=5,  # Maximum burst capacity
            batch_size=20,  # Process 20 contacts at a time (reduced from 50 to avoid timeouts)
            timeout=30  # Use a longer timeout (30 seconds instead of default)
        )

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
