"""
Example script demonstrating the pipeline builder pattern.

This script creates sample quote data and uses the pipeline builder pattern
to create and run various pipeline configurations.
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
from scripts.pipeline.builder import PipelineBuilder

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

# Define a quote pipeline builder
class QuotePipelineBuilder(PipelineBuilder):
    """
    Builder for quote processing pipelines.
    """
    
    def __init__(self, name: str = "quote_pipeline"):
        """
        Initialize the quote pipeline builder.
        
        Args:
            name: The name of the pipeline
        """
        super().__init__(name)
    
    def add_validation(self) -> "QuotePipelineBuilder":
        """
        Add a validation stage to the pipeline.
        
        Returns:
            The builder instance for method chaining
        """
        self.add_stage(QuoteValidator("quote_validator"))
        return self
    
    def add_transformation(self) -> "QuotePipelineBuilder":
        """
        Add a transformation stage to the pipeline.
        
        Returns:
            The builder instance for method chaining
        """
        self.add_stage(QuoteTransformer("quote_transformer"))
        return self
    
    def add_csv_export(self, output_path: str) -> "QuotePipelineBuilder":
        """
        Add a CSV export stage to the pipeline.
        
        Args:
            output_path: The path to the output CSV file
            
        Returns:
            The builder instance for method chaining
        """
        self.add_stage(CSVLoader("csv_loader", output_path))
        return self
    
    def add_item_extraction(self) -> "QuotePipelineBuilder":
        """
        Add a quote item extraction stage to the pipeline.
        
        Returns:
            The builder instance for method chaining
        """
        self.add_stage(QuoteItemExtractor("quote_item_extractor"))
        return self

async def main():
    """
    Main function to demonstrate the pipeline builder pattern.
    """
    logger.info("Starting pipeline builder example")
    
    try:
        # Example 1: Quote validation pipeline
        logger.info("Example 1: Quote validation pipeline")
        validation_pipeline = QuotePipelineBuilder("quote_validation") \
            .add_validation() \
            .build()
        
        await validation_pipeline.run(sample_quote)
        logger.info("Quote validation pipeline completed successfully")
        
        # Example 2: Quote transformation pipeline
        logger.info("Example 2: Quote transformation pipeline")
        transformation_pipeline = QuotePipelineBuilder("quote_transformation") \
            .add_validation() \
            .add_transformation() \
            .build()
        
        transformed_quote = await transformation_pipeline.run(sample_quote)
        logger.info(f"Transformed quote: {json.dumps(transformed_quote, indent=2)}")
        
        # Example 3: Quote CSV export pipeline
        logger.info("Example 3: Quote CSV export pipeline")
        csv_pipeline = QuotePipelineBuilder("quote_csv_export") \
            .add_validation() \
            .add_transformation() \
            .add_csv_export("data_pipeline_example/quotes_builder.csv") \
            .build()
        
        await csv_pipeline.run(sample_quote)
        logger.info("Quote CSV export pipeline completed successfully")
        
        # Example 4: Quote item extraction pipeline
        logger.info("Example 4: Quote item extraction pipeline")
        extraction_pipeline = QuotePipelineBuilder("quote_item_extraction") \
            .add_validation() \
            .add_item_extraction() \
            .build()
        
        quote_items = await extraction_pipeline.run(sample_quote)
        logger.info(f"Extracted quote items: {json.dumps(quote_items, indent=2)}")
        
        # Example 5: Combined pipeline
        logger.info("Example 5: Combined pipeline")
        combined_pipeline = QuotePipelineBuilder("combined_pipeline") \
            .add_validation() \
            .add_transformation() \
            .add_csv_export("data_pipeline_example/quotes_combined.csv") \
            .build()
        
        await combined_pipeline.run(sample_quote)
        logger.info("Combined pipeline completed successfully")
        
        logger.info("All examples completed successfully")
    
    except Exception as e:
        logger.error(f"Error in pipeline builder example: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())