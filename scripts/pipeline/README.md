# Data Processing Pipeline Framework

This directory contains a modular pipeline framework for processing data from the Paperless Parts API with validation, transformation, and monitoring capabilities.

## Overview

The pipeline framework provides a structured approach to data processing with the following features:

- **Modular Architecture**: Each pipeline stage is a separate component that can be combined to create custom pipelines.
- **Type Safety**: Generic type parameters ensure type safety between pipeline stages.
- **Validation**: Built-in validation stages for different data types.
- **Transformation**: Stages for transforming data between different formats.
- **Loading**: Stages for loading data into different destinations (CSV, JSON, etc.).
- **Monitoring**: Metrics collection for each stage and the overall pipeline.
- **Error Handling**: Comprehensive error handling with detailed error information.

## Architecture

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

3. **Validators**: Implementations of validation stages for different data types:
   - `QuoteValidator`: Validates quote data
   - `QuoteItemValidator`: Validates quote item data

4. **Processors**: Implementations of transformation and loading stages:
   - `QuoteTransformer`: Transforms quote data
   - `QuoteItemTransformer`: Extracts and transforms quote items
   - `CSVLoader`: Loads data to CSV files
   - `JSONLoader`: Loads data to JSON files

5. **Exceptions**: Custom exceptions for different types of errors:
   - `PipelineError`: Base exception for all pipeline errors
   - `ValidationError`: For validation failures
   - `TransformationError`: For transformation failures
   - `LoadingError`: For loading failures
   - `DataAcquisitionError`: For data acquisition failures

## Usage

### Creating a Pipeline

You can create a pipeline using the factory methods provided by `QuotePipeline` and `QuoteItemPipeline`:

```python
from scripts.pipeline.orchestrator import QuotePipeline

# Create a pipeline for validating quotes
validation_pipeline = QuotePipeline.create_validation_pipeline()

# Create a pipeline for transforming quotes
transformation_pipeline = QuotePipeline.create_transformation_pipeline()

# Create a pipeline for exporting quotes to CSV
csv_pipeline = QuotePipeline.create_csv_export_pipeline("output.csv")
```

Or you can create a custom pipeline by adding stages manually:

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

See the `example.py` script for complete examples of using the pipeline framework.

## Next Steps

The current implementation is a proof of concept that demonstrates the core functionality of the pipeline framework. Here are some potential next steps for expanding the framework:

1. **Data Acquisition Stages**: Implement stages for fetching data from the Paperless Parts API and other sources.

2. **More Validators**: Add validators for other data types (orders, accounts, etc.).

3. **More Transformers**: Add transformers for other data types and formats.

4. **More Loaders**: Add loaders for other destinations (databases, S3, etc.).

5. **Pipeline Visualization**: Add tools for visualizing pipeline execution and metrics.

6. **Parallel Processing**: Add support for parallel processing of data.

7. **Retry Mechanisms**: Add configurable retry mechanisms for failed stages.

8. **Dead Letter Queues**: Add support for storing failed records for later processing.

9. **Workflow Engine Integration**: Integrate with a workflow engine like Apache Airflow for more complex pipelines.

10. **Data Lineage Tracking**: Add support for tracking the origin and transformations of data.