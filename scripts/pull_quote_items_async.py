import asyncio
from typing import Dict, Any
from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

class QuoteItemsPuller(AsyncPuller[Dict[str, Any]]):
    """Async puller for quote items."""
    
    def __init__(self):
        super().__init__(
            endpoint="quote-items/public",
            rate=1.8,
            capacity=5
        )
    
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw quote item data into the desired format."""
        return {
            "quote_item_id": data.get("id"),
            "quote_number": safe_get(data, "quote", "number"),
            "part_number": data.get("part_number"),
            "description": data.get("description"),
            "quantity": data.get("quantity"),
            "unit_price": safe_get(data, "pricing", "unit_price"),
            "total_price": safe_get(data, "pricing", "total_price"),
            "currency": safe_get(data, "pricing", "currency"),
            "material": safe_get(data, "material", "name"),
            "finish": safe_get(data, "finish", "name"),
            "lead_time_days": data.get("lead_time_days"),
            "notes": data.get("notes")
        }

async def main():
    """Main entry point for the script."""
    # Example range - adjust as needed
    START = 1
    END = 100
    
    puller = QuoteItemsPuller()
    await puller.run(START, END)

if __name__ == "__main__":
    asyncio.run(main()) 