# Testing Documentation for PaperlessReporting

This directory contains tests for the PaperlessReporting project. The tests are organized by component and include both unit tests and integration tests.

## Test Structure

- **Unit Tests**: Test individual components in isolation
  - `test_pull_users.py`: Tests for the user data pulling script
  - `test_config_loader.py`: Tests for the configuration loader
  - `test_async_puller.py`: Tests for the asynchronous data pulling utility
  - `test_webhook_server.py`: Tests for the webhook server

- **Integration Tests**: Test the interaction between components
  - `test_integration.py`: End-to-end tests for data pulling and CSV generation

## Running Tests

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

## Coverage Reporting

The project is configured to generate coverage reports when running tests. To view coverage:

```bash
# Run tests with coverage
pytest

# View HTML coverage report
# This will be generated in the htmlcov directory
```

The coverage report will show which parts of the codebase are covered by tests and which parts need more testing.

## Test Configuration

The test configuration is defined in `pytest.ini` in the project root. It includes:

- Test discovery patterns
- Coverage reporting configuration

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