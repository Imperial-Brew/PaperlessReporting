"""
Pipeline orchestrator for the pipeline framework.

This module provides the orchestrator that connects pipeline stages
and executes them in sequence.
"""

import asyncio
import time
import logging
from abc import ABC
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Callable

from scripts.pipeline.base import PipelineStage, TransformationStage, ValidationStage
from scripts.pipeline.exceptions import PipelineError, PipelineConfigurationError
from scripts.utils.logging_config import get_logger, LogContext

# Get logger for this module
logger = get_logger(__name__)

# Type variable for pipeline input
T = TypeVar('T')
# Type variable for pipeline output
U = TypeVar('U')


class WrapInList(TransformationStage[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Transformation stage that wraps a dictionary in a list.

    This is used to convert a single quote dictionary into a list
    for the CSV loader which expects a list of dictionaries.
    """
    def __init__(self):
        super().__init__("wrap_in_list")

    async def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [data]


class ValidateQuoteItems(ValidationStage[List[Dict[str, Any]]]):
    """
    Validation stage that validates each quote item in a list.
    """
    def __init__(self):
        super().__init__("validate_quote_items")
        from scripts.pipeline.validators import QuoteItemValidator
        self.validator = QuoteItemValidator()

    async def validate(self, data: List[Dict[str, Any]]) -> List[str]:
        valid_items = []
        invalid_items = []
        errors = []

        for item in data:
            try:
                item_errors = await self.validator.validate(item)
                if not item_errors:
                    valid_items.append(item)
                else:
                    invalid_items.append((item, item_errors))
                    errors.extend(item_errors)
            except Exception as e:
                invalid_items.append((item, [str(e)]))
                errors.append(str(e))

        # Record metrics
        self.record_metric("total_items", len(data))
        self.record_metric("valid_items", len(valid_items))
        self.record_metric("invalid_items", len(invalid_items))

        if invalid_items:
            logger.warning(f"Found {len(invalid_items)} invalid quote items")
            for item, item_errors in invalid_items:
                logger.warning(f"Invalid quote item: {item.get('item_id')} - {', '.join(item_errors)}")

        return errors


class Pipeline(Generic[T, U]):
    """
    Pipeline orchestrator that connects stages and executes them in sequence.

    The pipeline takes input data of type T, processes it through a series
    of stages, and produces output data of type U.
    """

    def __init__(self, name: str):
        """
        Initialize the pipeline.

        Args:
            name: Name of the pipeline for identification and logging
        """
        self.name = name
        self.stages: List[PipelineStage] = []
        self.metrics: Dict[str, Any] = {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def add_stage(self, stage: PipelineStage) -> 'Pipeline':
        """
        Add a stage to the pipeline.

        Args:
            stage: Pipeline stage to add

        Returns:
            The pipeline instance for method chaining
        """
        self.stages.append(stage)
        return self

    async def run(self, data: T) -> U:
        """
        Run the pipeline with the given input data.

        Args:
            data: Input data to process

        Returns:
            Output data from the pipeline

        Raises:
            PipelineConfigurationError: If the pipeline has no stages
            PipelineError: If an error occurs during pipeline execution
        """
        if not self.stages:
            raise PipelineConfigurationError("Pipeline has no stages")

        # Record start time
        self.start_time = time.time()

        # Add pipeline context to logs
        with LogContext(pipeline=self.name):
            logger.info(f"Starting pipeline: {self.name}")

            # Initialize metrics
            self.metrics = {
                "pipeline_name": self.name,
                "start_time": self.start_time,
                "stage_metrics": {},
                "errors": [],
            }

            # Process data through each stage
            current_data = data

            for i, stage in enumerate(self.stages):
                stage_name = stage.name
                stage_type = stage.__class__.__name__

                # Add stage context to logs
                with LogContext(stage=stage_name, stage_type=stage_type, stage_index=i):
                    logger.info(f"Running stage: {stage_name} ({stage_type})")

                    try:
                        # Process data through the stage
                        stage_start_time = time.time()
                        current_data = await stage.process(current_data)
                        stage_end_time = time.time()

                        # Record stage metrics
                        stage_duration = stage_end_time - stage_start_time
                        stage_metrics = {
                            "name": stage_name,
                            "type": stage_type,
                            "duration": stage_duration,
                            "success": True,
                            "metrics": stage.get_metrics(),
                        }

                        self.metrics["stage_metrics"][stage_name] = stage_metrics

                        logger.info(f"Stage completed: {stage_name} in {stage_duration:.2f}s")
                    except Exception as e:
                        # Record error
                        error_info = {
                            "stage_name": stage_name,
                            "stage_type": stage_type,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        }

                        if isinstance(e, PipelineError):
                            error_info["details"] = e.details

                        self.metrics["errors"].append(error_info)

                        # Record stage metrics
                        stage_end_time = time.time()
                        stage_duration = stage_end_time - stage_start_time
                        stage_metrics = {
                            "name": stage_name,
                            "type": stage_type,
                            "duration": stage_duration,
                            "success": False,
                            "error": str(e),
                            "metrics": stage.get_metrics(),
                        }

                        self.metrics["stage_metrics"][stage_name] = stage_metrics

                        logger.error(f"Stage failed: {stage_name} - {str(e)}")

                        # Re-raise the exception
                        raise PipelineError(
                            f"Pipeline {self.name} failed at stage {stage_name}: {str(e)}",
                            details={
                                "pipeline_name": self.name,
                                "stage_name": stage_name,
                                "stage_type": stage_type,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                            }
                        ) from e

            # Record end time
            self.end_time = time.time()
            self.metrics["end_time"] = self.end_time
            self.metrics["duration"] = self.end_time - self.start_time

            logger.info(f"Pipeline completed: {self.name} in {self.metrics['duration']:.2f}s")

            return current_data

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all recorded metrics.

        Returns:
            Dictionary of metrics
        """
        return self.metrics


class QuotePipeline:
    """
    Factory for creating quote processing pipelines.

    This class provides methods for creating pipelines for processing
    quote data with different configurations.
    """

    @staticmethod
    def create_validation_pipeline(name: str = "quote_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating quote data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.validators import QuoteValidator

        pipeline = Pipeline(name)
        pipeline.add_stage(QuoteValidator())

        return pipeline

    @staticmethod
    def create_transformation_pipeline(name: str = "quote_transformation_pipeline") -> Pipeline:
        """
        Create a pipeline for transforming quote data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.validators import QuoteValidator
        from scripts.pipeline.processors import QuoteTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(QuoteValidator())
        pipeline.add_stage(QuoteTransformer())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "quote_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for validating, transforming, and exporting quote data to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.validators import QuoteValidator
        from scripts.pipeline.processors import QuoteTransformer, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(QuoteValidator())
        pipeline.add_stage(QuoteTransformer())

        # Wrap the transformed quote in a list for the CSV loader
        pipeline.add_stage(WrapInList())
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline


class QuoteItemPipeline:
    """
    Factory for creating quote item processing pipelines.

    This class provides methods for creating pipelines for processing
    quote item data with different configurations.
    """

    @staticmethod
    def create_extraction_pipeline(name: str = "quote_item_extraction_pipeline") -> Pipeline:
        """
        Create a pipeline for extracting quote items from a quote.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import QuoteItemTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(QuoteItemTransformer())

        return pipeline

    @staticmethod
    def create_validation_pipeline(name: str = "quote_item_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for extracting and validating quote items.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import QuoteItemTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(QuoteItemTransformer())
        pipeline.add_stage(ValidateQuoteItems())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "quote_item_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for extracting, validating, and exporting quote items to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.processors import CSVLoader

        pipeline = QuoteItemPipeline.create_validation_pipeline(name)
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline
