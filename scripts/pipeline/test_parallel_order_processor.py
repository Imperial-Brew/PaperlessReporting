"""
Test script for parallel order item processing.

This script tests the functionality of the parallel order item processing
classes implemented in parallel_order_processor.py.
"""

import asyncio
import sys
import time
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
from scripts.pipeline.parallel_order_processor import ParallelOrderItemProcessor, ParallelOrderProcessor
from scripts.pipeline.pipeline_testing import TestDataGenerator
from scripts.pipeline.exceptions import PipelineError


async def test_parallel_extraction_pipeline():
    """
    Test the parallel extraction pipeline.
    """
    logger.info("=== Testing Parallel Extraction Pipeline ===")

    # Create sample orders
    orders = [TestDataGenerator.create_sample_order() for _ in range(5)]

    # Create a temporary output path
    output_path = TestDataGenerator.create_temp_output_path()

    # Create the pipeline
    pipeline = ParallelOrderItemProcessor.create_parallel_extraction_pipeline(
        max_concurrency=3,
        batch_size=2,
        output_path=output_path
    )

    # Run the pipeline
    try:
        start_time = time.time()
        result = await pipeline.run(orders)
        end_time = time.time()

        # Log results
        logger.info(f"Parallel extraction pipeline completed in {end_time - start_time:.2f}s")

        # Check metrics
        metrics = pipeline.get_metrics()

        # Get the number of order items from the metrics
        extractor_metrics = metrics.get("stage_metrics", {}).get("parallel_order_item_extractor", {}).get("metrics", {})
        order_items_count = extractor_metrics.get("order_items_extracted", 0)
        logger.info(f"Extracted {order_items_count} order items")

        logger.info(f"Pipeline metrics: {metrics}")

        # Check if the output file was created
        import os
        if os.path.exists(output_path):
            logger.info(f"Output file created: {output_path}")

            # Read the output file
            import csv
            with open(output_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
                logger.info(f"Output file has {len(rows)} rows (excluding header)")
                logger.info(f"Output file header: {header}")
        else:
            logger.error(f"Output file not created: {output_path}")

        logger.info("Parallel extraction pipeline test passed")
    except PipelineError as e:
        logger.error(f"Parallel extraction pipeline test failed: {e}")


async def test_parallel_processing_pipeline():
    """
    Test the parallel processing pipeline.
    """
    logger.info("\n=== Testing Parallel Processing Pipeline ===")

    # Create sample order items
    order = TestDataGenerator.create_sample_order()

    # Extract order items
    from scripts.pipeline.order_processors import OrderItemExtractor
    extractor = OrderItemExtractor()
    order_items = await extractor.transform(order)

    # Create a temporary output path
    output_path = TestDataGenerator.create_temp_output_path()

    # Create the pipeline
    pipeline = ParallelOrderItemProcessor.create_parallel_processing_pipeline(
        max_concurrency=3,
        batch_size=2,
        output_path=output_path
    )

    # Set the context
    for stage in pipeline.stages:
        stage.set_context("order_items", order_items)

    # Run the pipeline
    try:
        start_time = time.time()
        result = await pipeline.run(None)
        end_time = time.time()

        # Log results
        logger.info(f"Parallel processing pipeline completed in {end_time - start_time:.2f}s")

        # Check metrics
        metrics = pipeline.get_metrics()

        # Get the number of order items from the context
        order_items_count = len(order_items)
        logger.info(f"Processed {order_items_count} order items")

        logger.info(f"Pipeline metrics: {metrics}")

        # Check if the output file was created
        import os
        if os.path.exists(output_path):
            logger.info(f"Output file created: {output_path}")

            # Read the output file
            import csv
            with open(output_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
                logger.info(f"Output file has {len(rows)} rows (excluding header)")
                logger.info(f"Output file header: {header}")
        else:
            logger.error(f"Output file not created: {output_path}")

        logger.info("Parallel processing pipeline test passed")
    except PipelineError as e:
        logger.error(f"Parallel processing pipeline test failed: {e}")


async def test_parallel_order_processor():
    """
    Test the parallel order processor.
    """
    logger.info("\n=== Testing Parallel Order Processor ===")

    # Create a temporary output directory
    import tempfile
    output_dir = tempfile.mkdtemp()

    # Create output paths
    import os
    orders_path = os.path.join(output_dir, "orders.csv")
    items_path = os.path.join(output_dir, "order_items.csv")

    # Create the pipeline
    pipeline = ParallelOrderProcessor.create_acquisition_pipeline(
        start_id=1,
        end_id=10,
        max_concurrency=3,
        batch_size=2,
        output_path=orders_path,
        items_output_path=items_path
    )

    # Mock the OrdersDataAcquisitionStage to return sample orders
    from scripts.pipeline.order_processors import OrdersDataAcquisitionStage

    # Save the original acquire method
    original_acquire = OrdersDataAcquisitionStage.acquire

    # Create a mock acquire method
    async def mock_acquire(self):
        # Create sample orders
        orders = [TestDataGenerator.create_sample_order() for _ in range(5)]

        # Create sample order items
        order_items = []
        for order in orders:
            from scripts.pipeline.order_processors import OrderItemExtractor
            extractor = OrderItemExtractor()
            items = await extractor.transform(order)
            order_items.extend(items)

        # Store order items in context
        self.set_context("order_items", order_items)

        return orders

    # Replace the acquire method with the mock
    OrdersDataAcquisitionStage.acquire = mock_acquire

    # Run the pipeline
    try:
        start_time = time.time()
        result = await pipeline.run(None)
        end_time = time.time()

        # Log results
        logger.info(f"Parallel order processor completed in {end_time - start_time:.2f}s")

        # Check metrics
        metrics = pipeline.get_metrics()

        # Get the number of orders from the metrics
        batch_transformer_metrics = metrics.get("stage_metrics", {}).get("batch_order_transformer", {}).get("metrics", {})
        orders_count = batch_transformer_metrics.get("successful_items", 0)
        logger.info(f"Processed {orders_count} orders")

        logger.info(f"Pipeline metrics: {metrics}")

        # Check if the output files were created
        if os.path.exists(orders_path):
            logger.info(f"Orders output file created: {orders_path}")

            # Read the output file
            import csv
            with open(orders_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
                logger.info(f"Orders output file has {len(rows)} rows (excluding header)")
                logger.info(f"Orders output file header: {header}")
        else:
            logger.error(f"Orders output file not created: {orders_path}")

        if os.path.exists(items_path):
            logger.info(f"Order items output file created: {items_path}")

            # Read the output file
            import csv
            with open(items_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader)
                rows = list(reader)
                logger.info(f"Order items output file has {len(rows)} rows (excluding header)")
                logger.info(f"Order items output file header: {header}")
        else:
            logger.error(f"Order items output file not created: {items_path}")

        logger.info("Parallel order processor test passed")
    except PipelineError as e:
        logger.error(f"Parallel order processor test failed: {e}")
    finally:
        # Restore the original acquire method
        OrdersDataAcquisitionStage.acquire = original_acquire


async def main():
    """
    Run all the tests.
    """
    await test_parallel_extraction_pipeline()
    await test_parallel_processing_pipeline()
    await test_parallel_order_processor()


if __name__ == "__main__":
    asyncio.run(main())
