"""
Example script demonstrating the pipeline framework.

This script creates sample quote data and runs it through various pipeline
configurations to demonstrate the functionality of the pipeline framework.
"""

import asyncio
import json
import os
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

# Import pipeline components
from scripts.pipeline.base import PipelineStage, ValidationStage, TransformationStage, LoadingStage
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.exceptions import PipelineError, ValidationError

# Sample quote data
sample_quote = {
    "id": 12345,
    "number": "Q12345",
    "status": "open",
    "created": "2023-01-01T12:00:00Z",
    "expiration": "2023-01-15T12:00:00Z",
    "customer_name": "Example Company",
    "quote_items": [
        {
            "id": 1,
            "quantity": 10,
            "unit_price": 25.50,
            "total_price": 255.00,
            "description": "Sample Part",
            "material": "Aluminum 6061",
            "process": "CNC Machining"
        },
        {
            "id": 2,
            "quantity": 5,
            "unit_price": 15.75,
            "total_price": 78.75,
            "description": "Another Part",
            "material": "Steel 1018",
            "process": "Laser Cutting"
        }
    ]
}

# Define a quote validator
class QuoteValidator(ValidationStage[Dict[str, Any]]):
    """
    Validates quote data against required fields and types.
    """
    
    async def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate the quote data.
        
        Args:
            data: The quote data to validate
            
        Raises:
            ValidationError: If the quote data is invalid
        """
        required_fields = ["id", "number", "status", "created", "customer_name"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not isinstance(data.get("id"), int):
            raise ValidationError("Quote ID must be an integer")
        
        if not isinstance(data.get("number"), str):
            raise ValidationError("Quote number must be a string")
        
        logger.info(f"Quote {data.get('number')} passed validation")

# Define a quote transformer
class QuoteTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transforms raw quote data into a standardized format.
    """
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the quote data.
        
        Args:
            data: The raw quote data to transform
            
        Returns:
            The transformed quote data
        """
        transformed = {
            "quote_id": data.get("id"),
            "quote_number": data.get("number"),
            "status": data.get("status"),
            "created_date": data.get("created"),
            "expiration_date": data.get("expiration"),
            "customer": data.get("customer_name"),
            "item_count": len(data.get("quote_items", [])),
            "total_value": sum(item.get("total_price", 0) for item in data.get("quote_items", []))
        }
        
        logger.info(f"Transformed quote {data.get('number')}")
        return transformed

# Define a CSV loader
class CSVLoader(LoadingStage[Dict[str, Any]]):
    """
    Loads data into a CSV file.
    """
    
    def __init__(self, name: str, output_path: str):
        """
        Initialize the CSV loader.
        
        Args:
            name: The name of the stage
            output_path: The path to the output CSV file
        """
        super().__init__(name)
        self.output_path = output_path
    
    async def load(self, data: Dict[str, Any]) -> None:
        """
        Load the data into a CSV file.
        
        Args:
            data: The data to load
        """
        # Create the output directory if it doesn't exist
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # Write the header row if the file doesn't exist
        file_exists = os.path.exists(self.output_path)
        
        with open(self.output_path, "a", newline="") as f:
            if not file_exists:
                header = ",".join(data.keys())
                f.write(header + "\n")
            
            # Write the data row
            values = [str(value) for value in data.values()]
            row = ",".join(values)
            f.write(row + "\n")
        
        logger.info(f"Saved data to {self.output_path}")

# Define a quote item extractor
class QuoteItemExtractor(TransformationStage[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Extracts quote items from a quote.
    """
    
    async def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract quote items from the quote.
        
        Args:
            data: The quote data
            
        Returns:
            The extracted quote items
        """
        quote_items = data.get("quote_items", [])
        
        # Add the quote number to each item
        for item in quote_items:
            item["quote_number"] = data.get("number")
        
        logger.info(f"Extracted {len(quote_items)} items from quote {data.get('number')}")
        return quote_items

# Define a quote item validator
class QuoteItemValidator(ValidationStage[Dict[str, Any]]):
    """
    Validates quote item data against required fields and types.
    """
    
    async def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate the quote item data.
        
        Args:
            data: The quote item data to validate
            
        Raises:
            ValidationError: If the quote item data is invalid
        """
        required_fields = ["id", "quantity", "unit_price", "total_price", "description"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not isinstance(data.get("id"), int):
            raise ValidationError("Quote item ID must be an integer")
        
        if not isinstance(data.get("quantity"), (int, float)):
            raise ValidationError("Quantity must be a number")
        
        if not isinstance(data.get("unit_price"), (int, float)):
            raise ValidationError("Unit price must be a number")
        
        if not isinstance(data.get("total_price"), (int, float)):
            raise ValidationError("Total price must be a number")
        
        logger.info(f"Quote item {data.get('id')} passed validation")

# Define a quote item transformer
class QuoteItemTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transforms raw quote item data into a standardized format.
    """
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the quote item data.
        
        Args:
            data: The raw quote item data to transform
            
        Returns:
            The transformed quote item data
        """
        transformed = {
            "item_id": data.get("id"),
            "quote_number": data.get("quote_number"),
            "quantity": data.get("quantity"),
            "unit_price": data.get("unit_price"),
            "total_price": data.get("total_price"),
            "description": data.get("description"),
            "material": data.get("material"),
            "process": data.get("process")
        }
        
        logger.info(f"Transformed quote item {data.get('id')}")
        return transformed

async def main():
    """
    Main function to demonstrate the pipeline framework.
    """
    logger.info("Starting pipeline example")
    
    try:
        # Example 1: Quote validation pipeline
        logger.info("Example 1: Quote validation pipeline")
        validation_pipeline = Pipeline("quote_validation")
        validation_pipeline.add_stage(QuoteValidator("quote_validator"))
        
        await validation_pipeline.run(sample_quote)
        logger.info("Quote validation pipeline completed successfully")
        
        # Example 2: Quote transformation pipeline
        logger.info("Example 2: Quote transformation pipeline")
        transformation_pipeline = Pipeline("quote_transformation")
        transformation_pipeline.add_stage(QuoteValidator("quote_validator"))
        transformation_pipeline.add_stage(QuoteTransformer("quote_transformer"))
        
        transformed_quote = await transformation_pipeline.run(sample_quote)
        logger.info(f"Transformed quote: {json.dumps(transformed_quote, indent=2)}")
        
        # Example 3: Quote CSV export pipeline
        logger.info("Example 3: Quote CSV export pipeline")
        csv_pipeline = Pipeline("quote_csv_export")
        csv_pipeline.add_stage(QuoteValidator("quote_validator"))
        csv_pipeline.add_stage(QuoteTransformer("quote_transformer"))
        csv_pipeline.add_stage(CSVLoader("csv_loader", "data_pipeline_example/quotes.csv"))
        
        await csv_pipeline.run(sample_quote)
        logger.info("Quote CSV export pipeline completed successfully")
        
        # Example 4: Quote item extraction pipeline
        logger.info("Example 4: Quote item extraction pipeline")
        extraction_pipeline = Pipeline("quote_item_extraction")
        extraction_pipeline.add_stage(QuoteValidator("quote_validator"))
        extraction_pipeline.add_stage(QuoteItemExtractor("quote_item_extractor"))
        
        quote_items = await extraction_pipeline.run(sample_quote)
        logger.info(f"Extracted quote items: {json.dumps(quote_items, indent=2)}")
        
        # Example 5: Quote item validation pipeline
        logger.info("Example 5: Quote item validation pipeline")
        item_validation_pipeline = Pipeline("quote_item_validation")
        item_validation_pipeline.add_stage(QuoteItemValidator("quote_item_validator"))
        
        for item in quote_items:
            await item_validation_pipeline.run(item)
        logger.info("Quote item validation pipeline completed successfully")
        
        # Example 6: Quote item transformation pipeline
        logger.info("Example 6: Quote item transformation pipeline")
        item_transformation_pipeline = Pipeline("quote_item_transformation")
        item_transformation_pipeline.add_stage(QuoteItemValidator("quote_item_validator"))
        item_transformation_pipeline.add_stage(QuoteItemTransformer("quote_item_transformer"))
        
        transformed_items = []
        for item in quote_items:
            transformed_item = await item_transformation_pipeline.run(item)
            transformed_items.append(transformed_item)
        
        logger.info(f"Transformed quote items: {json.dumps(transformed_items, indent=2)}")
        
        # Example 7: Quote item CSV export pipeline
        logger.info("Example 7: Quote item CSV export pipeline")
        item_csv_pipeline = Pipeline("quote_item_csv_export")
        item_csv_pipeline.add_stage(QuoteItemValidator("quote_item_validator"))
        item_csv_pipeline.add_stage(QuoteItemTransformer("quote_item_transformer"))
        item_csv_pipeline.add_stage(CSVLoader("csv_loader", "data_pipeline_example/quote_items.csv"))
        
        for item in quote_items:
            await item_csv_pipeline.run(item)
        logger.info("Quote item CSV export pipeline completed successfully")
        
        # Example 8: Error handling
        logger.info("Example 8: Error handling")
        invalid_quote = {
            "id": "not_an_integer",  # This should be an integer
            "number": "Q12345",
            "status": "open",
            "created": "2023-01-01T12:00:00Z",
            "customer_name": "Example Company"
        }
        
        try:
            await validation_pipeline.run(invalid_quote)
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
        except PipelineError as e:
            logger.error(f"Pipeline error: {str(e)}")
        
        logger.info("All examples completed successfully")
    
    except Exception as e:
        logger.error(f"Error in pipeline example: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())