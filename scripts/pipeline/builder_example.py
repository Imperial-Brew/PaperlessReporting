"""
Example of using the PipelineBuilder to create pipelines.

This module demonstrates how to use the PipelineBuilder class to create
pipelines with a fluent interface. It provides examples of creating different
types of pipelines using the builder pattern.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.processors import (
    AccountsDataAcquisitionStage, AccountValidator, AccountTransformer,
    ContactsDataAcquisitionStage, ContactValidator, ContactTransformer,
    CSVLoader
)
from scripts.pipeline.orchestrator import WrapInList
from scripts.pipeline.exceptions import PipelineError


async def create_account_pipeline_example():
    """
    Example of creating an account pipeline using the builder pattern.

    This example demonstrates how to create a pipeline for acquiring,
    validating, transforming, and exporting account data using the
    PipelineBuilder class.
    """
    logger.info("Creating account pipeline using the builder pattern")

    # Create the pipeline using the builder pattern
    pipeline = (PipelineBuilder("account_pipeline")
                .add_acquisition(AccountsDataAcquisitionStage())
                .add_batch_processor(AccountValidator())
                .add_batch_processor(AccountTransformer())
                .add_loading(CSVLoader("data_real/accounts_builder.csv"))
                .build())

    # Configure a longer timeout for the acquisition stage
    pipeline.stages[0].configure_timeout(timeout=1200.0)  # 20 minutes timeout

    try:
        # Run the pipeline
        await pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Account pipeline completed successfully")

        # Print metrics
        metrics = pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def create_contact_pipeline_example():
    """
    Example of creating a contact pipeline using the builder pattern.

    This example demonstrates how to create a pipeline for acquiring,
    validating, transforming, and exporting contact data using the
    PipelineBuilder class.
    """
    logger.info("Creating contact pipeline using the builder pattern")

    # Create the pipeline using the builder pattern
    builder = PipelineBuilder("contact_pipeline")

    # Add stages to the pipeline
    pipeline = (builder
                .add_acquisition(ContactsDataAcquisitionStage())
                .add_batch_processor(ContactValidator())
                .add_batch_processor(ContactTransformer())
                .add_loading(CSVLoader("data_real/contacts_builder.csv"))
                .build())

    # Configure a longer timeout for the acquisition stage
    pipeline.stages[0].configure_timeout(timeout=3600.0)  # 60 minutes timeout

    try:
        # Run the pipeline
        await pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Contact pipeline completed successfully")

        # Print metrics
        metrics = pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def create_single_account_pipeline_example(account_data):
    """
    Example of creating a pipeline for processing a single account.

    This example demonstrates how to create a pipeline for validating,
    transforming, and exporting a single account using the PipelineBuilder class.

    Args:
        account_data: Account data to process
    """
    logger.info("Creating single account pipeline using the builder pattern")

    # Create the pipeline using the builder pattern
    pipeline = (PipelineBuilder("single_account_pipeline")
                .add_validation(AccountValidator())
                .add_transformation(AccountTransformer())
                .add_stage(WrapInList())  # Wrap the transformed account in a list for the CSV loader
                .add_loading(CSVLoader("data_real/single_account_builder.csv"))
                .build())

    try:
        # Run the pipeline
        await pipeline.run(account_data)
        logger.info("Single account pipeline completed successfully")

        # Print metrics
        metrics = pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def main():
    """
    Main entry point for the script.

    Runs the example pipelines to demonstrate the builder pattern.
    """
    # Example account data
    account_data = {
        "id": 12345,
        "name": "Example Company",
        "phone": "555-123-4567",
        "erp_code": "EX123",
        "type": "customer",
        "url": "https://example.com"
    }

    # Run the single account pipeline example
    await create_single_account_pipeline_example(account_data)

    # Uncomment to run the full account pipeline example
    # await create_account_pipeline_example()

    # Uncomment to run the full contact pipeline example
    # await create_contact_pipeline_example()


if __name__ == "__main__":
    asyncio.run(main())
