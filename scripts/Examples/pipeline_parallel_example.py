"""
Example script demonstrating parallel processing in the pipeline framework.

This script creates sample quote data and demonstrates how to use the parallel
processing capabilities of the pipeline framework to process multiple items concurrently.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, TypeVar, Generic

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

# Type variables for generic types
T = TypeVar('T')
U = TypeVar('U')

# Sample quote data
sample_quotes = [
    {
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
    },
    {
        "id": 12346,
        "number": "Q12346",
        "status": "open",
        "created": "2023-01-02T12:00:00Z",
        "expiration": "2023-01-16T12:00:00Z",
        "customer_name": "Another Company",
        "quote_items": [
            {
                "id": 3,
                "quantity": 20,
                "unit_price": 30.00,
                "total_price": 600.00,
                "description": "Complex Part",
                "material": "Titanium",
                "process": "CNC Machining"
            }
        ]
    },
    {
        "id": 12347,
        "number": "Q12347",
        "status": "open",
        "created": "2023-01-03T12:00:00Z",
        "expiration": "2023-01-17T12:00:00Z",
        "customer_name": "Third Company",
        "quote_items": [
            {
                "id": 4,
                "quantity": 100,
                "unit_price": 5.00,
                "total_price": 500.00,
                "description": "Simple Part",
                "material": "Plastic",
                "process": "Injection Molding"
            },
            {
                "id": 5,
                "quantity": 50,
                "unit_price": 10.00,
                "total_price": 500.00,
                "description": "Medium Part",
                "material": "Aluminum",
                "process": "CNC Machining"
            },
            {
                "id": 6,
                "quantity": 25,
                "unit_price": 20.00,
                "total_price": 500.00,
                "description": "Complex Part",
                "material": "Steel",
                "process": "CNC Machining"
            }
        ]
    }
]

# Define a quote validator with simulated processing time
class QuoteValidator(ValidationStage[Dict[str, Any]]):
    """
    Validates quote data against required fields and types.
    Includes a simulated processing delay.
    """
    
    async def validate(self, data: Dict[str, Any]) -> None:
        """
        Validate the quote data with a simulated processing delay.
        
        Args:
            data: The quote data to validate
            
        Raises:
            ValidationError: If the quote data is invalid
        """
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        required_fields = ["id", "number", "status", "created", "customer_name"]
        
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
        
        if not isinstance(data.get("id"), int):
            raise ValidationError("Quote ID must be an integer")
        
        if not isinstance(data.get("number"), str):
            raise ValidationError("Quote number must be a string")
        
        logger.info(f"Quote {data.get('number')} passed validation")

# Define a quote transformer with simulated processing time
class QuoteTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transforms raw quote data into a standardized format.
    Includes a simulated processing delay.
    """
    
    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform the quote data with a simulated processing delay.
        
        Args:
            data: The raw quote data to transform
            
        Returns:
            The transformed quote data
        """
        # Simulate processing time
        await asyncio.sleep(0.5)
        
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

# Define a parallel processing stage
class ParallelProcessingStage(PipelineStage, Generic[T, U]):
    """
    A pipeline stage that processes multiple items in parallel.
    """
    
    def __init__(self, name: str, pipeline: Pipeline, max_concurrency: int = 5):
        """
        Initialize the parallel processing stage.
        
        Args:
            name: The name of the stage
            pipeline: The pipeline to use for processing each item
            max_concurrency: The maximum number of concurrent tasks
        """
        super().__init__(name)
        self.pipeline = pipeline
        self.max_concurrency = max_concurrency
    
    async def process(self, data: List[T]) -> List[U]:
        """
        Process multiple items in parallel.
        
        Args:
            data: The list of items to process
            
        Returns:
            The list of processed items
        """
        logger.info(f"Processing {len(data)} items in parallel with max concurrency {self.max_concurrency}")
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrency)
        
        async def process_item(item: T) -> U:
            """
            Process a single item with concurrency control.
            
            Args:
                item: The item to process
                
            Returns:
                The processed item
            """
            async with semaphore:
                return await self.pipeline.run(item)
        
        # Create tasks for all items
        tasks = [process_item(item) for item in data]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Completed processing {len(results)} items in parallel")
        return results

# Define a CSV loader with simulated processing time
class CSVLoader(LoadingStage[Dict[str, Any]]):
    """
    Loads data into a CSV file.
    Includes a simulated processing delay.
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
        Load the data into a CSV file with a simulated processing delay.
        
        Args:
            data: The data to load
        """
        # Simulate processing time
        await asyncio.sleep(0.5)
        
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

async def run_sequential(quotes: List[Dict[str, Any]]) -> None:
    """
    Process quotes sequentially.
    
    Args:
        quotes: The list of quotes to process
    """
    logger.info("Starting sequential processing")
    start_time = time.time()
    
    # Create a pipeline for processing quotes
    pipeline = Pipeline("sequential_pipeline")
    pipeline.add_stage(QuoteValidator("quote_validator"))
    pipeline.add_stage(QuoteTransformer("quote_transformer"))
    pipeline.add_stage(CSVLoader("csv_loader", "data_pipeline_example/quotes_sequential.csv"))
    
    # Process each quote sequentially
    for quote in quotes:
        await pipeline.run(quote)
    
    end_time = time.time()
    logger.info(f"Sequential processing completed in {end_time - start_time:.2f} seconds")

async def run_parallel(quotes: List[Dict[str, Any]], max_concurrency: int) -> None:
    """
    Process quotes in parallel.
    
    Args:
        quotes: The list of quotes to process
        max_concurrency: The maximum number of concurrent tasks
    """
    logger.info(f"Starting parallel processing with max concurrency {max_concurrency}")
    start_time = time.time()
    
    # Create a pipeline for processing a single quote
    item_pipeline = Pipeline("item_pipeline")
    item_pipeline.add_stage(QuoteValidator("quote_validator"))
    item_pipeline.add_stage(QuoteTransformer("quote_transformer"))
    item_pipeline.add_stage(CSVLoader("csv_loader", "data_pipeline_example/quotes_parallel.csv"))
    
    # Create a parallel processing stage
    parallel_stage = ParallelProcessingStage("parallel_processor", item_pipeline, max_concurrency)
    
    # Process all quotes in parallel
    await parallel_stage.process(quotes)
    
    end_time = time.time()
    logger.info(f"Parallel processing completed in {end_time - start_time:.2f} seconds")

async def main():
    """
    Main function to demonstrate parallel processing.
    """
    logger.info("Starting parallel processing example")
    
    try:
        # Run sequential processing
        await run_sequential(sample_quotes)
        
        # Run parallel processing with different concurrency levels
        for concurrency in [1, 2, 3]:
            await run_parallel(sample_quotes, concurrency)
        
        logger.info("All examples completed successfully")
    
    except Exception as e:
        logger.error(f"Error in parallel processing example: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())