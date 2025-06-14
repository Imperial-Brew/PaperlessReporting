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

- `scripts/pull_quotes.py`, `pull_orders.py`, `pull_quote_items.py`, `pull_contacts_async.py`  
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
  - **IMPORTANT**: Never commit your `.env` file to version control
  - Always use environment variables for sensitive information, not hardcoded values
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

## Security

This project handles sensitive information such as API keys and AWS credentials. Following these security best practices is essential:

### Credential Management

- **Environment Variables**: All sensitive credentials should be stored in environment variables
  - Use the `.env` file for local development only
  - In production, set environment variables through your hosting platform
  - Never hardcode credentials in source code

- **Secrets Rotation**:
  - Regularly rotate API keys, AWS credentials, and webhook secrets
  - Update your `.env` file and environment variables after rotation

- **Least Privilege Principle**:
  - Use AWS IAM roles with minimal permissions required for the application
  - Create API tokens with only the necessary scopes and permissions

### Secure Development Practices

- **Code Reviews**:
  - Always review code for hardcoded credentials before merging
  - Use the pre-commit hooks to catch accidental credential commits

- **Dependency Management**:
  - Regularly update dependencies to patch security vulnerabilities
  - Use `pip-audit` or similar tools to check for vulnerable dependencies

### Pre-commit Hooks

The repository includes pre-commit hooks to prevent accidentally committing sensitive information:

1. **Installation**:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

2. **Available Hooks**:
   - `detect-secrets`: Scans for potential secrets in code
   - `no-commit-to-branch`: Prevents direct commits to main/master
   - `check-added-large-files`: Prevents committing large files
   - `check-merge-conflict`: Checks for merge conflict strings

3. **Manual Check**:
   ```bash
   pre-commit run --all-files
   ```

### .env File Security

- **Template**: Use `.env.example` as a template with placeholder values
- **Gitignore**: The `.env` file is included in `.gitignore` to prevent accidental commits
- **Local Storage**: Keep your `.env` file secure on your local machine
- **Sharing**: Never share your `.env` file with others; each developer should create their own

### S3 Security

- **Bucket Policies**: Ensure S3 buckets have appropriate access policies
- **Encryption**: Enable server-side encryption for S3 buckets
- **Access Logging**: Enable access logging for S3 buckets to track usage

See [Security Documentation](docs/security.md) for more detailed information.

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
- **S3 Integration**: Support for uploading data to AWS S3. CSVs are saved both locally and to S3 by default.
- **Parallel Processing**: Support for processing data in parallel using asyncio:
  - **BatchProcessor**: Process batches of items in parallel with configurable concurrency
  - **ParallelStage**: Run multiple stages concurrently and combine their results

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

3. **Pipeline Builder**: Simplifies pipeline creation with a fluent interface:
   - `PipelineBuilder`: Builder for creating pipelines with method chaining
   - Provides type-safe methods for adding different types of stages
   - Supports configuration of timeouts, retries, and circuit breakers

### Pipeline Builder

The PipelineBuilder class implements the builder pattern for creating pipelines with a fluent interface. It simplifies the process of creating pipelines by providing methods for adding different types of stages and ensuring type safety between stages.

#### Example Usage

```python
from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.account_contact_processors import (
    AccountsDataAcquisitionStage, AccountValidator, AccountTransformer
)
from scripts.pipeline.processors import CSVLoader

# Create a pipeline using the builder pattern
pipeline = (PipelineBuilder("account_pipeline")
           .add_acquisition(AccountsDataAcquisitionStage())
           .add_batch_processor(AccountValidator())
           .add_batch_processor(AccountTransformer())
           .add_loading(CSVLoader("data_real/accounts.csv"))
           .build())

# Configure a longer timeout for the acquisition stage
pipeline.stages[0].configure_timeout(timeout=1200.0)

# Run the pipeline
await pipeline.run(None)  # No input needed for acquisition stage
```

The builder provides methods for adding different types of stages:
- `add_acquisition`: Add a data acquisition stage
- `add_validation`: Add a validation stage
- `add_transformation`: Add a transformation stage
- `add_loading`: Add a loading stage
- `add_batch_processor`: Add a batch processor stage
- `add_stage`: Add any type of stage (low-level method)

It also provides methods for configuring stages:
- `configure_timeout`: Configure the timeout for a specific stage
- `configure_retry`: Configure retry behavior for a specific stage
- `configure_circuit_breaker`: Configure circuit breaker behavior for a specific stage

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

