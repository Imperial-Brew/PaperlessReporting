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


class PipelineConfigurationError(PipelineError):
    """Exception raised when pipeline configuration is invalid."""
    pass