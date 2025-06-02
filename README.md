# PaperlessReporting

A Python-based tool for pulling, processing, and reporting data from the Paperless Parts API.

## What This Repository Does

- Python scripts under `scripts/` pull data (quotes, orders, quote_items, etc.) from the PaperlessParts API
- Utilities in `scripts/utils/` merge batches of CSVs into cleaned outputs
- A GitHub Actions CI pipeline (`.github/workflows/ci.yml`) lints, tests, and builds docs
- Data lands in `data_raw/` then is consolidated in `data_cleaned/`
- Webhook server receives and processes events from Paperless Parts

## Key Scripts

- `scripts/pull_quotes.py`, `pull_orders.py`, `pull_quote_items.py`  
  → each uses the same API-Token header, paginates/rate-limits, writes CSVs under `data_raw/`
- `scripts/utils/merge_*.py`  
  → read all `*_*.csv` in `data_raw/…`, drop duplicates, output a single `data_cleaned/*.csv`
- `scripts/utils/token_bucket.py`  
  → simple rate-limiter used by the pull scripts
- `scripts/webhook_server.py`
  → receives and processes webhook events from Paperless Parts

## Environment & Configuration

- Environment variables are used for sensitive credentials (API keys, AWS credentials)
- Copy `.env.example` to `.env` and fill in your values
- `config.json` is used for non-sensitive configuration
- CI relies on Python 3.9+, pytest for tests, flake8 for linting

## Workflow

1. `git pull` latest  
2. `python scripts/pull_quotes.py` (etc.) to regenerate raw CSVs  
3. `python scripts/utils/merge_all_batches.py` to consolidate  
4. Commit CSVs, push → CI runs and validates formatting + simple smoke tests

## Development

1. Set up environment variables:
```bash
# Copy the example .env file
cp .env.example .env

# Edit .env with your credentials
# DO NOT commit your .env file to version control
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run tests:
```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=scripts

# Run specific test file
pytest tests/test_pull_users.py

# Run specific test
pytest tests/test_pull_users.py::test_fetch_users
```

## Documentation

The project includes comprehensive documentation:

- **[Webhook Server](docs/webhook.md)**: Documentation for the webhook server, including setup, configuration, and supported events
- **[S3 Configuration](docs/s3_configuration.md)**: Guide for setting up and configuring AWS S3 integration
- **[Testing](docs/testing.md)**: Detailed information about testing, including how to run tests and coverage reporting
- **[Logging and Error Handling](docs/logging.md)**: Information about the logging and error handling system
- **[Changelog](CHANGELOG.md)**: Record of all notable changes to the project

## Testing

The project includes a comprehensive test suite:

- **Unit Tests**: Test individual components in isolation
  - Tests for data pulling scripts (users, accounts, etc.)
  - Tests for configuration loading
  - Tests for async utilities
  - Tests for webhook server

- **Integration Tests**: Test the interaction between components
  - End-to-end tests for data pulling and CSV generation
  - Tests for webhook event handling

See [Testing Documentation](docs/testing.md) for more details.

## License

MIT