The current implementation demonstrates the core functionality of the pipeline framework, including the new builder pattern for pipeline creation. Future improvements include:

1. **Short-term**:
   - Integrate with existing scripts
   - Add more validators and transformers
   - Expand S3 integration
   - Refactor factory methods to use the builder pattern

2. **Medium-term**:
   - Enhance retry mechanisms
   - Implement dead letter queues
   - Add pipeline visualization
   - Expand parallel processing capabilities

3. **Long-term**:
   - Integrate with workflow engines
   - Add data lineage tracking
   - Support real-time processing
   - Integrate machine learning capabilities

### Parallel Processing

The pipeline framework supports two types of parallel processing:

#### BatchProcessor

The BatchProcessor class processes a batch of items using another stage, with support for parallel processing using asyncio.gather. This is useful for processing large datasets in parallel.

```python
from scripts.pipeline.processors import BatchProcessor

# Create a processor for individual items
item_processor = MyItemProcessor()

# Create a batch processor with parallel processing
batch_processor = BatchProcessor(
    stage=item_processor,
    name="parallel_batch_processor",
    batch_size=100,  # Process 100 items at a time
    max_concurrency=10  # Process up to 10 items concurrently
)

# Process a list of items in parallel
results = await batch_processor.process(items)
```

#### ParallelStage

The ParallelStage class runs multiple stages concurrently and combines their results into a dictionary. This is useful for running independent operations in parallel.

```python
from scripts.pipeline.processors import ParallelStage

# Create a parallel stage
parallel_stage = ParallelStage("parallel_operations")

# Add stages to be run in parallel
parallel_stage.add_stage("validation", ValidationStage())
parallel_stage.add_stage("transformation", TransformationStage())
parallel_stage.add_stage("enrichment", EnrichmentStage())

# Set a timeout for parallel execution
parallel_stage.set_timeout(30.0)  # 30-second timeout

# Process data through all stages in parallel
results = await parallel_stage.process(data)

# Access results from each stage
validation_result = results["validation"]
transformation_result = results["transformation"]
enrichment_result = results["enrichment"]
```

For a complete example of parallel processing, see [scripts/pipeline/parallel_example.py](scripts/pipeline/parallel_example.py).

See [Pipeline Framework Documentation](scripts/pipeline/README.md) for more details.

## API Client

The project includes a dedicated client for interacting with the Paperless Parts API:

### PaperlessPartsClient

The `PaperlessPartsClient` class encapsulates all API interactions, providing a clean and consistent interface for making requests to the Paperless Parts API.

#### Features

- **Authentication**: Automatically handles API token authentication
- **Rate Limiting**: Built-in rate limiting using the token bucket algorithm
- **Pagination**: Handles paginated responses automatically
- **Error Handling**: Comprehensive error handling with retries and exponential backoff
- **Timeout Handling**: Configurable timeouts for API requests
- **Specialized Methods**: Dedicated methods for common endpoints (accounts, contacts, quotes, orders)
- **Centralized Endpoints**: All API endpoint URLs are defined as constants within the client class

#### Example Usage

```python
from scripts.utils.paperless_client import PaperlessPartsClient

async def fetch_data():
    # Create a client with default settings
    client = PaperlessPartsClient()

    # Fetch all accounts
    accounts = await client.get_accounts()
    print(f"Retrieved {len(accounts)} accounts")

    # Fetch a single account by ID
    account = await client.get_account(12345)

    # Fetch all contacts
    contacts = await client.get_contacts()

    # Fetch quotes within a specific ID range
    quotes = await client.get_quotes(start_id=7500, end_id=7550)

    # Fetch items for a specific quote
    quote_items = await client.get_quote_items(7500)

    # Fetch a quote with a specific revision
    quote_with_revision = await client.get_quote_with_revision(7500, 2)

    # Fetch all quote revisions
    quote_revisions = await client.get_quote_revisions()
```

For a complete example, see [scripts/Examples/client_example.py](scripts/Examples/client_example.py).

### Integration with EntityPuller

The `EntityPuller` class has been updated to use the `PaperlessPartsClient` internally, providing backward compatibility while leveraging the improved API client. This ensures that all API interactions use the same authentication, rate limiting, and endpoint URL handling.

## License

MIT
