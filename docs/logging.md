# Logging and Error Handling

## Overview

This document describes the logging and error handling system in the PaperlessReporting application.

## Centralized Logging Configuration

The centralized logging configuration is implemented in `scripts/utils/logging_config.py`. It provides:

- A consistent logging format across the application
- Support for different log levels based on environment variables or config
- Support for correlation IDs to track requests
- JSON formatting for structured logging
- A context manager for adding context to log records
- A decorator for adding correlation IDs to functions

### Usage

To configure logging in your application:

```python
from scripts.utils.logging_config import configure_logging, get_logger

# Configure logging
configure_logging(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    use_json=os.getenv('LOG_FORMAT', '').lower() == 'json',
    log_file=os.getenv('LOG_FILE')
)

# Get a logger for your module
logger = get_logger(__name__)

# Use the logger
logger.info("This is an info message")
logger.error("This is an error message")
```

### Correlation IDs

Correlation IDs are used to track requests across components. They are automatically added to log records when using the `get_logger` function.

To set a correlation ID for a function:

```python
from scripts.utils.logging_config import with_correlation_id

@with_correlation_id
def my_function():
    # This function will have a correlation ID set
    logger.info("This log message will include the correlation ID")
```

### Context Information

Context information can be added to log records using the `LogContext` context manager:

```python
from scripts.utils.logging_config import LogContext

# Add context information to logs
with LogContext(operation="process_data", user_id=123):
    logger.info("Processing data")  # This log message will include the context information
```

## Custom Exception Hierarchy

The custom exception hierarchy is implemented in `scripts/utils/exceptions.py`. It provides:

- A base `PaperlessError` class for all application-specific errors
- Specialized exceptions for different types of errors (API, webhook, S3, etc.)
- Support for detailed error information to aid in debugging

### Usage

To use the custom exceptions:

```python
from scripts.utils.exceptions import APIError, WebhookError, DataProcessingError

# Raise an API error
raise APIError("Failed to fetch data from API", status_code=500, details={"endpoint": "/api/data"})

# Raise a webhook error
raise WebhookError("Failed to process webhook", details={"event_type": "quote.created"})

# Raise a data processing error
raise DataProcessingError("Failed to process data", details={"file": "data.csv"})
```

## Environment Variables

The following environment variables can be used to configure logging:

- `LOG_LEVEL`: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LOG_FORMAT`: The log format (text or json)
- `LOG_FILE`: The path to the log file (optional)

These can be set in the `.env` file or as environment variables.

## Command-Line Arguments

The following command-line arguments can be used to configure logging in scripts:

- `--log-level`: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--log-file`: The path to the log file (optional)
- `--json-logs`: Output logs in JSON format

## Best Practices

1. **Use the centralized logging configuration**
   - Import `configure_logging` and `get_logger` from `scripts/utils/logging_config.py`
   - Configure logging at the start of your application
   - Get a logger for each module

2. **Use correlation IDs**
   - Use the `@with_correlation_id` decorator for functions that process requests
   - Use the `set_correlation_id` function to set a correlation ID manually

3. **Add context information**
   - Use the `LogContext` context manager to add context information to log records
   - Include relevant information like operation, user ID, etc.

4. **Use custom exceptions**
   - Use the custom exceptions from `scripts/utils/exceptions.py`
   - Include detailed error information in the `details` parameter
   - Catch and handle exceptions appropriately

5. **Log at the appropriate level**
   - Use `logger.debug` for detailed debugging information
   - Use `logger.info` for general information
   - Use `logger.warning` for warnings
   - Use `logger.error` for errors
   - Use `logger.critical` for critical errors