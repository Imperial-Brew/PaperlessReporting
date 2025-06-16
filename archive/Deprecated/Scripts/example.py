"""
[ARCHIVED] Example script demonstrating the pipeline framework.

This script has been archived and moved to scripts/Examples/pipeline_example.py.
Please use the new location for the latest version.

This script shows how to use the pipeline framework to process quote data.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.orchestrator import QuotePipeline, QuoteItemPipeline
from scripts.pipeline.exceptions import PipelineError


async def process_quote_example():
    """
    Example of processing a quote through the pipeline.
    """
    # Create a sample quote
    sample_quote = {
        "quote_number": "Q12345",
        "revision_number": 1,
        "status": "sent",
        "created": "2023-01-01T12:00:00Z",
        "due_date": "2023-01-15T12:00:00Z",
        "contact": {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "account": {
                "name": "Example Company"
            }
        },
        "estimator": {
            "email": "estimator@example.com"
        },
        "salesperson": {
            "email": "sales@example.com"
        },
        "quote_items": [
            {
                "id": 1,
                "workflow_status": "pending",
                "export_controlled": False,
                "components": [
                    {
                        "is_root_component": True,
                        "part_number": "PART-001",
                        "revision": "A",
                        "description": "Sample Part",
                        "type": "machined",
                        "material": {
                            "name": "Aluminum 6061"
                        },
                        "process": {
                            "name": "CNC Machining"
                        },
                        "quantities": [
                            {
                                "quantity": 10,
                                "unit_price": 25.50,
                                "total_price": 255.00,
                                "total_price_with_required_add_ons": 275.00,
                                "lead_time": "2 weeks"
                            }
                        ]
                    }
                ]
            }
        ]
    }

    # Create output directory
    output_dir = project_root / "data_pipeline_example"
    os.makedirs(output_dir, exist_ok=True)

    # Save the sample quote to a JSON file
    sample_quote_path = output_dir / "sample_quote.json"
    with open(sample_quote_path, "w") as f:
        json.dump(sample_quote, f, indent=2)

    logger.info(f"Saved sample quote to {sample_quote_path}")

    # Example 1: Validate a quote
    logger.info("Example 1: Validating a quote")
    validation_pipeline = QuotePipeline.create_validation_pipeline()

    try:
        # Run the pipeline
        await validation_pipeline.run(sample_quote)
        logger.info("Quote validation successful")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in validation_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")

    # Print validation metrics
    logger.info("Validation metrics:")
    for stage_name, metrics in validation_pipeline.get_metrics().get("stage_metrics", {}).items():
        logger.info(f"  {stage_name}: {metrics['metrics']}")

    # Example 2: Transform a quote
    logger.info("\nExample 2: Transforming a quote")
    transformation_pipeline = QuotePipeline.create_transformation_pipeline()

    try:
        # Run the pipeline
        transformed_quote = await transformation_pipeline.run(sample_quote)
        logger.info("Quote transformation successful")
        logger.info(f"Transformed quote: {transformed_quote}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Example 3: Export a quote to CSV
    logger.info("\nExample 3: Exporting a quote to CSV")
    csv_path = output_dir / "sample_quote.csv"
    csv_pipeline = QuotePipeline.create_csv_export_pipeline(str(csv_path))

    try:
        # Run the pipeline
        await csv_pipeline.run(sample_quote)
        logger.info(f"Quote exported to {csv_path}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Example 4: Extract and validate quote items
    logger.info("\nExample 4: Extracting and validating quote items")
    quote_item_pipeline = QuoteItemPipeline.create_validation_pipeline()

    try:
        # Run the pipeline
        quote_items = await quote_item_pipeline.run(sample_quote)
        logger.info(f"Extracted {len(quote_items)} valid quote items")
        for item in quote_items:
            logger.info(f"  Item: {item['part_number']} - {item['description']}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Example 5: Export quote items to CSV
    logger.info("\nExample 5: Exporting quote items to CSV")
    items_csv_path = output_dir / "sample_quote_items.csv"
    items_csv_pipeline = QuoteItemPipeline.create_csv_export_pipeline(str(items_csv_path))

    try:
        # Run the pipeline
        await items_csv_pipeline.run(sample_quote)
        logger.info(f"Quote items exported to {items_csv_path}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Example 6: Demonstrate error handling with invalid data
    logger.info("\nExample 6: Demonstrating error handling with invalid data")
    invalid_quote = {
        "number": "Q12345",
        # Missing required fields
        "contact": {
            "first_name": "John"
            # Missing last_name and email
        }
    }

    validation_pipeline = QuotePipeline.create_validation_pipeline()

    try:
        # Run the pipeline
        await validation_pipeline.run(invalid_quote)
        logger.info("Quote validation successful (unexpected)")
    except PipelineError as e:
        logger.error(f"Pipeline error (expected): {e.message}")

        # Print validation errors
        for stage_name, metrics in validation_pipeline.get_metrics().get("stage_metrics", {}).items():
            if "validation_errors" in metrics.get("metrics", {}):
                logger.error(f"  Validation errors: {metrics['metrics']['validation_errors']}")


if __name__ == "__main__":
    asyncio.run(process_quote_example())
