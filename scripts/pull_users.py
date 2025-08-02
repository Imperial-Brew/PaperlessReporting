"""
Script to pull users (salespeople/estimators) from Paperless API.

This script fetches user data from the API and displays the first 5 responses in full detail.
"""

import asyncio
import json
import csv
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from scripts.utils.async_puller import AsyncPuller
from scripts.utils.config_loader import config_loader
from scripts.utils.logging_config import get_logger

logger = get_logger(__name__)

class UsersPuller(AsyncPuller[Dict[str, Any]]):
    """
    Asynchronous puller for user data.

    This class extends AsyncPuller to fetch user data from the API.
    """

    def __init__(self, output_dir: str = "data_raw"):
        """
        Initialize the UsersPuller.

        Args:
            output_dir: Directory to save output files
        """
        super().__init__(
            endpoint="users/public",
            rate=1.0,  # Requests per second
            capacity=5  # Maximum burst capacity
        )
        self.output_dir = output_dir

    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw user data into the desired format.

        Args:
            data: Raw user data from the API

        Returns:
            Transformed user data
        """
        # Return the data as is, or transform it as needed
        return data

    def get_output_path(self) -> str:
        """
        Get the path to save the output CSV file.

        Returns:
            Path to the output CSV file
        """
        output_dir = Path(self.output_dir) / "users" / "public"
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir / "users_all.csv")

    def get_item_range(self) -> List[int]:
        """
        Get the range of item IDs to fetch.

        For users, we don't use IDs, so we return an empty list.
        The run method will be overridden to fetch all users.

        Returns:
            Empty list
        """
        return []

    async def run(self):
        """
        Run the puller to fetch all users.

        This overrides the base class method to fetch all users at once
        instead of by ID.

        Returns:
            List of user data
        """
        url = f"{self.base_url}/{self.endpoint}"
        logger.info(f"Fetching users from {url}")

        async with self.session_factory() as session:
            async with session.get(url, headers=self.headers) as response:
                response.raise_for_status()
                data = await response.json()

                # Check if the response is a list or has a 'results' field
                if isinstance(data, list):
                    users = data
                else:
                    users = data.get("results", [])

                # Transform each user
                transformed_users = [self.transform_data(user) for user in users]

                # Save to CSV
                self.save_to_csv(transformed_users, self.get_output_path())

                # Display summary
                logger.info(f"✅ Found {len(transformed_users)} users")

                return transformed_users

async def main():
    """
    Main entry point for the script.

    Creates a UsersPuller instance and runs it to fetch user data from the API.
    """
    try:
        users_puller = UsersPuller()
        users = await users_puller.run()

        # Display the first 5 users in full detail
        print("\n=== First 5 Users (Full Data) ===")
        for i, user in enumerate(users[:5], 1):
            print(f"\n--- User {i}/{min(5, len(users))} ---")
            print(json.dumps(user, indent=2))

        # Display a summary of all users
        print("\n=== All Users (Summary) ===")
        for i, user in enumerate(users, 1):
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            email = user.get('email', 'No email')
            role = user.get('role', 'Unknown role')
            print(f"{i}. {name} ({email}) - {role}")

    except Exception as e:
        logger.error(f"❌ Failed to fetch users: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
