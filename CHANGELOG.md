# Changelog

All notable changes to the PaperlessReporting project will be documented in this file.

## [Unreleased]

### Added
- Parallel processing capabilities to the pipeline framework
  - Enhanced `BatchProcessor` to support true parallel processing using asyncio
  - Added `ParallelStage` for running multiple stages concurrently
  - Added example script `scripts/pipeline/parallel_example.py` to demonstrate parallel processing
- Pipeline builder pattern for simplified pipeline creation
  - Added `PipelineBuilder` class with fluent interface for creating pipelines
  - Added type-safe methods for adding different types of stages
  - Added support for configuring timeouts, retries, and circuit breakers
  - Added example script `scripts/pipeline/builder_example.py` to demonstrate the builder pattern
- Dedicated API client for Paperless Parts
  - Created `PaperlessPartsClient` class to encapsulate all API interactions
  - Centralized endpoint URLs as constants within the client
  - Added specialized methods for common endpoints (accounts, contacts, quotes, orders)
  - Added example script `scripts/Examples/client_example.py` to demonstrate the client
- Validation utilities for common data formats
  - Added `scripts/utils/validation.py` with functions for validating emails, phone numbers, etc.

### Changed
- Improved credential management
  - Removed hardcoded API keys and AWS credentials from config.json
  - Updated config_loader.py to load credentials from environment variables
  - Added documentation on credential management
- Consolidated duplicate code in pull scripts
  - Created `EntityPuller` base class for common functionality
  - Refactored `AccountsPuller` and `ContactsPuller` to extend `EntityPuller`
  - Standardized error handling and logging
- Updated README.md with documentation for new features
  - Added sections for parallel processing, pipeline builder, and API client
  - Added examples for each new feature

### Fixed
- Consolidated documentation into a single README.md and specialized docs in the docs/ directory
- Created CHANGELOG.md to track all changes
- Moved all test files to the tests/ directory
- Standardized test naming

## [2023-06-15]

### Added
- Support for `order.created` event type in the webhook server
  - Modified `scripts/webhook_server.py` to handle `order.created` events
  - Reused the existing `handle_order_status_changed` function to process the order data
  - Added logging to track order creation events
- Created test script `scripts/test_order_created.py` to test the `order.created` event handling

## [2023-06-01]

### Added
- Support for `quote.created` event type in the webhook server
  - Modified `scripts/webhook_server.py` to handle `quote.created` events
  - Reused the existing `handle_quote_status_changed` function to process the quote data
  - Added logging to track quote creation events
- Created test script `scripts/test_quote_created.py` to test the `quote.created` event handling

### Fixed
- Quote created event processing
  - Updated the `handle_quote_status_changed` function to check for both `quote_number` and `number` fields
  - Added fallback logic to use `number` if `quote_number` is not present
  - Updated the function's docstring to reflect that it handles both event types
- Created test script `scripts/test_quote_created_fix.py` to verify the fix

## [2023-05-15]

### Added
- AWS S3 Configuration in Render
  - Added S3 environment variables to `render.yaml` for deployment
  - Added configuration for:
    - S3_BUCKET_NAME
    - AWS_DEFAULT_REGION
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY

### Fixed
- S3 Configuration issues
  - Improved AWS credentials loading
  - Updated bucket name in config.json
  - Added better logging for bucket name source
  - Created `scripts/test_s3_config.py` to test S3 configuration

## [2023-05-01]

### Fixed
- App Structure Issues
  - Fixed the error: `name 'app' is not defined` in the webhook server
  - Removed direct use of 'app' in webhook_server.py
    - Removed `@app.route` decorators
    - Removed code that used `app.url_map.iter_rules()`
    - Modified the `if __name__ == "__main__":` block to create a Flask app if the script is run directly
  - Fixed merge conflicts in render.yaml
    - Resolved conflicts to use `gunicorn app:app` as the start command

## [2023-04-15]

### Fixed
- Pytest Configuration
  - Updated pytest configuration to make coverage reporting optional
  - Commented out the `addopts` line in pytest.ini
  - Added documentation on how to run tests with and without coverage

## [2023-04-01]

### Added
- Logging and Error Handling Improvements
  - Centralized logging configuration
  - Custom exception hierarchy
  - Improved error handling
  - Request tracking with correlation IDs
