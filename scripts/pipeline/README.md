# Data Processing Pipeline Framework

This directory contains a modular pipeline framework for processing data from the Paperless Parts API with validation, transformation, and monitoring capabilities.

## Overview

The pipeline framework provides a structured approach to data processing with the following features:

- **Modular Architecture**: Each pipeline stage is a separate component that can be combined to create custom pipelines.
- **Type Safety**: Generic type parameters ensure type safety between pipeline stages.
- **Validation**: Built-in validation stages for different data types.
- **Transformation**: Stages for transforming data between different formats.
- **Loading**: Stages for loading data into different destinations (CSV, JSON, S3, etc.).
- **Monitoring**: Metrics collection for each stage and the overall pipeline.
- **Error Handling**: Comprehensive error handling with detailed error information.
- **Parallel Processing**: Support for processing data in parallel using asyncio:
  - **BatchProcessor**: Process batches of items in parallel with configurable concurrency
  - **ParallelStage**: Run multiple stages concurrently and combine their results
- **Pipeline Builder**: Simplified pipeline creation with a fluent interface.
- **S3 Integration**: Support for uploading data to AWS S3. CSVs are saved both locally and to S3 by default.
- **Incremental Processing**: Support for processing only new or changed data.

## Architecture

The pipeline framework is built around the following components:

1. **Pipeline Stages**: Abstract base classes for different types of stages:
   - `DataAcquisitionStage`: Fetches data from external sources
   - `ValidationStage`: Validates data against rules
   - `TransformationStage`: Transforms data between formats
   - `LoadingStage`: Loads data into destinations
   - `BatchProcessor`: Processes batches of items in parallel
   - `ParallelStage`: Runs multiple stages concurrently

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

4. **Validators**: Implementations of validation stages for different data types:
   - `QuoteValidator`: Validates quote data
   - `QuoteItemValidator`: Validates quote item data
   - `AccountValidator`: Validates account data
   - `ContactValidator`: Validates contact data

5. **Processors**: Implementations of transformation and loading stages:
   - `QuoteTransformer`: Transforms quote data
   - `QuoteItemTransformer`: Extracts and transforms quote items
   - `AccountTransformer`: Transforms account data
   - `ContactTransformer`: Transforms contact data
   - `AccountsDataAcquisitionStage`: Fetches account data from the API
   - `ContactsDataAcquisitionStage`: Fetches contact data from the API
   - `NewContactsDataAcquisitionStage`: Fetches contact data using the new async API
   - `CSVLoader`: Loads data to CSV files locally and uploads to S3 by default
   - `JSONLoader`: Loads data to JSON files
   - `S3Loader`: Loads data to AWS S3
   - `BatchProcessor`: Processes batches of items in parallel
   - `ParallelStage`: Runs multiple stages concurrently

6. **Exceptions**: Custom exceptions for different types of errors:
   - `PipelineError`: Base exception for all pipeline errors
   - `ValidationError`: For validation failures
   - `TransformationError`: For transformation failures
   - `LoadingError`: For loading failures
   - `DataAcquisitionError`: For data acquisition failures

## Usage

### Creating a Pipeline

#### Using the PipelineBuilder (Recommended)

The PipelineBuilder class implements the builder pattern for creating pipelines with a fluent interface. It simplifies the process of creating pipelines by providing methods for adding different types of stages and ensuring type safety between stages.

```python
from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.processors import (
    AccountsDataAcquisitionStage, AccountValidator, AccountTransformer,
    CSVLoader
)

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

#### Using Factory Methods

You can create a pipeline using the factory methods provided by the pipeline classes:

```python
from scripts.pipeline.orchestrator import QuotePipeline, AccountPipeline, ContactPipeline

# Create pipelines for quotes
quote_validation_pipeline = QuotePipeline.create_validation_pipeline()
quote_transformation_pipeline = QuotePipeline.create_transformation_pipeline()
quote_csv_pipeline = QuotePipeline.create_csv_export_pipeline("quotes.csv")

# Create pipelines for accounts
account_validation_pipeline = AccountPipeline.create_validation_pipeline()
account_transformation_pipeline = AccountPipeline.create_transformation_pipeline()
account_csv_pipeline = AccountPipeline.create_csv_export_pipeline("accounts.csv")
account_acquisition_pipeline = AccountPipeline.create_acquisition_pipeline(
    output_path="accounts.csv"
)

