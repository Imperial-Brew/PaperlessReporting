# Testing Documentation for PaperlessReporting

## Overview

This document provides comprehensive information about testing in the PaperlessReporting project, including test structure, how to run tests, coverage reporting, and best practices.

## Test Structure

The tests are organized by component and include both unit tests and integration tests:

- **Unit Tests**: Test individual components in isolation
  - `test_pull_users.py`: Tests for the user data pulling script
  - `test_config_loader.py`: Tests for the configuration loader
  - `test_async_puller.py`: Tests for the asynchronous data pulling utility
  - `test_webhook_server.py`: Tests for the webhook server
  - `test_s3_config.py`: Tests for the S3 configuration

- **Integration Tests**: Test the interaction between components
  - `test_integration.py`: End-to-end tests for data pulling and CSV generation
  - `test_webhook.py`: Tests for the webhook server with actual HTTP requests
  - `test_order_created.py`: Tests for the order.created event handling
  - `test_quote_created.py`: Tests for the quote.created event handling
  - `test_quote_created_fix.py`: Tests for the fixed quote.created event handling

## Running Tests

### Basic Test Commands

To run all tests:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/test_pull_users.py
```

To run a specific test:

```bash
pytest tests/test_pull_users.py::test_fetch_users
```

### Running Tests With Coverage

To run tests with coverage reporting, you need to install the pytest-cov plugin:

```bash
pip install pytest-cov
```

Alternatively, you can uncomment the pytest-cov line in requirements.txt and run:

```bash
pip install -r requirements.txt
```

Then you can run pytest with the coverage arguments:

```bash
pytest --cov=scripts --cov-report=term --cov-report=html
```

Or to run a specific test file with coverage:

```bash
pytest tests/test_pull_users.py --cov=scripts --cov-report=term --cov-report=html
```

## Pytest Configuration

The pytest configuration is defined in `pytest.ini` in the project root. It includes:

- Test discovery patterns
- Coverage reporting configuration

The `addopts` line in pytest.ini has been commented out to make coverage reporting optional. This allows pytest to run without the pytest-cov plugin installed.

If you want to restore the automatic coverage reporting for all pytest runs, you can uncomment the `addopts` line in pytest.ini:

```
# Configure pytest-cov (only used if pytest-cov is installed)
addopts = --cov=scripts --cov-report=term --cov-report=html
```

Note that this will require the pytest-cov plugin to be installed for all pytest runs.

## Coverage Reporting

The project is configured to generate coverage reports when running tests with the coverage options. The coverage report will show which parts of the codebase are covered by tests and which parts need more testing.

- **Terminal Report**: Shows a summary of coverage in the terminal
- **HTML Report**: Generates a detailed HTML report in the `htmlcov/` directory

## Adding New Tests

When adding new tests:

1. Create a new test file in the `tests` directory with the naming pattern `test_*.py`
2. Use pytest fixtures for common setup
3. Use mocking to isolate components
4. For async tests, use the `@pytest.mark.asyncio` decorator

## Mocking Strategy

The tests use mocking to avoid making actual API calls:

- `unittest.mock` for synchronous code
- `AsyncMock` for asynchronous code
- Custom mock classes for specific behaviors

## Test Data

Test data is defined in fixtures within each test file. This makes it easy to reuse test data across multiple tests.

## Best Practices

1. **Write Tests First**: Follow a test-driven development approach when possible
2. **Keep Tests Small and Focused**: Each test should test one specific behavior
3. **Use Descriptive Test Names**: Test names should describe what the test is checking
4. **Use Fixtures for Common Setup**: Avoid duplicating setup code
5. **Mock External Dependencies**: Tests should not depend on external services
6. **Check Edge Cases**: Test boundary conditions and error cases
7. **Maintain High Coverage**: Aim for high test coverage, especially for critical code paths