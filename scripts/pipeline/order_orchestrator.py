"""
Factory classes for creating order processing pipelines.

This module provides factory classes for creating pipelines for processing
order and order item data from the Paperless Parts API.
"""

from typing import Any, Dict, List, Optional, Union

from scripts.pipeline.orchestrator import Pipeline, WrapInList
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class OrderPipeline:
    """
    Factory for creating order processing pipelines.

    This class provides methods for creating pipelines for processing
    order data with different configurations.
    """

    @staticmethod
    def create_validation_pipeline(name: str = "order_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating order data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderValidator

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderValidator())

        return pipeline

    @staticmethod
    def create_transformation_pipeline(name: str = "order_transformation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating and transforming order data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderValidator, OrderTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderValidator())
        pipeline.add_stage(OrderTransformer())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "order_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for validating, transforming, and exporting order data to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderValidator, OrderTransformer
        from scripts.pipeline.processors import CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderValidator())
        pipeline.add_stage(OrderTransformer())

        # Wrap the transformed order in a list for the CSV loader
        pipeline.add_stage(WrapInList())
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_acquisition_pipeline(output_path: str = None, name: str = "order_acquisition_pipeline") -> Pipeline:
        """
        Create a pipeline for acquiring, validating, transforming, and exporting order data.

        This pipeline performs a full pull of all orders or a specific range of orders.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrdersDataAcquisitionStage, OrderValidator, OrderTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(OrdersDataAcquisitionStage())
        pipeline.add_stage(BatchProcessor(OrderValidator()))
        pipeline.add_stage(BatchProcessor(OrderTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_order_items_pipeline(output_path: str = None, name: str = "order_items_pipeline") -> Pipeline:
        """
        Create a pipeline for extracting, validating, transforming, and exporting order items.

        This pipeline extracts order items from the context set by the OrdersDataAcquisitionStage.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderItemValidator, OrderItemTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader
        from scripts.pipeline.orchestrator import ContextExtractor

        pipeline = Pipeline(name)
        
        # Extract order items from context
        pipeline.add_stage(ContextExtractor("order_items"))
        
        # Validate and transform order items
        pipeline.add_stage(BatchProcessor(OrderItemValidator()))
        pipeline.add_stage(BatchProcessor(OrderItemTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline


class OrderItemPipeline:
    """
    Factory for creating order item processing pipelines.

    This class provides methods for creating pipelines for processing
    order item data with different configurations.
    """

    @staticmethod
    def create_validation_pipeline(name: str = "order_item_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating order item data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderItemValidator

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderItemValidator())

        return pipeline

    @staticmethod
    def create_transformation_pipeline(name: str = "order_item_transformation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating and transforming order item data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderItemValidator, OrderItemTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderItemValidator())
        pipeline.add_stage(OrderItemTransformer())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "order_item_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for validating, transforming, and exporting order item data to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderItemValidator, OrderItemTransformer
        from scripts.pipeline.processors import CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderItemValidator())
        pipeline.add_stage(OrderItemTransformer())

        # Wrap the transformed order item in a list for the CSV loader
        pipeline.add_stage(WrapInList())
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_extraction_pipeline(order_data: Dict[str, Any], output_path: str = None, name: str = "order_item_extraction_pipeline") -> Pipeline:
        """
        Create a pipeline for extracting, validating, transforming, and exporting order items from an order.

        Args:
            order_data: Order data containing order items
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.order_processors import OrderItemExtractor, OrderItemValidator, OrderItemTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(OrderItemExtractor())
        pipeline.add_stage(BatchProcessor(OrderItemValidator()))
        pipeline.add_stage(BatchProcessor(OrderItemTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline