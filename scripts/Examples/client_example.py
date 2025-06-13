"""
Example script demonstrating the use of the PaperlessPartsClient.

This script shows how to use the PaperlessPartsClient to fetch data from the
Paperless Parts API, including accounts, contacts, quotes, and orders.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import the client
from scripts.utils.paperless_client import PaperlessPartsClient


async def fetch_accounts(client: PaperlessPartsClient, limit: int = 5) -> None:
    """
    Fetch accounts from the API and print information about them.
    
    Args:
        client: PaperlessPartsClient instance
        limit: Maximum number of accounts to print
    """
    logger.info("Fetching accounts...")
    
    # Fetch all accounts
    accounts = await client.get_accounts()
    
    logger.info(f"Retrieved {len(accounts)} accounts")
    
    # Print information about the first few accounts
    for i, account in enumerate(accounts[:limit]):
        logger.info(f"Account {i+1}:")
        logger.info(f"  ID: {account.get('id')}")
        logger.info(f"  Name: {account.get('name')}")
        logger.info(f"  Type: {account.get('type')}")
    
    # Fetch a single account by ID
    if accounts:
        account_id = accounts[0]["id"]
        logger.info(f"Fetching account with ID {account_id}...")
        account = await client.get_account(account_id)
        
        if account:
            logger.info(f"Retrieved account: {account.get('name')}")
        else:
            logger.error(f"Failed to retrieve account with ID {account_id}")


async def fetch_contacts(client: PaperlessPartsClient, limit: int = 5) -> None:
    """
    Fetch contacts from the API and print information about them.
    
    Args:
        client: PaperlessPartsClient instance
        limit: Maximum number of contacts to print
    """
    logger.info("Fetching contacts...")
    
    # Fetch all contacts
    contacts = await client.get_contacts()
    
    logger.info(f"Retrieved {len(contacts)} contacts")
    
    # Print information about the first few contacts
    for i, contact in enumerate(contacts[:limit]):
        logger.info(f"Contact {i+1}:")
        logger.info(f"  ID: {contact.get('id')}")
        logger.info(f"  Name: {contact.get('first_name')} {contact.get('last_name')}")
        logger.info(f"  Email: {contact.get('email')}")
        logger.info(f"  Account ID: {contact.get('account_id')}")
    
    # Fetch a single contact by ID
    if contacts:
        contact_id = contacts[0]["id"]
        logger.info(f"Fetching contact with ID {contact_id}...")
        contact = await client.get_contact(contact_id)
        
        if contact:
            logger.info(f"Retrieved contact: {contact.get('first_name')} {contact.get('last_name')}")
        else:
            logger.error(f"Failed to retrieve contact with ID {contact_id}")


async def fetch_quotes(client: PaperlessPartsClient, limit: int = 5) -> None:
    """
    Fetch quotes from the API and print information about them.
    
    Args:
        client: PaperlessPartsClient instance
        limit: Maximum number of quotes to print
    """
    logger.info("Fetching quotes...")
    
    # Fetch quotes with a specific ID range
    quotes = await client.get_quotes(start_id=7500, end_id=7550)
    
    logger.info(f"Retrieved {len(quotes)} quotes")
    
    # Print information about the first few quotes
    for i, quote in enumerate(quotes[:limit]):
        logger.info(f"Quote {i+1}:")
        logger.info(f"  ID: {quote.get('id')}")
        logger.info(f"  Number: {quote.get('number')}")
        logger.info(f"  Status: {quote.get('status')}")
    
    # Fetch a single quote by ID
    if quotes:
        quote_id = quotes[0]["id"]
        logger.info(f"Fetching quote with ID {quote_id}...")
        quote = await client.get_quote(quote_id)
        
        if quote:
            logger.info(f"Retrieved quote: {quote.get('number')}")
            
            # Fetch quote items
            logger.info(f"Fetching items for quote {quote_id}...")
            items = await client.get_quote_items(quote_id)
            logger.info(f"Retrieved {len(items)} items for quote {quote_id}")
        else:
            logger.error(f"Failed to retrieve quote with ID {quote_id}")


async def main():
    """
    Main entry point for the script.
    
    Creates a PaperlessPartsClient instance and demonstrates its use.
    """
    # Create a client with default settings
    client = PaperlessPartsClient()
    
    # Fetch and display accounts
    await fetch_accounts(client)
    
    # Fetch and display contacts
    await fetch_contacts(client)
    
    # Fetch and display quotes
    await fetch_quotes(client)
    
    logger.info("Example completed successfully")


if __name__ == "__main__":
    asyncio.run(main())