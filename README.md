# PaperlessReporting

A Python-based tool for pulling, processing, and reporting data from the Paperless Parts API.

## What This Repository Does

- Python scripts under `scripts/` pull data (quotes, orders, quote_items, etc.) from the PaperlessParts API
- Utilities in `scripts/utils/` merge batches of CSVs into cleaned outputs
- A GitHub Actions CI pipeline (`.github/workflows/ci.yml`) lints, tests, and builds docs
- Data lands in `data_raw/` then is consolidated in `data_cleaned/`
- Webhook server receives and processes events from Paperless Parts
- Data processing pipeline framework for structured data processing with validation, transformation, and monitoring

## Key Scripts

- `scripts/pull_quotes.py`, `pull_orders.py`, `pull_quote_items.py`  
  → each uses the same API-Token header, paginates/rate-limits, writes CSVs under `data_raw/`
- `scripts/utils/merge_*.py`  
  → read all `*_*.csv` in `data_raw/…`, drop duplicates, output a single `data_cleaned/*.csv`
- `scripts/utils/token_bucket.py`  
  → simple rate-limiter used by the pull scripts
- `scripts/webhook_server.py`
  → receives and processes webhook events from Paperless Parts
- `scripts/pipeline/example.py`
  → demonstrates the pipeline framework with sample data
- `scripts/pipeline/run_real_data_pipeline.py`
  → runs the pipeline with real data from the Paperless Parts API

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
- **[Pipeline Framework](scripts/pipeline/README.md)**: Documentation for the data processing pipeline framework

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

## Data Processing Pipeline Framework

The project includes a modular pipeline framework for processing data from the Paperless Parts API with validation, transformation, and monitoring capabilities.

### Features

- **Modular Architecture**: Each pipeline stage is a separate component that can be combined to create custom pipelines.
- **Type Safety**: Generic type parameters ensure type safety between pipeline stages.
- **Validation**: Built-in validation stages for different data types.
- **Transformation**: Stages for transforming data between different formats.
- **Loading**: Stages for loading data into different destinations (CSV, JSON, S3, etc.).
- **Monitoring**: Metrics collection for each stage and the overall pipeline.
- **Error Handling**: Comprehensive error handling with detailed error information.
- **Incremental Processing**: Support for processing only new or changed data.
- **S3 Integration**: Support for uploading data to AWS S3.

### Architecture

The pipeline framework is built around the following components:

1. **Pipeline Stages**: Abstract base classes for different types of stages:
   - `DataAcquisitionStage`: Fetches data from external sources
   - `ValidationStage`: Validates data against rules
   - `TransformationStage`: Transforms data between formats
   - `LoadingStage`: Loads data into destinations

2. **Pipeline Orchestrator**: Connects stages and executes them in sequence:
   - `Pipeline`: Generic pipeline that can process any type of data
   - `QuotePipeline`: Factory for creating quote processing pipelines
   - `QuoteItemPipeline`: Factory for creating quote item processing pipelines
   - `AccountPipeline`: Factory for creating account processing pipelines
   - `ContactPipeline`: Factory for creating contact processing pipelines

### Usage Examples

#### Example Pipeline

The example pipeline demonstrates how to use the framework with sample data:

```bash
python scripts/pipeline/example.py
```

This will:
1. Create a sample quote
2. Validate the quote data
3. Transform the quote data
4. Export the quote data to CSV
5. Extract and validate quote items
6. Export quote items to CSV
7. Demonstrate error handling with invalid data

#### Real Data Pipeline

The real data pipeline fetches quote data from the Paperless Parts API:

```bash
python scripts/pipeline/run_real_data_pipeline.py --start-id 7500 --end-id 7550 --output-dir data_real
```

Command-line arguments:
- `--start-id`: Starting quote ID (default: 7500)
- `--end-id`: Ending quote ID (default: 7550)
- `--output-dir`: Local output directory
- `--no-revisions`: Exclude revised quotes
- `--incremental`: Process only new or changed quotes
- `--state-file`: Path to the state file for tracking processed quotes
- `--s3-bucket`: S3 bucket name for output
- `--s3-prefix`: S3 prefix (folder) for output files
- `--s3-region`: AWS region for S3

#### Account and Contact Pipeline

The account and contact pipeline fetches account and contact data from the Paperless Parts API:

```bash
python scripts/pipeline/run_account_contact_pipeline.py --output-dir data_real
```

Command-line arguments:
- `--output-dir`: Local output directory (default: data_real)
- `--accounts-only`: Process only accounts
- `--contacts-only`: Process only contacts

This pipeline always performs a full pull of all accounts and contacts to ensure we catch any updates. Accounts and contacts are much smaller replies from the API, so we don't need to batch them.

This will:
1. Fetch account data from the Paperless Parts API
2. Validate the account data
3. Transform the account data
4. Export the account data to CSV
5. Fetch contact data from the Paperless Parts API
6. Validate the contact data
7. Transform the contact data
8. Export the contact data to CSV

### Next Steps

The current implementation is a proof of concept that demonstrates the core functionality of the pipeline framework. Future improvements include:

1. **Short-term**:
   - Integrate with existing scripts
   - Add more validators and transformers
   - Expand S3 integration

2. **Medium-term**:
   - Add retry mechanisms
   - Implement dead letter queues
   - Add parallel processing
   - Add pipeline visualization

3. **Long-term**:
   - Integrate with workflow engines
   - Add data lineage tracking
   - Support real-time processing
   - Integrate machine learning capabilities

See [Pipeline Framework Documentation](scripts/pipeline/README.md) for more details.

## License

MIT
