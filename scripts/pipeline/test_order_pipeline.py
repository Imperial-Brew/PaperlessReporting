"""
Test script for the order and order item pipelines.

This script tests the functionality of the order and order item pipelines
by creating sample order data and running it through the various pipeline
configurations.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.orchestrator import OrderPipeline, OrderItemPipeline
from scripts.pipeline.exceptions import PipelineError


@pytest.mark.asyncio
async def test_order_pipelines():
    """
    Test the order pipeline configurations.
    """
    # Create a sample order
    sample_order = {
        "order_number": "O12345",
        "status": "in_production",
        "quote_number": "Q12345",
        "quote_revision_number": 1,
        "created": "2023-01-01T12:00:00Z",
        "deliver_by": "2023-01-15T12:00:00Z",
        "ships_on": "2023-01-10T12:00:00Z",
        "payment_terms": "Net 30",
        "purchase_order_number": "PO12345",
        "salesperson_email": "sales@example.com",
        "customer_name": "Example Company",
        "order_items": [
            {
                "id": 1,
                "quantity": 10,
                "unit_price": 25.50,
                "total_price": 255.00,
                "description": "Sample Part",
                "export_controlled": False,
                "components": [
                    {
                        "is_root_component": True,
                        "part_number": "PART-001",
                        "part_uuid": "abc123",
                        "revision": "A",
                        "material": {
                            "name": "Aluminum 6061"
                        },
                        "process": {
                            "name": "CNC Machining"
                        }
                    }
                ]
            },
            {
                "id": 2,
                "quantity": 5,
                "unit_price": 15.75,
                "total_price": 78.75,
                "description": "Another Part",
                "export_controlled": False,
                "components": [
                    {
                        "is_root_component": True,
                        "part_number": "PART-002",
                        "part_uuid": "def456",
                        "revision": "B",
                        "material": {
                            "name": "Steel 1018"
                        },
                        "process": {
                            "name": "Laser Cutting"
                        }
                    }
                ]
            }
        ]
    }

    # Create output directory
    output_dir = project_root / "data_pipeline_example"
    os.makedirs(output_dir, exist_ok=True)

    # Save the sample order to a JSON file
    sample_order_path = output_dir / "sample_order.json"
    with open(sample_order_path, "w") as f:
        json.dump(sample_order, f, indent=2)

    logger.info(f"Saved sample order to {sample_order_path}")

    # Test 1: Validate an order
    logger.info("Test 1: Validating an order")
    validation_pipeline = OrderPipeline.create_validation_pipeline()

    try:
        # Run the pipeline
        await validation_pipeline.run(sample_order)
        logger.info("Order validation successful")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in validation_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")

    # Print validation metrics
    logger.info("Validation metrics:")
    for stage_name, metrics in validation_pipeline.get_metrics().get("stage_metrics", {}).items():
        logger.info(f"  {stage_name}: {metrics['metrics']}")

    # Test 2: Transform an order
    logger.info("\nTest 2: Transforming an order")
    transformation_pipeline = OrderPipeline.create_transformation_pipeline()

    try:
        # Run the pipeline
        transformed_order = await transformation_pipeline.run(sample_order)
        logger.info("Order transformation successful")
        logger.info(f"Transformed order: {transformed_order}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Test 3: Export an order to CSV
    logger.info("\nTest 3: Exporting an order to CSV")
    csv_path = output_dir / "sample_order.csv"
    csv_pipeline = OrderPipeline.create_csv_export_pipeline(str(csv_path))

    try:
        # Run the pipeline
        await csv_pipeline.run(sample_order)
        logger.info(f"Order exported to {csv_path}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Test 4: Extract and validate order items
    logger.info("\nTest 4: Extracting and validating order items")
    extraction_pipeline = OrderItemPipeline.create_extraction_pipeline(sample_order)

    try:
        # Run the pipeline
        order_items = await extraction_pipeline.run(sample_order)
        logger.info(f"Extracted {len(order_items)} valid order items")
        for item in order_items:
            logger.info(f"  Item: {item['part_number']} - {item['description']}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Test 5: Export order items to CSV
    logger.info("\nTest 5: Exporting order items to CSV")
    items_csv_path = output_dir / "sample_order_items.csv"
    items_csv_pipeline = OrderItemPipeline.create_csv_export_pipeline(str(items_csv_path))

    try:
        # Extract order items first
        order_items = await extraction_pipeline.run(sample_order)

        # Process each order item through the CSV export pipeline
        for item in order_items:
            await items_csv_pipeline.run(item)

        logger.info(f"Order items exported to {items_csv_path}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")

    # Test 6: Test the order_items_pipeline method in OrderPipeline
    logger.info("\nTest 6: Testing OrderPipeline.create_order_items_pipeline")

    # First, set up a context with order_items
    from scripts.pipeline.orchestrator import Pipeline, ContextExtractor
    from scripts.pipeline.processors import OrderItemExtractor

    # Extract order items
    extractor = OrderItemExtractor()
    order_items = await extractor.transform(sample_order)

    # Create a pipeline that sets the context
    setup_pipeline = Pipeline("setup_pipeline")

    # Add a stage that sets the context
    class ContextSetter(OrderItemExtractor):
        async def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
            items = await super().transform(data)
            self.set_context("order_items", items)
            return items

    setup_pipeline.add_stage(ContextSetter())

    # Run the setup pipeline
    await setup_pipeline.run(sample_order)

    # Get the context from the setup pipeline
    context_setter = setup_pipeline.stages[0]
    order_items_context = context_setter.get_context("order_items")

    # Now create the order_items_pipeline
    items_pipeline_path = output_dir / "order_items_pipeline.csv"
    order_items_pipeline = OrderPipeline.create_order_items_pipeline(str(items_pipeline_path))

    # Get the ContextExtractor stage and set the context
    context_extractor = order_items_pipeline.stages[0]
    context_extractor.set_context("order_items", order_items_context)

    try:
        # Run the pipeline
        await order_items_pipeline.run(None)  # Input is None because it uses context
        logger.info(f"Order items processed through OrderPipeline.create_order_items_pipeline and exported to {items_pipeline_path}")
    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")


@pytest.mark.asyncio
async def test_invalid_order():
    """
    Test validation with an invalid order.
    """
    logger.info("\nTesting validation with an invalid order")

    # Create an invalid order
    invalid_order = {
        "number": "O12345",  # Wrong field name
        # Missing required status field
        "created": "2023-01-01T12:00:00Z",
        "salesperson_email": "not-an-email"  # Invalid email format
    }

    validation_pipeline = OrderPipeline.create_validation_pipeline()

    try:
        # Run the pipeline
        await validation_pipeline.run(invalid_order)
        logger.info("Order validation successful (unexpected)")
    except PipelineError as e:
        logger.error(f"Pipeline error (expected): {e.message}")

        # Print validation errors
        for stage_name, metrics in validation_pipeline.get_metrics().get("stage_metrics", {}).items():
            if "validation_errors" in metrics.get("metrics", {}):
                logger.error(f"  Validation errors: {metrics['metrics']['validation_errors']}")


async def main():
    """
    Run all the tests.
    """
    await test_order_pipelines()
    await test_invalid_order()


if __name__ == "__main__":
    asyncio.run(main())
