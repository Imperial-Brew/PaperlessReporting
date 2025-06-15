import asyncio
import argparse
import os
import sys
import csv
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pull_contacts_async import ContactsPuller

async def process_contact_chunk(start_id: int, end_id: int, output_dir: str, chunk_number: int):
    """
    Process a chunk of contacts from the Paperless Parts API.

    Args:
        start_id: Starting contact ID
        end_id: Ending contact ID
        output_dir: Directory for output files
        chunk_number: Chunk number for naming the output file
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output path
    contacts_csv_path = os.path.join(output_dir, f"contacts_chunk_{chunk_number}.csv")

    # Create a custom pipeline for this chunk
    logger.info(f"Processing contacts chunk {chunk_number} (IDs {start_id} to {end_id})")
    
    # Create a puller to get just this chunk of contacts
    puller = ContactsPuller(start_id=start_id, end_id=end_id)
    
    try:
        # Run the puller directly
        await puller.run()
        logger.info(f"Contact chunk {chunk_number} processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error processing contact chunk {chunk_number}: {str(e)}")
        raise

async def merge_contact_chunks(output_dir: str):
    """
    Merge all contact chunks into a single CSV file.

    Args:
        output_dir: Directory containing the chunk files
    """
    # Find all chunk files
    chunk_files = list(Path(output_dir).glob("contacts_chunk_*.csv"))
    
    if not chunk_files:
        logger.warning("No contact chunk files found to merge")
        return
    
    logger.info(f"Found {len(chunk_files)} contact chunk files to merge")
    
    # Output file
    output_file = os.path.join(output_dir, "contacts.csv")
    
    # Read all contacts from chunk files
    all_contacts = []
    fieldnames = None
    
    for chunk_file in chunk_files:
        try:
            with open(chunk_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                all_contacts.extend(list(reader))
        except Exception as e:
            logger.error(f"Error reading chunk file {chunk_file}: {str(e)}")
    
    # Write all contacts to the output file
    if all_contacts and fieldnames:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_contacts)
        
        logger.info(f"Merged {len(all_contacts)} contacts into {output_file}")
    else:
        logger.warning("No contacts found in chunk files")

async def get_contact_id_range():
    """
    Get the range of contact IDs to process.
    
    Returns:
        Tuple of (min_id, max_id)
    """
    puller = ContactsPuller()
    contact_ids = await puller.get_all_item_ids()
    
    if not contact_ids:
        logger.warning("No contact IDs found")
        return None, None
    
    min_id = min(contact_ids)
    max_id = max(contact_ids)
    
    logger.info(f"Found {len(contact_ids)} contacts with IDs ranging from {min_id} to {max_id}")
    
    return min_id, max_id

async def process_contacts_in_chunks(output_dir: str, chunk_size: int = 100):
    """
    Process all contacts in chunks.
    
    Args:
        output_dir: Directory for output files
        chunk_size: Number of contacts to process in each chunk
    """
    # Get the range of contact IDs
    min_id, max_id = await get_contact_id_range()
    
    if min_id is None or max_id is None:
        logger.error("Could not determine contact ID range")
        return
    
    # Process contacts in chunks
    chunk_number = 1
    for start_id in range(min_id, max_id + 1, chunk_size):
        end_id = min(start_id + chunk_size - 1, max_id)
        
        try:
            await process_contact_chunk(start_id, end_id, output_dir, chunk_number)
            chunk_number += 1
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk_number}: {str(e)}")
            # Continue with the next chunk even if this one fails
    
    # Merge all chunks
    await merge_contact_chunks(output_dir)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process contacts in chunks to avoid timeouts")
    parser.add_argument("--output-dir", type=str, default="data_real", help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=100, help="Number of contacts per chunk")
    
    args = parser.parse_args()
    
    # Run the chunked processing
    asyncio.run(process_contacts_in_chunks(
        output_dir=args.output_dir,
        chunk_size=args.chunk_size
    ))