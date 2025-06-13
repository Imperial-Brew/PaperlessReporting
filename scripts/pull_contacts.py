import asyncio
import aiohttp
import json
import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables from .env file
load_dotenv(project_root / ".env")

async def pull_contacts(fetch_all=False, output_format="json"):
    """
    Simple script to pull contacts from the Paperless Parts API.

    Uses the /contacts/public endpoint with API token authentication.

    Args:
        fetch_all: If True, fetch all pages of contacts. If False, fetch only the first page.
        output_format: Format to save the data in. Options: "json" or "csv".
    """
    # Get API credentials from environment variables
    api_base_url = os.getenv("API_BASE_URL")
    api_token = os.getenv("PAPERLESS_API_TOKEN")

    if not api_base_url or not api_token:
        logger.error("API_BASE_URL and PAPERLESS_API_TOKEN must be set in the .env file")
        return

    # Construct the URL and headers
    url = f"{api_base_url}/contacts/public"
    headers = {"Authorization": f"API-Token {api_token}"}

    logger.info(f"Pulling contacts from {url}")

    all_contacts = []
    page_count = 0

    # Make the API request with pagination
    async with aiohttp.ClientSession() as session:
        while url:
            page_count += 1
            logger.info(f"Fetching page {page_count}...")

            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"Error {response.status} fetching contacts: {await response.text()}")
                    return

                # Parse the JSON response
                data = await response.json()

                # Extract the results
                contacts = data.get("results", [])
                all_contacts.extend(contacts)
                logger.info(f"Retrieved {len(contacts)} contacts from page {page_count}")

                # Check if there are more pages
                next_url = data.get("next")

                # If fetch_all is True and there's a next page, update the URL
                if fetch_all and next_url:
                    # Extract the path and query from the next URL
                    from urllib.parse import urlparse
                    parsed_url = urlparse(next_url)
                    url = f"{api_base_url}{parsed_url.path}?{parsed_url.query}"
                    logger.info(f"More contacts available, fetching next page...")
                    # Add a small delay to avoid rate limiting
                    await asyncio.sleep(0.2)
                else:
                    if next_url and not fetch_all:
                        logger.info(f"More contacts available at: {next_url}")
                        logger.info("Run with --fetch-all to retrieve all contacts")
                    url = None

    # Print summary
    logger.info(f"Retrieved a total of {len(all_contacts)} contacts from {page_count} pages")

    # Print the first contact as an example
    if all_contacts:
        logger.info(f"First contact example: {json.dumps(all_contacts[0], indent=2)}")

    # Save the results to a file
    output_dir = project_root / "data_raw" / "contacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    if output_format.lower() == "json":
        # Save as JSON
        output_file = output_dir / "contacts_all.json"
        with open(output_file, 'w') as f:
            json.dump(all_contacts, f, indent=2)
        logger.info(f"Saved all contacts data to {output_file} in JSON format")

    elif output_format.lower() == "csv":
        # Save as CSV
        import csv
        output_file = output_dir / "contacts_all.csv"

        # Determine fieldnames from the first contact
        if all_contacts:
            fieldnames = all_contacts[0].keys()

            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_contacts)

            logger.info(f"Saved all contacts data to {output_file} in CSV format")
        else:
            logger.warning("No contacts to save to CSV")

    else:
        logger.error(f"Unsupported output format: {output_format}. Supported formats: json, csv")

    return all_contacts

if __name__ == "__main__":
    import argparse

    # Create a detailed description with examples
    description = """
    Pull contacts from the Paperless Parts API.

    This script fetches contact data from the Paperless Parts API using the /contacts/public endpoint.
    By default, it fetches only the first page of contacts (usually 20 contacts) and saves them in JSON format.

    Examples:
      python pull_contacts.py                     # Fetch first page in JSON format
      python pull_contacts.py --fetch-all         # Fetch all pages in JSON format
      python pull_contacts.py --format csv        # Fetch first page in CSV format
      python pull_contacts.py --fetch-all --format csv  # Fetch all pages in CSV format

    The output files are saved in the data_raw/contacts directory:
      - JSON output: contacts_all.json
      - CSV output: contacts_all.csv

    Note: This script requires API credentials to be set in the .env file:
      - API_BASE_URL: The base URL of the Paperless Parts API
      - PAPERLESS_API_TOKEN: Your API token for authentication
    """

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--fetch-all", action="store_true", 
                        help="Fetch all pages of contacts (default: fetch only first page)")
    parser.add_argument("--format", choices=["json", "csv"], default="json", 
                        help="Output format (default: json)")
    args = parser.parse_args()

    # Run the script
    asyncio.run(pull_contacts(fetch_all=args.fetch_all, output_format=args.format))
