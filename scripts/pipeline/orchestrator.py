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

    async def process_core(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform the input data and return the result.

        Args:
            data: Input data to transform

        Returns:
            Transformed output data
        """
        result = await self.transform(data)

        # Record metrics
        self.record_metric("transformation_completed", True)

        return result


class ContextExtractor(TransformationStage[Any, Any]):
    """
    Transformation stage that extracts data from the context.

    This stage is used to extract data that was stored in the context
    by previous stages, allowing pipelines to share data.

    Examples:
        # Extract order items from context with no default
        pipeline.add_stage(ContextExtractor("order_items"))

        # Extract order items with an empty list as default
        pipeline.add_stage(ContextExtractor("order_items", default=[]))

        # Extract a specific value with custom error handling
        pipeline.add_stage(ContextExtractor(
            "customer_id", 
            default=None,
            raise_if_missing=False
        ))
    """
    def __init__(self, context_key: str, default: Any = None, 
                 raise_if_missing: bool = True, name: str = None):
        """
        Initialize the context extractor.

        Args:
            context_key: Key to extract from the context
            default: Default value to return if the key doesn't exist
            raise_if_missing: Whether to raise an error if the key doesn't exist
            name: Name of the stage (defaults to "context_extractor_{context_key}")
        """
        if name is None:
            name = f"context_extractor_{context_key}"
        super().__init__(name)
        self.context_key = context_key
        self.default = default
        self.raise_if_missing = raise_if_missing

    async def transform(self, _: Any) -> Any:
        """
        Extract data from the context.

        Args:
            _: Input data (ignored)

        Returns:
            Data extracted from the context or the default value

        Raises:
            KeyError: If the context key does not exist and raise_if_missing is True
        """
        # Check if we should use the global context registry
        from scripts.pipeline.context_registry import get_global_context

        # First try to get from local context
        if hasattr(self, "_context") and self.context_key in self._context:
            data = self.get_context(self.context_key)
            self.record_metric("context_source", "local")
        else:
            # Try to get from global context registry using pipeline name as namespace
            try:
                pipeline_name = self.get_context("pipeline_name", "default")
                data = get_global_context(pipeline_name, self.context_key, None)
                if data is not None:  # Found in global context
                    self.record_metric("context_source", "global")
                else:
                    # Not found in either local or global context
                    if self.raise_if_missing and self.default is None:
                        pipeline_info = f" in pipeline '{pipeline_name}'" if pipeline_name else ""
                        raise KeyError(
                            f"Context key '{self.context_key}' not found in local context or "
                            f"global registry{pipeline_info}. Available keys in local context: "
                            f"{list(self._context.keys() if hasattr(self, '_context') else [])}"
                        )
                    self.record_metric("context_source", "default")
                    data = self.default
            except ImportError:
                # Global context registry not available
                if self.raise_if_missing and self.default is None and (not hasattr(self, "_context") or self.context_key not in self._context):
                    raise KeyError(
                        f"Context key '{self.context_key}' not found. Available keys: "
                        f"{list(self._context.keys() if hasattr(self, '_context') else [])}"
                    )
                data = self.get_context(self.context_key, self.default)
                self.record_metric("context_source", "default")

        self.record_metric("context_key", self.context_key)
        self.record_metric("data_extracted", True)
        self.record_metric("using_default", data is self.default)

        return data


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

    async def process_core(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate the input data and return it if valid.

        Args:
            data: Input data to validate

        Returns:
            The input data if valid

        Raises:
            ValidationError: If the data is invalid
        """
        errors = await self.validate(data)
        if errors:
            from scripts.pipeline.exceptions import ValidationError
            raise ValidationError(f"Validation failed: {', '.join(errors)}", errors=errors, data=data)

        # Record metrics
        self.record_metric("validation_passed", True)

        return data


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

            # Initialize shared context
            shared_context = {"pipeline_name": self.name}

            # Process data through each stage
            current_data = data

            for i, stage in enumerate(self.stages):
                stage_name = stage.name
                stage_type = stage.__class__.__name__

                # Set pipeline name in stage context
                stage.set_context("pipeline_name", self.name)

                # Update stage context with shared context
                stage.update_context(shared_context)

                # Add stage context to logs
                with LogContext(stage=stage_name, stage_type=stage_type, stage_index=i):
                    logger.info(f"Running stage: {stage_name} ({stage_type})")

                    try:
                        # Process data through the stage
                        stage_start_time = time.time()
                        current_data = await stage.process(current_data)
                        stage_end_time = time.time()

                        # Update shared context with stage context
                        shared_context.update(stage.get_full_context())

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
        pipeline.add_stage(CSVLoader(output_path, upload_to_s3=True))

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
        pipeline.add_stage(CSVLoader(output_path, upload_to_s3=True))

        return pipeline
