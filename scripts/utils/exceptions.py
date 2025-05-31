"""
Custom exceptions for the PaperlessReporting application.

This module defines a hierarchy of custom exceptions that can be used
throughout the application for more granular error handling.
"""

from typing import Optional, Dict, Any


class PaperlessError(Exception):
    """Base exception for all application-specific errors."""
    
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


class ConfigurationError(PaperlessError):
    """Error related to application configuration."""
    pass


class APIError(PaperlessError):
    """Error related to API communication."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None, 
        response_body: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the API error.
        
        Args:
            message: Human-readable error message
            status_code: HTTP status code if applicable
            response_body: Response body if available
            details: Additional error details
        """
        self.status_code = status_code
        self.response_body = response_body
        
        # Add status_code and response_body to details
        details = details or {}
        if status_code is not None:
            details['status_code'] = status_code
        if response_body is not None:
            details['response_body'] = response_body
            
        super().__init__(message, details)


class RateLimitError(APIError):
    """Error when API rate limit is exceeded."""
    pass


class AuthenticationError(APIError):
    """Error related to API authentication."""
    pass


class WebhookError(PaperlessError):
    """Error related to webhook processing."""
    pass


class WebhookAuthenticationError(WebhookError):
    """Error when webhook authentication fails."""
    pass


class WebhookValidationError(WebhookError):
    """Error when webhook payload validation fails."""
    pass


class DataProcessingError(PaperlessError):
    """Error related to data processing."""
    pass


class S3Error(PaperlessError):
    """Error related to S3 operations."""
    pass


class S3UploadError(S3Error):
    """Error when uploading to S3 fails."""
    pass


class S3DownloadError(S3Error):
    """Error when downloading from S3 fails."""
    pass


class S3ConfigurationError(S3Error):
    """Error related to S3 configuration."""
    pass