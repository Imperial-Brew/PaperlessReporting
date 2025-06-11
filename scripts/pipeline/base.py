import abc
import asyncio
import time
import random
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, Set, Callable

from scripts.pipeline.exceptions import PipelineError
from scripts.utils.logging_config import get_logger, LogContext

# Get logger for this module
logger = get_logger(__name__)

# Type variable for input data
T = TypeVar('T')
# Type variable for output data
U = TypeVar('U')

class PipelineStage(Generic[T, U], abc.ABC):
    """
    Abstract base class for a pipeline stage.

    A pipeline stage takes input data of type T, processes it,
    and produces output data of type U.
    """

    def __init__(self, name: str):
        """
        Initialize the pipeline stage.

        Args:
            name: Name of the stage for identification and logging
        """
        self.name = name
        self.metrics = {}
        self._context = {}
        self._dependencies = {}
        self._required_dependencies = set()

        # Circuit breaker state
        self._circuit_state = "closed"  # "closed", "open", "half-open"
        self._failure_count = 0
        self._last_failure_time = 0
        self._circuit_reset_timeout = 60  # seconds
        self._failure_threshold = 5

        # Retry configuration
        self._max_retries = 3
        self._retry_delay = 1.0  # seconds
        self._retry_backoff_factor = 2.0
        self._retry_jitter = 0.1

        # Timeout configuration
        self._timeout = 30.0  # seconds

        # Batch processing configuration
        self._batch_size = 100
        self._parallel_workers = 5

    def set_context(self, key: str, value: Any) -> None:
        """
        Set a value in the context.

        Args:
            key: Context key
            value: Context value
        """
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context.

        Args:
            key: Context key
            default: Default value if key doesn't exist

        Returns:
            Context value or default
        """
        return self._context.get(key, default)

    def update_context(self, context: Dict[str, Any]) -> None:
        """
        Update the context with values from another context.

        Args:
            context: Context dictionary to update from
        """
        self._context.update(context)

    def get_full_context(self) -> Dict[str, Any]:
        """
        Get the full context dictionary.

        Returns:
            Context dictionary
        """
        return self._context.copy()

    def register_dependency(self, name: str, dependency: Any, required: bool = False) -> None:
        """
        Register a dependency for this stage.

        Args:
            name: Name of the dependency
            dependency: The dependency object
            required: Whether this dependency is required
        """
        self._dependencies[name] = dependency
        if required:
            self._required_dependencies.add(name)

    def get_dependency(self, name: str) -> Any:
        """
        Get a registered dependency.

        Args:
            name: Name of the dependency

        Returns:
            The dependency object

        Raises:
            DependencyError: If the dependency is not registered
        """
        if name not in self._dependencies:
            from scripts.pipeline.exceptions import DependencyError
            raise DependencyError(f"Dependency '{name}' not registered", dependency_name=name)
        return self._dependencies[name]

    def configure_retry(self, max_retries: int = 3, retry_delay: float = 1.0, 
                        backoff_factor: float = 2.0, jitter: float = 0.1) -> None:
        """
        Configure retry behavior.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (in seconds)
            backoff_factor: Factor to increase delay with each retry
            jitter: Random factor to add to delay (0-1)
        """
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._retry_backoff_factor = backoff_factor
        self._retry_jitter = jitter

    def configure_circuit_breaker(self, failure_threshold: int = 5, 
                                 reset_timeout: float = 60.0) -> None:
        """
        Configure circuit breaker behavior.

        Args:
            failure_threshold: Number of failures before opening circuit
            reset_timeout: Time before attempting to close circuit (in seconds)
        """
        self._failure_threshold = failure_threshold
        self._circuit_reset_timeout = reset_timeout

    def configure_timeout(self, timeout: float = 30.0) -> None:
        """
        Configure operation timeout.

        Args:
            timeout: Timeout in seconds
        """
        self._timeout = timeout

    def configure_batch_processing(self, batch_size: int = 100, 
                                  parallel_workers: int = 5) -> None:
        """
        Configure batch processing behavior.

        Args:
            batch_size: Size of batches for processing
            parallel_workers: Number of parallel workers
        """
        self._batch_size = batch_size
        self._parallel_workers = parallel_workers

    async def pre_process(self, data: T) -> T:
        """
        Pre-process the input data before main processing.

        This hook can be overridden by subclasses to implement
        custom pre-processing logic.

        Args:
            data: Input data to pre-process

        Returns:
            Pre-processed data
        """
        return data

    async def post_process(self, data: U) -> U:
        """
        Post-process the output data after main processing.

        This hook can be overridden by subclasses to implement
        custom post-processing logic.

        Args:
            data: Output data to post-process

        Returns:
            Post-processed data
        """
        return data

    @abc.abstractmethod
    async def process_core(self, data: T) -> U:
        """
        Core processing logic for the stage.

        This method must be implemented by subclasses to define
        the main processing logic.

        Args:
            data: Input data to process

        Returns:
            Processed output data
        """
        pass

    async def process(self, data: T) -> U:
        """
        Process the input data and return the output data.

        This method implements the full processing flow including
        - Pre-processing hook
        - Circuit breaker check
        - Retry logic
        - Timeout handling
        - Dependency validation
        - Core processing
        - Post-processing hook
        - Metrics recording

        Args:
            data: Input data to process

        Returns:
            Processed output data

        Raises:
            Various exceptions depending on what goes wrong
        """
        # Check circuit breaker
        if self._circuit_state == "open":
            # Check if it's time to try again
            if time.time() - self._last_failure_time > self._circuit_reset_timeout:
                logger.info(f"Circuit half-open for stage {self.name}, attempting reset")
                self._circuit_state = "half-open"
            else:
                from scripts.pipeline.exceptions import CircuitBreakerError
                reset_after = self._circuit_reset_timeout - (time.time() - self._last_failure_time)
                raise CircuitBreakerError(
                    f"Circuit breaker open for stage {self.name}", 
                    reset_after=reset_after
                )

        # Check required dependencies
        for dep_name in self._required_dependencies:
            if dep_name not in self._dependencies:
                from scripts.pipeline.exceptions import DependencyError
                raise DependencyError(
                    f"Required dependency '{dep_name}' not provided for stage {self.name}",
                    dependency_name=dep_name
                )

        # Apply pre-processing hook
        try:
            data = await self.pre_process(data)
        except Exception as e:
            logger.error(f"Pre-processing failed in stage {self.name}: {str(e)}")
            self._record_failure()
            raise

        # Process with retry logic
        retry_count = 0
        last_exception = None

        while retry_count <= self._max_retries:
            try:
                # Apply timeout
                try:
                    # Use asyncio.wait_for to implement timeout
                    result = await asyncio.wait_for(
                        self.process_core(data),
                        timeout=self._timeout
                    )

                    # If we get here, processing succeeded
                    if self._circuit_state == "half-open":
                        logger.info(f"Circuit closed for stage {self.name}, reset successful")
                        self._circuit_state = "closed"
                        self._failure_count = 0

                    # Apply post-processing hook
                    result = await self.post_process(result)

                    # Record success metric
                    self.record_metric("success", True)

                    return result

                except asyncio.TimeoutError:
                    from scripts.pipeline.exceptions import TimeoutError
                    raise TimeoutError(
                        f"Operation timed out in stage {self.name}",
                        timeout=self._timeout
                    )

            except Exception as e:
                last_exception = e

                # Check if this is a retryable error
                from scripts.pipeline.exceptions import RetryableError
                is_retryable = isinstance(e, RetryableError) or not isinstance(e, PipelineError)

                if is_retryable and retry_count < self._max_retries:
                    retry_count += 1

                    # Calculate delay with exponential backoff and jitter
                    delay = self._retry_delay * (self._retry_backoff_factor ** (retry_count - 1))
                    jitter = random.uniform(-self._retry_jitter, self._retry_jitter) * delay
                    delay = max(0, delay + jitter)

                    # If it's a RetryableError with a retry_after hint, use that instead
                    if isinstance(e, RetryableError) and e.retry_after is not None:
                        delay = e.retry_after

                    logger.warning(
                        f"Retry {retry_count}/{self._max_retries} for stage {self.name} "
                        f"after {delay:.2f}s: {str(e)}"
                    )

                    # Record retry metric
                    self.record_metric("retry_count", retry_count)
                    self.record_metric("last_retry_delay", delay)

                    # Wait before retrying
                    await asyncio.sleep(delay)
                    continue
                else:
                    # Not retryable or max retries exceeded
                    self._record_failure()

                    # Record failure metrics
                    self.record_metric("success", False)
                    self.record_metric("error", str(e))
                    self.record_metric("error_type", type(e).__name__)

                    # Re-raise the exception
                    raise

        # This should never be reached due to the continue/raise in the loop,
        # but just in case, re-raise the last exception
        if last_exception:
            raise last_exception

        # This should never be reached
        raise RuntimeError("Unexpected end of process method")

    def _record_failure(self) -> None:
        """Record a failure and update circuit breaker state."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        # Check if we need to open the circuit
        if self._circuit_state == "closed" and self._failure_count >= self._failure_threshold:
            logger.warning(f"Circuit opened for stage {self.name} after {self._failure_count} failures")
            self._circuit_state = "open"

        # If we're in half-open state and get a failure, go back to open
        elif self._circuit_state == "half-open":
            logger.warning(f"Circuit re-opened for stage {self.name} after failed reset attempt")
            self._circuit_state = "open"

    async def process_batch(self, items: List[T]) -> List[U]:
        """
        Process a batch of items.

        Args:
            items: List of input items to process

        Returns:
            List of processed output items
        """
        # Split into sub-batches based on batch size
        results = []
        for i in range(0, len(items), self._batch_size):
            batch = items[i:i + self._batch_size]

            # Process sub-batch with parallel workers
            tasks = []
            for item in batch:
                tasks.append(self.process(item))

            # Use asyncio.gather to run tasks in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error processing item {i} in batch: {str(result)}")
                    # You could re-raise, skip, or handle differently based on your needs
                    # For now, we'll just skip this item
                    continue
                results.append(result)

        return results

    def record_metric(self, name: str, value: Any) -> None:
        """
        Record a metric for monitoring.

        Args:
            name: Name of the metric
            value: Value of the metric
        """
        self.metrics[name] = value

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get all recorded metrics.

        Returns:
            Dictionary of metrics
        """
        return self.metrics


class DataAcquisitionStage(PipelineStage[None, T], abc.ABC):
    """
    Abstract base class for a data acquisition stage.

    This stage fetches data from an external source and returns it.
    It takes no input (None) and produces output data of type T.
    """

    @abc.abstractmethod
    async def acquire(self) -> T:
        """
        Fetch data from an external source.

        Returns:
            Fetched data
        """
        pass

    async def process_core(self, data: None = None) -> T:
        """
        Fetch data from an external source.

        Args:
            data: Not used in this stage

        Returns:
            Fetched data
        """
        result = await self.acquire()

        # Record metrics
        self.record_metric("acquisition_completed", True)

        return result


class ValidationStage(PipelineStage[T, T], abc.ABC):
    """
    Abstract base class for a validation stage.

    This stage validates input data and returns it if valid.
    It takes input data of type T and produces output data of the same type.
    """

    @abc.abstractmethod
    async def validate(self, data: T) -> List[str]:
        """
        Validate the input data.

        Args:
            data: Input data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        pass

    async def process_core(self, data: T) -> T:
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


class TransformationStage(PipelineStage[T, U], abc.ABC):
    """
    Abstract base class for a transformation stage.

    This stage transforms input data of type T into output data of type U.
    """

    @abc.abstractmethod
    async def transform(self, data: T) -> U:
        """
        Transform the input data.

        Args:
            data: Input data to transform

        Returns:
            Transformed output data
        """
        pass

    async def process_core(self, data: T) -> U:
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


class LoadingStage(PipelineStage[T, None], abc.ABC):
    """
    Abstract base class for a loading stage.

    This stage loads data into a destination (e.g., file, database).
    It takes input data of type T and produces no output (None).
    """

    @abc.abstractmethod
    async def load(self, data: T) -> None:
        """
        Load the input data into a destination.

        Args:
            data: Input data to load
        """
        pass

    async def process_core(self, data: T) -> None:
        """
        Load the input data into a destination.

        Args:
            data: Input data to load
        """
        await self.load(data)

        # Record metrics
        self.record_metric("loading_completed", True)

        return None
