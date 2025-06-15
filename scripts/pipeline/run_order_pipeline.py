"""
Script for running the order and order item pipelines.

This script creates and runs pipelines for processing order and order item data
from the Paperless Parts API.
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Union, Type

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.orchestrator import Pipeline, OrderPipeline, OrderItemPipeline
from scripts.pipeline.exceptions import PipelineError


async def process_order_data(
    output_dir: str = "data_real",
    start_id: Optional[int] = None,
    end_id: Optional[int] = None
):
    """
    Process order data from the Paperless Parts API.

    Args:
        output_dir: Directory for output files
        start_id: Optional starting ID for range of orders to fetch
        end_id: Optional ending ID for range of orders to fetch
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output paths
    orders_csv_path = os.path.join(output_dir, "orders.csv")
    order_items_csv_path = os.path.join(output_dir, "order_items.csv")

    # Create and run the orders pipeline
    logger.info(f"Processing orders{' from ' + str(start_id) + ' to ' + str(end_id) if start_id and end_id else ''}")

    # Create a custom acquisition stage with the specified range
    from scripts.pipeline.processors import OrdersDataAcquisitionStage
    acquisition_stage = OrdersDataAcquisitionStage(start_id=start_id, end_id=end_id)

    # Create the orders pipeline
    orders_pipeline = Pipeline("orders_pipeline")
    orders_pipeline.add_stage(acquisition_stage)
    orders_pipeline.add_stage(OrderPipeline.create_transformation_pipeline().stages[0])  # Add validator
    orders_pipeline.add_stage(OrderPipeline.create_transformation_pipeline().stages[1])  # Add transformer
    orders_pipeline.add_stage(CSVLoader(orders_csv_path))

    # Configure a longer timeout for the acquisition stage
    acquisition_stage.configure_timeout(timeout=1200.0)  # 20 minutes timeout

    try:
        # Run the pipeline
        await orders_pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Order processing completed successfully")

        # Print metrics
        metrics = orders_pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

        # Log the output file path
        logger.info(f"Orders exported to {orders_csv_path}")

        # Process order items
        logger.info("Processing order items")

        # Create the order items pipeline
        order_items_pipeline = OrderPipeline.create_order_items_pipeline(output_path=order_items_csv_path)

        # Get the order items from the context
        order_items = acquisition_stage.get_context("order_items", [])

        if order_items:
            # Run the pipeline
            await order_items_pipeline.run(order_items)
            logger.info("Order item processing completed successfully")

            # Print metrics
            metrics = order_items_pipeline.get_metrics()
            logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

            # Log the output file path
            logger.info(f"Order items exported to {order_items_csv_path}")
        else:
            logger.warning("No order items found in the orders data")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in orders_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def process_all_data(
    output_dir: str = "data_real",
    start_id: Optional[int] = None,
    end_id: Optional[int] = None,
    orders_only: bool = False,
    order_items_only: bool = False
):
    """
    Process all data from the Paperless Parts API.

    Args:
        output_dir: Directory for output files
        start_id: Optional starting ID for range of orders to fetch
        end_id: Optional ending ID for range of orders to fetch
        orders_only: Process only orders
        order_items_only: Process only order items
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine what to process
    process_orders = not order_items_only
    process_order_items = not orders_only

    # Process orders
    if process_orders:
        await process_order_data(output_dir, start_id, end_id)


async def main():
    """
    Main entry point for the script.

    Parses command line arguments and runs the appropriate pipeline.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process order data from the Paperless Parts API")
    parser.add_argument("--output-dir", type=str, default="data_real", help="Directory for output files")
    parser.add_argument("--start-id", type=int, help="Starting order ID")
    parser.add_argument("--end-id", type=int, help="Ending order ID")
    parser.add_argument("--orders-only", action="store_true", help="Process only orders")
    parser.add_argument("--order-items-only", action="store_true", help="Process only order items")
    args = parser.parse_args()

    # Validate arguments
    if args.orders_only and args.order_items_only:
        logger.error("Cannot specify both --orders-only and --order-items-only")
        return

    if args.start_id is not None and args.end_id is None:
        logger.error("If --start-id is specified, --end-id must also be specified")
        return

    if args.start_id is None and args.end_id is not None:
        logger.error("If --end-id is specified, --start-id must also be specified")
        return

    if args.start_id is not None and args.end_id is not None and args.start_id > args.end_id:
        logger.error(f"Start ID ({args.start_id}) must be less than or equal to End ID ({args.end_id})")
        return

    # Process data
    await process_all_data(
        output_dir=args.output_dir,
        start_id=args.start_id,
        end_id=args.end_id,
        orders_only=args.orders_only,
        order_items_only=args.order_items_only
    )


if __name__ == "__main__":
    # Import here to avoid circular imports
    from scripts.pipeline.processors import CSVLoader

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Order processing interrupted by user")
    except Exception as e:
        logger.error(f"Error processing orders: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
