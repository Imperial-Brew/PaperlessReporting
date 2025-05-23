import asyncio
from typing import Dict, Any
from scripts.utils.async_puller import AsyncPuller
from scripts.utils.utils import safe_get

class QuotesPuller(AsyncPuller[Dict[str, Any]]):
    """Async puller for quotes."""
    
    def __init__(self):
        super().__init__(
            endpoint="quotes/public",
            rate=1.8,
            capacity=5
        )
    
    def transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw quote data into the desired format."""
        return {
            "quote_number": data.get("number"),
            "status": data.get("status"),
            "created": data.get("created"),
            "customer_name": safe_get(data, "customer", "business_name"),
            "salesperson_email": safe_get(data, "salesperson", "email"),
            "total_price": safe_get(data, "pricing", "total_price"),
            "currency": safe_get(data, "pricing", "currency"),
            "payment_terms": safe_get(data, "payment_details", "payment_terms"),
            "notes": data.get("notes"),
            "revision_number": data.get("revision_number")
        }

async def main():
    """Main entry point for the script."""
    # Example range - adjust as needed
    START = 7500
    END = 7550
    
    puller = QuotesPuller()
    await puller.run(START, END)

if __name__ == "__main__":
    asyncio.run(main()) 