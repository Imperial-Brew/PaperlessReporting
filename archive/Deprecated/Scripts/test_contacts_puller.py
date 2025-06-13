import asyncio
import logging
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from scripts.pull_contacts_async import ContactsPuller

async def test_contacts_puller():
    """
    Test the ContactsPuller directly to debug pagination issues.
    """
    puller = ContactsPuller()
    logger.info("Starting contact pull test")
    
    # Get all contact IDs
    contact_ids = await puller.get_all_item_ids()
    logger.info(f"Found {len(contact_ids)} contact IDs")
    
    # Print the first 5 contact IDs
    if contact_ids:
        logger.info(f"First 5 contact IDs: {contact_ids[:5]}")
    
    logger.info("Contact pull test completed")

if __name__ == "__main__":
    asyncio.run(test_contacts_puller())