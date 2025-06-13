"""
Parallel processing for order items in the pipeline framework.

This module provides parallel implementations of order item processing
to improve performance when processing large numbers of orders and order items.
"""

import asyncio
from typing import Any, Dict, List, Optional, Union

from scripts.pipeline.base import PipelineStage, TransformationStage
from scripts.pipeline.orchestrator import Pipeline, ContextExtractor
from scripts.pipeline.processors import BatchProcessor, ParallelStage
from scripts.pipeline.order_processors import OrderItemValidator, OrderItemTransformer, OrderItemExtractor
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class ParallelOrderItemProcessor:
    """
    Factory for creating pipelines that process order items in parallel.
    
    This class provides methods for creating pipelines that extract and process
    order items from orders with parallel processing for improved performance.
    """
    
    @staticmethod
    def create_parallel_extraction_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        name: str = "parallel_order_item_extraction_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for extracting and processing order items in parallel.
        
        This pipeline extracts order items from a list of orders and processes
        them in parallel for improved performance.
        
        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file (if None, no CSV is generated)
            name: Name of the pipeline
            
        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import CSVLoader
        
        # Create pipeline
        pipeline = Pipeline(name)
        
        # Add extraction stage with parallel processing
        class ParallelOrderItemExtractor(TransformationStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
            """
            Transformation stage that extracts order items from a list of orders in parallel.
            """
            
            def __init__(self, name: str = "parallel_order_item_extractor"):
                super().__init__(name)
                self.extractor = OrderItemExtractor()
                
            async def transform(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                """
                Extract order items from a list of orders in parallel.
                
                Args:
                    data: List of orders
                    
                Returns:
                    List of order items
                """
                if not data:
                    return []
                
                # Create tasks for parallel extraction
                tasks = []
                for order in data:
                    tasks.append(self.extractor.transform(order))
                
                # Use asyncio.gather to run tasks in parallel
                results = await asyncio.gather(*tasks)
                
                # Flatten the list of lists
                order_items = [item for sublist in results for item in sublist]
                
                # Record metrics
                self.record_metric("orders_processed", len(data))
                self.record_metric("order_items_extracted", len(order_items))
                
                return order_items
        
        # Add extraction stage
        pipeline.add_stage(ParallelOrderItemExtractor())
        
        # Add validation stage with batch processing
        validator = OrderItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_order_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)
        
        # Add transformation stage with batch processing
        transformer = OrderItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_order_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)
        
        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))
        
        return pipeline
    
    @staticmethod
    def create_parallel_processing_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        name: str = "parallel_order_item_processing_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for processing order items in parallel.
        
        This pipeline processes order items from the context in parallel
        for improved performance.
        
        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file (if None, no CSV is generated)
            name: Name of the pipeline
            
        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import CSVLoader
        
        # Create pipeline
        pipeline = Pipeline(name)
        
        # Add context extraction stage
        pipeline.add_stage(ContextExtractor("order_items", default=[]))
        
        # Add validation stage with batch processing
        validator = OrderItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_order_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)
        
        # Add transformation stage with batch processing
        transformer = OrderItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_order_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)
        
        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))
        
        return pipeline
    
    @staticmethod
    def create_parallel_validation_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        name: str = "parallel_order_item_validation_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for validating order items in parallel.
        
        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            name: Name of the pipeline
            
        Returns:
            Pipeline instance
        """
        # Create pipeline
        pipeline = Pipeline(name)
        
        # Add validation stage with batch processing
        validator = OrderItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_order_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)
        
        return pipeline
    
    @staticmethod
    def create_parallel_transformation_pipeline(
        max_concurrency: int = 5,
        batch_size: int = 100,
        name: str = "parallel_order_item_transformation_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for transforming order items in parallel.
        
        Args:
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            name: Name of the pipeline
            
        Returns:
            Pipeline instance
        """
        # Create pipeline
        pipeline = Pipeline(name)
        
        # Add validation stage with batch processing
        validator = OrderItemValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_order_item_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)
        
        # Add transformation stage with batch processing
        transformer = OrderItemTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_order_item_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)
        
        return pipeline