# Create pipelines for contacts
contact_validation_pipeline = ContactPipeline.create_validation_pipeline()
contact_transformation_pipeline = ContactPipeline.create_transformation_pipeline()
contact_csv_pipeline = ContactPipeline.create_csv_export_pipeline("contacts.csv")
contact_acquisition_pipeline = ContactPipeline.create_acquisition_pipeline(
    output_path="contacts.csv"
)
```

> **Note**: The account and contact acquisition pipelines always perform a full pull of all accounts and contacts to ensure we catch any updates. Accounts and contacts are much smaller replies from the API, so we don't need to batch them.

#### Creating a Custom Pipeline Manually

You can create a custom pipeline by adding stages manually:

```python
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.validators import QuoteValidator
from scripts.pipeline.processors import QuoteTransformer, CSVLoader

# Create a custom pipeline
pipeline = Pipeline("custom_pipeline")
pipeline.add_stage(QuoteValidator())
pipeline.add_stage(QuoteTransformer())
pipeline.add_stage(CSVLoader("output.csv"))
```

### Running a Pipeline

Pipelines are run asynchronously using the `run` method:

```python
import asyncio

async def process_quote(quote_data):
    try:
        # Run the pipeline
        result = await pipeline.run(quote_data)
        print("Pipeline completed successfully")

        # Get pipeline metrics
        metrics = pipeline.get_metrics()
        print(f"Pipeline duration: {metrics['duration']:.2f}s")
    except PipelineError as e:
        print(f"Pipeline error: {e.message}")

# Run the async function
asyncio.run(process_quote(quote_data))
```

### Error Handling

Pipelines provide detailed error information through the `PipelineError` exception and metrics:

```python
try:
    await pipeline.run(data)
except PipelineError as e:
    print(f"Pipeline error: {e.message}")
    print(f"Error details: {e.details}")

    # Get error information from metrics
    for error in pipeline.get_metrics().get("errors", []):
        print(f"  {error['stage_name']}: {error['error_message']}")
```

### Metrics

Pipelines collect metrics for each stage and the overall pipeline:

```python
# Get pipeline metrics
metrics = pipeline.get_metrics()

# Print pipeline duration
print(f"Pipeline duration: {metrics['duration']:.2f}s")

# Print stage metrics
for stage_name, stage_metrics in metrics.get("stage_metrics", {}).items():
    print(f"Stage: {stage_name}")
    print(f"  Duration: {stage_metrics['duration']:.2f}s")
    print(f"  Success: {stage_metrics['success']}")
    print(f"  Metrics: {stage_metrics['metrics']}")
```

## Examples

The following example scripts demonstrate different aspects of the pipeline framework:

- **[pipeline_example.py](../Examples/pipeline_example.py)**: Basic example of using the pipeline framework with sample data
- **[pipeline_parallel_example.py](../Examples/pipeline_parallel_example.py)**: Demonstrates parallel processing capabilities
- **[pipeline_builder_example.py](../Examples/pipeline_builder_example.py)**: Shows how to use the builder pattern to create pipelines
- **[run_real_data_pipeline.py](run_real_data_pipeline.py)**: Shows how to use the pipeline with real data from the API
- **[run_account_contact_pipeline.py](run_account_contact_pipeline.py)**: Example of fetching and processing account and contact data

## Next Steps

The current implementation provides a robust foundation for data processing with the pipeline framework. Here are some potential next steps for further expanding the framework:

1. **More Validators**: Add validators for other data types (orders, users, etc.).

2. **More Transformers**: Add transformers for other data types and formats.

3. **Pipeline Visualization**: Add tools for visualizing pipeline execution and metrics.

4. **Enhanced Retry Mechanisms**: Expand the configurable retry mechanisms for failed stages.

5. **Dead Letter Queues**: Add support for storing failed records for later processing.

6. **Workflow Engine Integration**: Integrate with a workflow engine like Apache Airflow for more complex pipelines.

7. **Data Lineage Tracking**: Add support for tracking the origin and transformations of data.

8. **Real-time Processing**: Add support for processing data in real-time using streaming technologies.

9. **Machine Learning Integration**: Add support for integrating machine learning models into the pipeline.

10. **Distributed Processing**: Expand parallel processing capabilities to support distributed processing across multiple machines.
