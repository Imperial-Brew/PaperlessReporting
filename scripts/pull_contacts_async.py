import asyncio
from typing import Dict, Any
from scripts.utils.async_puller import AsyncPuller

class ContactsPuller(AsyncPuller[Dict[str, Any]]):
    """Async puller for contacts."""
    
    def __init__(self):
        super().__init__(
            endpoint="contacts/public",
            rate=1.8,
            capacity=5
        )
    
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw contact data into the desired format."""
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
    """Main entry point for the script."""
    puller = ContactsPuller()
    # No start/end IDs means fetch all contacts
    await puller.run()

if __name__ == "__main__":
    asyncio.run(main()) 