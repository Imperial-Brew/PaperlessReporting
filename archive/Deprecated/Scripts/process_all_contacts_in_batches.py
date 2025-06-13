import asyncio
import argparse
import os
import sys
import csv
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

async def process_contact_batch(contact_ids: List[int], start_index: int, batch_size: int, output_dir: str, batch_number: int):
    """
    Process a batch of contacts from the list of contact IDs.
    
    Args:
        contact_ids: List of all contact IDs
        start_index: Starting index in the list
        batch_size: Number of contacts to process in this batch
        output_dir: Directory for output files
        batch_number: Batch number for naming the output file
    """
    if not contact_ids:
        logger.error("No contact IDs provided")
        return False
        
    # Calculate the end index (inclusive)
    end_index = min(start_index + batch_size - 1, len(contact_ids) - 1)
    
    # Get the subset of contact IDs
    subset_ids = contact_ids[start_index:end_index + 1]
    
    if not subset_ids:
        logger.error(f"No contact IDs in range {start_index} to {end_index}")
        return False
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output path
    contacts_csv_path = os.path.join(output_dir, f"contacts_batch_{batch_number}.csv")
    
    logger.info(f"Processing batch {batch_number}: {len(subset_ids)} contacts (indices {start_index} to {end_index})")
    
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
        logger.info(f"Batch {batch_number} processing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error processing batch {batch_number}: {str(e)}")
        return False
    finally:
        # Restore the original method
        puller.get_output_path = original_get_output_path

async def merge_contact_batches(output_dir: str):
    """
    Merge all contact batch files into a single CSV file.
    
    Args:
        output_dir: Directory containing the batch files
    """
    # Find all batch files
    batch_files = list(Path(output_dir).glob("contacts_batch_*.csv"))
    
    if not batch_files:
        logger.warning("No contact batch files found to merge")
        return
    
    logger.info(f"Found {len(batch_files)} contact batch files to merge")
    
    # Output file
    output_file = os.path.join(output_dir, "contacts.csv")
    
    # Read all contacts from batch files
    all_contacts = []
    fieldnames = None
    
    for batch_file in batch_files:
        try:
            with open(batch_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                all_contacts.extend(list(reader))
        except Exception as e:
            logger.error(f"Error reading batch file {batch_file}: {str(e)}")
    
    # Write all contacts to the output file
    if all_contacts and fieldnames:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_contacts)
        
        logger.info(f"Merged {len(all_contacts)} contacts into {output_file}")
    else:
        logger.warning("No contacts found in batch files")

async def process_all_contacts(output_dir: str, batch_size: int = 20):
    """
    Process all contacts in batches.
    
    Args:
        output_dir: Directory for output files
        batch_size: Number of contacts to process in each batch
    """
    # Get all contact IDs
    contact_ids = await get_contact_ids()
    
    if not contact_ids:
        logger.error("Failed to get contact IDs")
        return
    
    # Calculate the number of batches
    num_batches = (len(contact_ids) + batch_size - 1) // batch_size
    logger.info(f"Processing {len(contact_ids)} contacts in {num_batches} batches of {batch_size}")
    
    # Process each batch
    successful_batches = 0
    for batch_number in range(1, num_batches + 1):
        start_index = (batch_number - 1) * batch_size
        
        success = await process_contact_batch(
            contact_ids=contact_ids,
            start_index=start_index,
            batch_size=batch_size,
            output_dir=output_dir,
            batch_number=batch_number
        )
        
        if success:
            successful_batches += 1
    
    logger.info(f"Processed {successful_batches}/{num_batches} batches successfully")
    
    # Merge all batches
    await merge_contact_batches(output_dir)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process all contacts in batches")
    parser.add_argument("--output-dir", type=str, default="data_real", help="Output directory")
    parser.add_argument("--batch-size", type=int, default=20, help="Number of contacts to process in each batch")
    
    args = parser.parse_args()
    
    # Run the batch processing
    asyncio.run(process_all_contacts(
        output_dir=args.output_dir,
        batch_size=args.batch_size
    ))