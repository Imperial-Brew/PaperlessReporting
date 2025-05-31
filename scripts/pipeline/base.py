"""
Base classes for the pipeline framework.

This module defines the abstract base classes for pipeline stages and the
interfaces they must implement.
"""

import abc
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union

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
        
    @abc.abstractmethod
    async def process(self, data: T) -> U:
        """
        Process the input data and return the output data.
        
        Args:
            data: Input data to process
            
        Returns:
            Processed output data
        """
        pass
    
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
    async def process(self, data: None = None) -> T:
        """
        Fetch data from an external source.
        
        Args:
            data: Not used in this stage
            
        Returns:
            Fetched data
        """
        pass


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
    
    async def process(self, data: T) -> T:
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
    
    async def process(self, data: T) -> U:
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
    
    async def process(self, data: T) -> None:
        """
        Load the input data into a destination.
        
        Args:
            data: Input data to load
        """
        await self.load(data)
        
        # Record metrics
        self.record_metric("loading_completed", True)
        
        return None