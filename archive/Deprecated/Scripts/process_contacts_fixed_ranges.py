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

async def process_contact_range(start_id: int, end_id: int, output_dir: str, range_number: int):
    """
    Process a range of contacts from the Paperless Parts API.

    Args:
        start_id: Starting contact ID
        end_id: Ending contact ID
        output_dir: Directory for output files
        range_number: Range number for naming the output file
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output path (override the default path in the puller)
    contacts_csv_path = os.path.join(output_dir, f"contacts_range_{range_number}.csv")

    # Create a puller to get just this range of contacts
    logger.info(f"Processing contacts range {range_number} (IDs {start_id} to {end_id})")
    
    puller = ContactsPuller(start_id=start_id, end_id=end_id)
    
    # Override the output path
    original_get_output_path = puller.get_output_path
    puller.get_output_path = lambda: contacts_csv_path
    
    try:
        # Run the puller directly
        await puller.run()
        logger.info(f"Contact range {range_number} processing completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error processing contact range {range_number}: {str(e)}")
        return False
    finally:
        # Restore the original method
        puller.get_output_path = original_get_output_path

async def merge_contact_ranges(output_dir: str):
    """
    Merge all contact range files into a single CSV file.

    Args:
        output_dir: Directory containing the range files
    """
    # Find all range files
    range_files = list(Path(output_dir).glob("contacts_range_*.csv"))
    
    if not range_files:
        logger.warning("No contact range files found to merge")
        return
    
    logger.info(f"Found {len(range_files)} contact range files to merge")
    
    # Output file
    output_file = os.path.join(output_dir, "contacts.csv")
    
    # Read all contacts from range files
    all_contacts = []
    fieldnames = None
    
    for range_file in range_files:
        try:
            with open(range_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if fieldnames is None:
                    fieldnames = reader.fieldnames
                all_contacts.extend(list(reader))
        except Exception as e:
            logger.error(f"Error reading range file {range_file}: {str(e)}")
    
    # Write all contacts to the output file
    if all_contacts and fieldnames:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_contacts)
        
        logger.info(f"Merged {len(all_contacts)} contacts into {output_file}")
    else:
        logger.warning("No contacts found in range files")

async def process_contacts_in_fixed_ranges(output_dir: str, range_size: int = 1000, max_id: int = 10000):
    """
    Process contacts in fixed ID ranges without fetching all IDs first.
    
    Args:
        output_dir: Directory for output files
        range_size: Size of each ID range
        max_id: Maximum ID to consider
    """
    # Process contacts in fixed ranges
    range_number = 1
    successful_ranges = 0
    
    for start_id in range(1, max_id + 1, range_size):
        end_id = start_id + range_size - 1
        
        success = await process_contact_range(start_id, end_id, output_dir, range_number)
        if success:
            successful_ranges += 1
        
        range_number += 1
    
    logger.info(f"Processed {successful_ranges} ranges successfully")
    
    # Merge all ranges
    await merge_contact_ranges(output_dir)

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process contacts in fixed ID ranges to avoid timeouts")
    parser.add_argument("--output-dir", type=str, default="data_real", help="Output directory")
    parser.add_argument("--range-size", type=int, default=1000, help="Size of each ID range")
    parser.add_argument("--max-id", type=int, default=10000, help="Maximum ID to consider")
    
    args = parser.parse_args()
    
    # Run the fixed range processing
    asyncio.run(process_contacts_in_fixed_ranges(
        output_dir=args.output_dir,
        range_size=args.range_size,
        max_id=args.max_id
    ))