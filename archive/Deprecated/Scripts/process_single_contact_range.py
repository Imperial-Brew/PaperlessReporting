import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pull_contacts_async import ContactsPuller

async def get_contact_ids() -> List[int]:
    """
    Get all contact IDs from the API.

    Returns:
        List of contact IDs
    """
    puller = ContactsPuller()
    contact_ids = await puller.get_all_item_ids()
    logger.info(f"Found {len(contact_ids)} contact IDs")
    return contact_ids

async def process_contact_subset(contact_ids: List[int], start_index: int, count: int, output_dir: str):
    """
    Process a subset of contacts from the list of contact IDs.

    Args:
        contact_ids: List of all contact IDs
        start_index: Starting index in the list
        count: Number of contacts to process
        output_dir: Directory for output files
    """
    if not contact_ids:
        logger.error("No contact IDs provided")
        return False

    # Calculate the end index (inclusive)
    end_index = min(start_index + count - 1, len(contact_ids) - 1)

    # Get the subset of contact IDs
    subset_ids = contact_ids[start_index:end_index + 1]

    if not subset_ids:
        logger.error(f"No contact IDs in range {start_index} to {end_index}")
        return False

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output path
    contacts_csv_path = os.path.join(output_dir, f"contacts_subset_{start_index}_{end_index}.csv")

    logger.info(f"Processing {len(subset_ids)} contacts (indices {start_index} to {end_index})")
    logger.info(f"First few IDs in subset: {subset_ids[:5]}")

    # Create a custom puller for this subset
    class SubsetContactsPuller(ContactsPuller):
        def __init__(self, contact_ids: List[int]):
            super().__init__()
            self.subset_ids = contact_ids

        async def get_all_item_ids(self) -> List[int]:
            return self.subset_ids

        def get_item_range(self):
            return None, None  # Use get_all_item_ids instead

    puller = SubsetContactsPuller(subset_ids)

    # Override the output path
    original_get_output_path = puller.get_output_path
    puller.get_output_path = lambda: contacts_csv_path

    try:
        # Run the puller directly
        await puller.run()
        logger.info(f"Contact subset processing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error processing contact subset: {str(e)}")
        return False
    finally:
        # Restore the original method
        puller.get_output_path = original_get_output_path

async def main():
    """
    Main entry point for the script.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process a subset of contacts")
    parser.add_argument("--output-dir", type=str, default="data_real", help="Output directory")
    parser.add_argument("--start-index", type=int, default=0, help="Starting index in the contact list")
    parser.add_argument("--count", type=int, default=20, help="Number of contacts to process")

    args = parser.parse_args()

    # Get all contact IDs
    contact_ids = await get_contact_ids()

    if not contact_ids:
        logger.error("Failed to get contact IDs")
        return

    # Process the subset
    await process_contact_subset(
        contact_ids=contact_ids,
        start_index=args.start_index,
        count=args.count,
        output_dir=args.output_dir
    )

if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())
