"""
Centralized logging configuration for the PaperlessReporting application.

This module provides functions to set up consistent logging across the application,
including structured logging with JSON format, correlation IDs for request tracking,
and configurable log levels.
"""

import logging
import os
import json
import uuid
import sys
from typing import Optional, Dict, Any
from functools import wraps
from scripts.utils.config_loader import get

# Default log format for non-JSON logging
DEFAULT_LOG_FORMAT = '%(asctime)s - %(levelname)s - [%(correlation_id)s] - %(name)s - %(message)s'

# Default log level
DEFAULT_LOG_LEVEL = 'INFO'

# Global correlation ID for the current context
_correlation_id = None


class CorrelationFilter(logging.Filter):
    """
    Filter that adds correlation_id to log records.
    """
    def filter(self, record):
        record.correlation_id = get_correlation_id() or '-'
        return True


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings for log records.
    """
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'correlation_id': getattr(record, 'correlation_id', '-'),
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
                          'correlation_id'):
                log_data[key] = value

        return json.dumps(log_data)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID.
    
    Returns:
        The current correlation ID or None if not set.
    """
    return _correlation_id


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set the correlation ID for the current context.
    
    Args:
        correlation_id: The correlation ID to set. If None, a new UUID will be generated.
        
    Returns:
        The correlation ID that was set.
    """
    global _correlation_id
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    _correlation_id = correlation_id
    return _correlation_id


def with_correlation_id(func):
    """
    Decorator that sets a correlation ID for the duration of the function call.
    
    Args:
        func: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Generate a new correlation ID if one doesn't exist
        old_correlation_id = get_correlation_id()
        if not old_correlation_id:
            set_correlation_id()
        
        try:
            return func(*args, **kwargs)
        finally:
            # Restore the previous correlation ID
            if old_correlation_id:
                set_correlation_id(old_correlation_id)
            else:
                set_correlation_id(None)
                
    return wrapper


def configure_logging(
    level: Optional[str] = None,
    use_json: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting for logs
        log_file: Path to log file (if None, logs to console only)
    """
    # Determine log level from environment, config, or default
    if level is None:
        level = os.getenv('LOG_LEVEL', get('logging', {}).get('level', DEFAULT_LOG_LEVEL))
    
    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")
    
    # Create handlers
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        # Ensure directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)
    
    # Configure formatters and filters
    correlation_filter = CorrelationFilter()
    
    if use_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add and configure handlers
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(correlation_filter)
        root_logger.addHandler(handler)
    
    # Log configuration info
    logging.info(f"Logging configured: level={level}, json={use_json}, file={log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    
    This is a wrapper around logging.getLogger() that ensures
    the logger has the correlation ID filter.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    
    # Add correlation filter if not already present
    has_correlation_filter = any(
        isinstance(f, CorrelationFilter) for f in logger.filters
    )
    
    if not has_correlation_filter:
        logger.addFilter(CorrelationFilter())
        
    return logger


class LogContext:
    """
    Context manager for adding context to log records.
    
    Example:
        with LogContext(request_id='123', user='john'):
            logger.info('Processing request')
    """
    def __init__(self, **kwargs):
        self.old_context = {}
        self.context = kwargs
        
    def __enter__(self):
        # Store old context and set new context
        for key, value in self.context.items():
            if hasattr(logging, key):
                self.old_context[key] = getattr(logging, key)
            setattr(logging, key, value)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        for key, value in self.old_context.items():
            setattr(logging, key, value)
        
        # Remove new context keys that didn't exist before
        for key in self.context:
            if key not in self.old_context:
                delattr(logging, key)