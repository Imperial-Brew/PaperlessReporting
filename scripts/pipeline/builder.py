"""
PipelineBuilder: A builder pattern for creating pipelines.

This module provides a PipelineBuilder class that implements the builder pattern
for creating pipelines with a fluent interface. It simplifies the process of
creating pipelines by providing methods for adding different types of stages.
"""

from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Callable

from scripts.pipeline.base import (
    PipelineStage, DataAcquisitionStage, ValidationStage,
    TransformationStage, LoadingStage
)
from scripts.pipeline.orchestrator import Pipeline
from scripts.utils.logging_config import get_logger

# Type variables for generic stages
T = TypeVar('T')  # Input type
U = TypeVar('U')  # Output type
V = TypeVar('V')  # Intermediate type

# Get logger for this module
logger = get_logger(__name__)


class PipelineBuilder(Generic[T, U]):
    """
    Builder for creating pipelines with a fluent interface.

    This class implements the builder pattern for creating pipelines with
    a fluent interface. It provides methods for adding different types of
    stages and ensures type safety between stages.

    Example:
        ```python
        pipeline = (PipelineBuilder("account_pipeline")
                   .add_acquisition(AccountsDataAcquisitionStage())
                   .add_validation(AccountValidator())
                   .add_transformation(AccountTransformer())
                   .add_loading(CSVLoader("output.csv"))
                   .build())
        ```
    """

    def __init__(self, name: str):
        """
        Initialize the pipeline builder.

        Args:
            name: Name of the pipeline for identification and logging
        """
        self.name = name
        self.pipeline = Pipeline(name)
        self._current_type = None  # Track the current output type

    def add_stage(self, stage: PipelineStage) -> 'PipelineBuilder':
        """
        Add a generic stage to the pipeline.

        This is a low-level method that adds any type of stage to the pipeline.
        It's recommended to use the more specific methods like add_acquisition,
        add_validation, etc. for better type safety.

        Args:
            stage: Pipeline stage to add

        Returns:
            The builder instance for method chaining
        """
        self.pipeline.add_stage(stage)
        return self

    def add_acquisition(self, stage: DataAcquisitionStage[U]) -> 'PipelineBuilder[None, U]':
        """
        Add a data acquisition stage to the pipeline.

        This method adds a stage that acquires data from an external source.
        It should be the first stage in the pipeline.

        Args:
            stage: Data acquisition stage to add

        Returns:
            The builder instance for method chaining
        """
        self._current_type = U  # Update the current output type
        self.pipeline.add_stage(stage)
        return self

    def add_validation(self, stage: ValidationStage[T]) -> 'PipelineBuilder[T, T]':
        """
        Add a validation stage to the pipeline.

        This method adds a stage that validates data against rules.

        Args:
            stage: Validation stage to add

        Returns:
            The builder instance for method chaining
        """
        # No type change for validation stages (input type = output type)
        self.pipeline.add_stage(stage)
        return self

    def add_transformation(self, stage: TransformationStage[T, U]) -> 'PipelineBuilder[T, U]':
        """
        Add a transformation stage to the pipeline.

        This method adds a stage that transforms data from one format to another.

        Args:
            stage: Transformation stage to add

        Returns:
            The builder instance for method chaining
        """
        self._current_type = U  # Update the current output type
        self.pipeline.add_stage(stage)
        return self

    def add_loading(self, stage: LoadingStage[T]) -> 'PipelineBuilder[T, None]':
        """
        Add a loading stage to the pipeline.

        This method adds a stage that loads data into a destination.
        It's typically the last stage in the pipeline.

        Args:
            stage: Loading stage to add

        Returns:
            The builder instance for method chaining
        """
        self._current_type = None  # Loading stages have no output
        self.pipeline.add_stage(stage)
        return self

    def add_batch_processor(self, stage: PipelineStage[T, U]) -> 'PipelineBuilder[List[T], List[U]]':
        """
        Add a batch processor stage to the pipeline.

        This method adds a stage that processes a batch of items.
        It's typically used with the BatchProcessor class.

        Args:
            stage: Batch processor stage to add

        Returns:
            The builder instance for method chaining
        """
        from scripts.pipeline.processors import BatchProcessor
        self._current_type = U  # Update the current output type
        self.pipeline.add_stage(BatchProcessor(stage))
        return self

    def configure_timeout(self, stage_index: int, timeout: float) -> 'PipelineBuilder[T, U]':
        """
        Configure the timeout for a specific stage.

        Args:
            stage_index: Index of the stage to configure
            timeout: Timeout value in seconds

        Returns:
            The builder instance for method chaining
        """
        if 0 <= stage_index < len(self.pipeline.stages):
            self.pipeline.stages[stage_index].configure_timeout(timeout)
        else:
            logger.warning(f"Invalid stage index: {stage_index}")
        return self

    def configure_retry(self, stage_index: int, max_retries: int = 3,
                       retry_delay: float = 1.0, backoff_factor: float = 2.0,
                       jitter: float = 0.1) -> 'PipelineBuilder[T, U]':
        """
        Configure retry behavior for a specific stage.

        Args:
            stage_index: Index of the stage to configure
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Factor to increase delay for each retry
            jitter: Random jitter factor to add to delay

        Returns:
            The builder instance for method chaining
        """
        if 0 <= stage_index < len(self.pipeline.stages):
            self.pipeline.stages[stage_index].configure_retry(
                max_retries=max_retries,
                retry_delay=retry_delay,
                backoff_factor=backoff_factor,
                jitter=jitter
            )
        else:
            logger.warning(f"Invalid stage index: {stage_index}")
        return self

    def configure_circuit_breaker(self, stage_index: int, failure_threshold: int = 5,
                                 reset_timeout: float = 60.0) -> 'PipelineBuilder[T, U]':
        """
        Configure circuit breaker behavior for a specific stage.

        Args:
            stage_index: Index of the stage to configure
            failure_threshold: Number of failures before opening the circuit
            reset_timeout: Time in seconds before resetting the circuit

        Returns:
            The builder instance for method chaining
        """
        if 0 <= stage_index < len(self.pipeline.stages):
            self.pipeline.stages[stage_index].configure_circuit_breaker(
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout
            )
        else:
            logger.warning(f"Invalid stage index: {stage_index}")
        return self

    def build(self) -> Pipeline:
        """
        Build and return the pipeline.

        Returns:
            The configured pipeline instance
        """
        return self.pipeline