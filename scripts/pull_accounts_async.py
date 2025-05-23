import asyncio
from typing import Dict, Any
from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

class AccountsPuller(AsyncPuller[Dict[str, Any]]):
    """Async puller for accounts."""
    
    def __init__(self):
        super().__init__(
            endpoint="accounts/public",
            rate=1.8,
            capacity=5
        )
    
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw account data into the desired format."""
        return {
            "id": data.get("id"),
            "business_name": data.get("business_name"),
            "website": data.get("website"),
            "notes": data.get("notes"),
            "billing_address": safe_get(data, "billing_address", "street"),
            "billing_city": safe_get(data, "billing_address", "city"),
            "billing_state": safe_get(data, "billing_address", "state"),
            "billing_zip": safe_get(data, "billing_address", "zip"),
            "billing_country": safe_get(data, "billing_address", "country"),
            "shipping_address": safe_get(data, "shipping_address", "street"),
            "shipping_city": safe_get(data, "shipping_address", "city"),
            "shipping_state": safe_get(data, "shipping_address", "state"),
            "shipping_zip": safe_get(data, "shipping_address", "zip"),
            "shipping_country": safe_get(data, "shipping_address", "country")
        }

async def main():
    """Main entry point for the script."""
    puller = AccountsPuller()
    # No start/end IDs means fetch all accounts
    await puller.run()

if __name__ == "__main__":
    asyncio.run(main()) 