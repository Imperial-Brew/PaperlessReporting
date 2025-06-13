"""
Script to run the pipeline with account and contact data from the Paperless Parts API.

This script fetches account and contact data from the Paperless Parts API, processes it
through the pipeline, and saves the results to CSV files.
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional, Union, Type

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.orchestrator import Pipeline
from scripts.pipeline.account_contact_orchestrator import AccountPipeline, ContactPipeline
from scripts.pipeline.exceptions import PipelineError


async def process_account_data(
    output_dir: str = "data_real"
):
    """
    Process account data from the Paperless Parts API.

    Args:
        output_dir: Directory for output files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output paths
    accounts_csv_path = os.path.join(output_dir, "accounts.csv")

    # Create and run the accounts pipeline
    logger.info("Processing all accounts")
    accounts_pipeline = AccountPipeline.create_acquisition_pipeline(
        output_path=accounts_csv_path
    )

    # Configure a longer timeout for the acquisition stage
    acquisition_stage = accounts_pipeline.stages[0]
    acquisition_stage.configure_timeout(timeout=1200.0)  # 20 minutes timeout

    try:
        # Run the pipeline
        await accounts_pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Account processing completed successfully")

        # Print metrics
        metrics = accounts_pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

        # Log the output file path
        logger.info(f"Accounts exported to {accounts_csv_path}")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in accounts_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def process_contact_data(
    output_dir: str = "data_real"
):
    """
    Process contact data from the Paperless Parts API.

    Args:
        output_dir: Directory for output files
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Determine output paths
    contacts_csv_path = os.path.join(output_dir, "contacts.csv")

    # Create and run the contacts pipeline using the new script
    logger.info("Processing all contacts using the new pull_contacts script")
    contacts_pipeline = ContactPipeline.create_acquisition_pipeline_with_new_script(
        output_path=contacts_csv_path
    )

    # Configure a longer timeout for the acquisition stage
    acquisition_stage = contacts_pipeline.stages[0]
    acquisition_stage.configure_timeout(timeout=3600.0)  # 60 minutes timeout

    try:
        # Run the pipeline
        await contacts_pipeline.run(None)  # No input needed for acquisition stage
        logger.info("Contact processing completed successfully")

        # Print metrics
        metrics = contacts_pipeline.get_metrics()
        logger.info(f"Pipeline duration: {metrics['duration']:.2f}s")

        # Display detailed validation metrics if available
        stage_metrics = metrics.get('stage_metrics', {})
        for stage_name, stage_data in stage_metrics.items():
            if 'contact_validator' in stage_name:
                validator_metrics = stage_data.get('metrics', {})

                # Display validation error counts
                total_errors = validator_metrics.get('validation_errors', 0)
                logger.info(f"Contact validation results:")
                logger.info(f"  Total validation errors: {total_errors}")

                # Display detailed error metrics
                missing_fields = validator_metrics.get('missing_required_field_errors', 0)
                invalid_types = validator_metrics.get('invalid_type_errors', 0)
                invalid_emails = validator_metrics.get('invalid_email_errors', 0)
                invalid_phones = validator_metrics.get('invalid_phone_errors', 0)

                logger.info(f"  Missing required field errors: {missing_fields}")
                logger.info(f"  Invalid type errors: {invalid_types}")
                logger.info(f"  Invalid email format errors: {invalid_emails}")
                logger.info(f"  Invalid phone format errors: {invalid_phones}")

                # Display fields with errors
                error_fields = validator_metrics.get('error_fields', [])
                if error_fields:
                    logger.info(f"  Fields with errors: {', '.join(error_fields)}")

        # Log the output file path
        logger.info(f"Contacts exported to {contacts_csv_path}")

    except PipelineError as e:
        logger.error(f"Pipeline error: {e.message}")
        for error in contacts_pipeline.get_metrics().get("errors", []):
            logger.error(f"  {error['stage_name']}: {error['error_message']}")
        raise


async def process_all_data(
    output_dir: str = "data_real",
    data_types: list = None
):
    """
    Process both account and contact data from the Paperless Parts API.

    Args:
        output_dir: Directory for output files
        data_types: List of data types to process (accounts, contacts)
    """
    if data_types is None:
        data_types = ["accounts", "contacts"]

    try:
        if "accounts" in data_types:
            await process_account_data(output_dir)

        if "contacts" in data_types:
            await process_contact_data(output_dir)

        logger.info("All data processing completed successfully")

    except Exception as e:
        logger.error(f"Error processing data: {str(e)}")
        raise


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process account and contact data from the Paperless Parts API")

    # Output options
    parser.add_argument("--output-dir", type=str, default="data_real", help="Output directory")

    # Data type options
    parser.add_argument("--accounts-only", action="store_true", help="Process only accounts")
    parser.add_argument("--contacts-only", action="store_true", help="Process only contacts")

    args = parser.parse_args()

    # Determine which data types to process
    data_types = []
    if args.accounts_only:
        data_types.append("accounts")
    elif args.contacts_only:
        data_types.append("contacts")
    else:
        data_types = ["accounts", "contacts"]

    # Run the pipeline
    asyncio.run(process_all_data(
        output_dir=args.output_dir,
        data_types=data_types
    ))