class ParallelOrderProcessor:
    """
    Factory for creating pipelines that process orders and order items in parallel.
    
    This class provides methods for creating pipelines that process orders
    and their items with parallel processing for improved performance.
    """
    
    @staticmethod
    def create_acquisition_pipeline(
        start_id: Optional[int] = None,
        end_id: Optional[int] = None,
        max_concurrency: int = 5,
        batch_size: int = 100,
        output_path: Optional[str] = None,
        items_output_path: Optional[str] = None,
        name: str = "parallel_order_acquisition_pipeline"
    ) -> Pipeline:
        """
        Create a pipeline for acquiring and processing orders and their items in parallel.
        
        Args:
            start_id: Starting order ID
            end_id: Ending order ID
            max_concurrency: Maximum number of items to process concurrently
            batch_size: Maximum number of items to process in a single batch
            output_path: Path to the output CSV file for orders
            items_output_path: Path to the output CSV file for order items
            name: Name of the pipeline
            
        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrdersDataAcquisitionStage, OrderValidator, OrderTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader
        
        # Create pipeline
        pipeline = Pipeline(name)
        
        # Add acquisition stage
        acquisition_stage = OrdersDataAcquisitionStage(start_id=start_id, end_id=end_id)
        pipeline.add_stage(acquisition_stage)
        
        # Add validation stage with batch processing
        validator = OrderValidator()
        batch_validator = BatchProcessor(
            validator,
            name="batch_order_validator",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_validator)
        
        # Add transformation stage with batch processing
        transformer = OrderTransformer()
        batch_transformer = BatchProcessor(
            transformer,
            name="batch_order_transformer",
            batch_size=batch_size,
            max_concurrency=max_concurrency
        )
        pipeline.add_stage(batch_transformer)
        
        # Add CSV loader if output path is provided
        if output_path:
            pipeline.add_stage(CSVLoader(output_path))
        
        # Create and add a parallel stage for processing order items if needed
        if items_output_path:
            # Create a parallel stage that will run after the main pipeline
            class OrderItemsProcessor(PipelineStage[List[Dict[str, Any]], List[Dict[str, Any]]]):
                """
                Pipeline stage that processes order items from the context.
                """
                
                def __init__(self, acquisition_stage: OrdersDataAcquisitionStage, output_path: str):
                    super().__init__("order_items_processor")
                    self.acquisition_stage = acquisition_stage
                    self.output_path = output_path
                    
                async def process_core(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                    """
                    Process order items from the context.
                    
                    Args:
                        data: List of processed orders (not used)
                        
                    Returns:
                        List of processed order items
                    """
                    # Get order items from context
                    order_items = self.acquisition_stage.get_context("order_items", [])
                    
                    if not order_items:
                        logger.warning("No order items found in context")
                        return []
                    
                    # Create a pipeline for processing order items
                    items_pipeline = ParallelOrderItemProcessor.create_parallel_processing_pipeline(
                        max_concurrency=max_concurrency,
                        batch_size=batch_size,
                        output_path=self.output_path,
                        name="order_items_processor_pipeline"
                    )
                    
                    # Set the context for the pipeline
                    for stage in items_pipeline.stages:
                        stage.set_context("order_items", order_items)
                    
                    # Run the pipeline
                    processed_items = await items_pipeline.run(None)
                    
                    return processed_items
            
            # Add the order items processor stage
            pipeline.add_stage(OrderItemsProcessor(acquisition_stage, items_output_path))
        
        return pipeline


# Example usage
async def process_orders_in_parallel(
    start_id: int,
    end_id: int,
    max_concurrency: int = 5,
    output_dir: str = "data_raw"
) -> None:
    """
    Process orders and their items in parallel.
    
    Args:
        start_id: Starting order ID
        end_id: Ending order ID
        max_concurrency: Maximum number of items to process concurrently
        output_dir: Directory for output files
    """
    import os
    from pathlib import Path
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Create output paths
    orders_path = os.path.join(output_dir, "orders", "orders.csv")
    items_path = os.path.join(output_dir, "order_items", "order_items.csv")
    
    # Ensure parent directories exist
    os.makedirs(os.path.dirname(orders_path), exist_ok=True)
    os.makedirs(os.path.dirname(items_path), exist_ok=True)
    
    # Create and run the pipeline
    pipeline = ParallelOrderProcessor.create_acquisition_pipeline(
        start_id=start_id,
        end_id=end_id,
        max_concurrency=max_concurrency,
        output_path=orders_path,
        items_output_path=items_path
    )
    
    logger.info(f"Processing orders {start_id} to {end_id} with max concurrency {max_concurrency}")
    await pipeline.run(None)
    logger.info("Processing completed")
    
    # Print metrics
    metrics = pipeline.get_metrics()
    logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")
    logger.info(f"Orders processed: {metrics['stage_metrics']['batch_order_transformer']['metrics']['total_items']}")
    
    # Get order items metrics if available
    if "order_items_processor" in metrics["stage_metrics"]:
        items_metrics = metrics["stage_metrics"]["order_items_processor"]["metrics"]
        if "pipeline_metrics" in items_metrics:
            items_pipeline_metrics = items_metrics["pipeline_metrics"]
            if "batch_order_item_transformer" in items_pipeline_metrics["stage_metrics"]:
                transformer_metrics = items_pipeline_metrics["stage_metrics"]["batch_order_item_transformer"]["metrics"]
                logger.info(f"Order items processed: {transformer_metrics['total_items']}")


if __name__ == "__main__":
    import asyncio
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process orders and their items in parallel")
    parser.add_argument("--start-id", type=int, help="Starting order ID", default=1)
    parser.add_argument("--end-id", type=int, help="Ending order ID", default=100)
    parser.add_argument("--max-concurrency", type=int, help="Maximum concurrency", default=5)
    parser.add_argument("--output-dir", type=str, help="Output directory", default="data_raw")
    
    args = parser.parse_args()
    
    # Run the processor
    asyncio.run(process_orders_in_parallel(
        start_id=args.start_id,
        end_id=args.end_id,
        max_concurrency=args.max_concurrency,
        output_dir=args.output_dir
    ))