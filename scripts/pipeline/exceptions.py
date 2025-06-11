"""
Custom exceptions for the pipeline framework.

This module defines custom exceptions that can be raised by pipeline stages
during processing.
"""

from typing import Any, Dict, List, Optional


class PipelineError(Exception):
    """Base exception for all pipeline-related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            details: Additional error details for logging and debugging
        """
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(PipelineError):
    """Exception raised when data validation fails."""
    
    def __init__(self, message: str, errors: List[str], data: Any = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the validation error.
        
        Args:
            message: Human-readable error message
            errors: List of validation error messages
            data: The data that failed validation
            details: Additional error details
        """
        self.errors = errors
        self.invalid_data = data
        
        # Add errors and data to details
        details = details or {}
        details['validation_errors'] = errors
        if data is not None:
            details['invalid_data'] = data
            
        super().__init__(message, details)


class TransformationError(PipelineError):
    """Exception raised when data transformation fails."""
    
    def __init__(self, message: str, data: Any = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the transformation error.
        
        Args:
            message: Human-readable error message
            data: The data that failed transformation
            details: Additional error details
        """
        self.failed_data = data
        
        # Add data to details
        details = details or {}
        if data is not None:
            details['failed_data'] = data
            
        super().__init__(message, details)


class LoadingError(PipelineError):
    """Exception raised when data loading fails."""
    
    def __init__(self, message: str, data: Any = None, destination: str = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the loading error.
        
        Args:
            message: Human-readable error message
            data: The data that failed to load
            destination: The destination where loading failed
            details: Additional error details
        """
        self.failed_data = data
        self.destination = destination
        
        # Add data and destination to details
        details = details or {}
        if data is not None:
            details['failed_data'] = data
        if destination is not None:
            details['destination'] = destination
            
        super().__init__(message, details)


class DataAcquisitionError(PipelineError):
    """Exception raised when data acquisition fails."""
    
    def __init__(self, message: str, source: str = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the data acquisition error.
        
        Args:
            message: Human-readable error message
            source: The source from which acquisition failed
            details: Additional error details
        """
        self.source = source
        
        # Add source to details
        details = details or {}
        if source is not None:
            details['source'] = source
            
        super().__init__(message, details)



class RetryableError(PipelineError):
    """Exception indicating that an operation can be retried."""

    def __init__(self, message: str, retry_after: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the retryable error.

        Args:
            message: Human-readable error message
            retry_after: Suggested time to wait before retrying (in seconds)
            details: Additional error details
        """
        self.retry_after = retry_after

        # Add retry_after to details
        details = details or {}
        if retry_after is not None:
            details['retry_after'] = retry_after

        super().__init__(message, details)


class CircuitBreakerError(PipelineError):
    """Exception indicating that the circuit breaker is open."""

    def __init__(self, message: str, reset_after: Optional[float] = None, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the circuit breaker error.

        Args:
            message: Human-readable error message
            reset_after: Time until the circuit breaker resets (in seconds)
            details: Additional error details
        """
        self.reset_after = reset_after

        # Add reset_after to details
        details = details or {}
        if reset_after is not None:
            details['reset_after'] = reset_after

        super().__init__(message, details)


class DependencyError(PipelineError):
    """Exception indicating that a required dependency is missing."""

    def __init__(self, message: str, dependency_name: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the dependency error.

        Args:
            message: Human-readable error message
            dependency_name: Name of the missing dependency
            details: Additional error details
        """
        self.dependency_name = dependency_name

        # Add dependency_name to details
        details = details or {}
        details['dependency_name'] = dependency_name

        super().__init__(message, details)


class TimeoutError(PipelineError):
    """Exception indicating that an operation timed out."""

    def __init__(self, message: str, timeout: float, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the timeout error.

        Args:
            message: Human-readable error message
            timeout: The timeout value that was exceeded (in seconds)
            details: Additional error details
        """
        self.timeout = timeout

        # Add timeout to details
        details = details or {}
        details['timeout'] = timeout

        super().__init__(message, details)



class PipelineConfigurationError(PipelineError):
    """Exception raised when pipeline configuration is invalid."""
    pass