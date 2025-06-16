"""
Data Pipeline Script for PaperlessReporting

This script builds a pipeline to pull the following data:
- Quotes and items for quote#s 7900-7935, including any revisions in that range
- Orders and items for order#s 550-571, including any revisions in that range
- All accounts
- All contacts
- All users

The script saves raw data to the relevant PaperlessReporting\data_raw folder,
verifies completion of each pipeline module, and saves final merged data-sets
to the relevant PaperlessReporting\data_real folder and S3.
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Configure logging
from scripts.utils.logging_config import configure_logging, get_logger
configure_logging(level="INFO")
logger = get_logger(__name__)

# Import pipeline components
from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.base import DataAcquisitionStage, ValidationStage, TransformationStage, LoadingStage
from scripts.pipeline.processors import (
    QuotesDataAcquisitionStage, QuoteTransformer, QuoteItemExtractor,
    OrdersDataAcquisitionStage, OrderTransformer, OrderItemExtractor,
    AccountsDataAcquisitionStage, AccountTransformer, NewAccountsDataAcquisitionStage, ImprovedAccountsDataAcquisitionStage,
    ContactsDataAcquisitionStage, ContactTransformer, NewContactsDataAcquisitionStage,
    CSVLoader, BatchProcessor, ParallelStage
)
from scripts.pipeline.exceptions import PipelineError, TransformationError
from scripts.pipeline.s3_integration import S3Loader
from scripts.pipeline.context_registry import get_global_context
import os

# Define a UsersDataAcquisitionStage class
class UsersDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching users from the Paperless Parts API.

    This stage performs a full pull of all users.
    """

    def __init__(self, name: str = "users_acquisition"):
        """
        Initialize the users data acquisition stage.

        Args:
            name: Name of the stage
        """
        super().__init__(name)

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch users from the Paperless Parts API.

        Returns:
            List of user dictionaries
        """
        from scripts.pull_users import fetch_users

        # Fetch users
        users = fetch_users()

        # Record metrics
        self.record_metric("total_users", len(users))

        return users

# Define a UserTransformer class
class UserTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for user data.

    This transformer processes raw user data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "user_transformer"):
        """
        Initialize the user transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform user data.

        Args:
            data: Raw user data to transform

        Returns:
            Transformed user data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "user_id": data.get("id", ""),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "email": data.get("email", ""),
                "role": data.get("role", ""),
                "is_active": data.get("is_active", False),
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming user data: {str(e)}", data=data)

# Define a pipeline verification function
async def verify_pipeline_completion(pipeline, data, stage_name):
    """
    Verify that a pipeline stage completed successfully.

    Args:
        pipeline: The pipeline to verify
        data: The input data for the pipeline
        stage_name: The name of the stage to verify

    Returns:
        True if the stage completed successfully, False otherwise
    """
    try:
        # Run the pipeline
        result = await pipeline.run(data)

        # Get the metrics
        metrics = pipeline.get_metrics()

        # Check if there were any errors
        errors = metrics.get("errors", [])
        if errors:
            logger.error(f"Pipeline {stage_name} failed with errors: {errors}")
            return False

        # Check stage-specific metrics
        stage_metrics = metrics.get("stage_metrics", {})
        for stage, stage_data in stage_metrics.items():
            if not stage_data.get("success", False):
                logger.error(f"Stage {stage} in pipeline {stage_name} failed")
                return False

        logger.info(f"Pipeline {stage_name} completed successfully")
        return True
    except Exception as e:
        logger.error(f"Pipeline {stage_name} failed with exception: {str(e)}")
        return False

async def run_quotes_pipeline():
    """
    Run the quotes pipeline.

    This pipeline pulls quotes and quote items for quote#s 7900-7935,
    including any revisions in that range.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting quotes pipeline")
    overall_success = True

    # Create a pipeline for quotes
    quotes_pipeline = (PipelineBuilder("quotes_pipeline")
                      .add_acquisition(QuotesDataAcquisitionStage(start_id=7900, end_id=7935))
                      .add_batch_processor(BatchProcessor(QuoteTransformer()))
                      .add_loading(CSVLoader("data_raw/quotes/quotes_7900_7935.csv"))
                      .build())

    # Verify quotes pipeline completion
    quotes_success = await verify_pipeline_completion(quotes_pipeline, None, "quotes_pipeline")
    if not quotes_success:
        overall_success = False

    # Create a pipeline for quote items
    if quotes_success:
        # Get the quote items from the context
        quote_items = get_global_context("quotes_pipeline", "quote_items")

        # If quote items are not found in the context, try to get them from the QuotesDataAcquisitionStage directly
        if not quote_items:
            logger.info("Quote items not found in context, attempting to retrieve from QuotesPuller")
            try:
                from scripts.pull_quotes_async import QuotesPuller
                puller = QuotesPuller(start_id=7900, end_id=7935, output_dir="data_raw")
                await puller.run()
                quote_items = puller.quote_items

                # Store the quote items in the global context for future use
                if quote_items:
                    from scripts.pipeline.context_registry import set_global_context
                    set_global_context("quotes_pipeline", "quote_items", quote_items)
                    logger.info(f"Retrieved {len(quote_items)} quote items directly from QuotesPuller")
            except Exception as e:
                logger.error(f"Error retrieving quote items directly: {str(e)}")

        if quote_items:
            # Ensure the output directory exists
            import os
            os.makedirs("data_raw/quote_items", exist_ok=True)

            quote_items_pipeline = (PipelineBuilder("quote_items_pipeline")
                                  .add_batch_processor(BatchProcessor(QuoteItemExtractor()))
                                  .add_loading(CSVLoader("data_raw/quote_items/quote_items_7900_7935.csv"))
                                  .build())

            # Verify quote items pipeline completion
            quote_items_success = await verify_pipeline_completion(quote_items_pipeline, quote_items, "quote_items_pipeline")

            if quote_items_success:
                logger.info("Quote items pipeline completed successfully")
            else:
                logger.error("Quote items pipeline failed")
                overall_success = False
        else:
            logger.warning("No quote items found in context or from direct retrieval")
    else:
        logger.error("Quotes pipeline failed, skipping quote items pipeline")

    logger.info("Quotes pipeline completed")
    return overall_success

async def run_orders_pipeline():
    """
    Run the orders pipeline.

    This pipeline pulls orders and order items for order#s 550-571,
    including any revisions in that range.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting orders pipeline")
    overall_success = True

    # Create a pipeline for orders
    orders_pipeline = (PipelineBuilder("orders_pipeline")
                      .add_acquisition(OrdersDataAcquisitionStage(start_id=550, end_id=571))
                      .add_batch_processor(BatchProcessor(OrderTransformer()))
                      .add_loading(CSVLoader("data_raw/orders/orders_550_571.csv"))
                      .build())

    # Verify orders pipeline completion
    orders_success = await verify_pipeline_completion(orders_pipeline, None, "orders_pipeline")
    if not orders_success:
        overall_success = False

    # Create a pipeline for order items
    if orders_success:
        # Get the order items from the context
        order_items = get_global_context("orders_pipeline", "order_items")

        if order_items:
            order_items_pipeline = (PipelineBuilder("order_items_pipeline")
                                  .add_batch_processor(BatchProcessor(OrderItemExtractor()))
                                  .add_loading(CSVLoader("data_raw/order_items/order_items_550_571.csv"))
                                  .build())

            # Verify order items pipeline completion
            order_items_success = await verify_pipeline_completion(order_items_pipeline, order_items, "order_items_pipeline")

            if order_items_success:
                logger.info("Order items pipeline completed successfully")
            else:
                logger.error("Order items pipeline failed")
                overall_success = False
        else:
            logger.warning("No order items found in context")
    else:
        logger.error("Orders pipeline failed, skipping order items pipeline")

    logger.info("Orders pipeline completed")
    return overall_success

async def run_accounts_pipeline():
    """
    Run the accounts pipeline.

    This pipeline pulls all accounts using the improved accounts acquisition stage
    with proper pagination handling and increased concurrency.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting accounts pipeline")
    start_time = time.time()

    # Create a pipeline for accounts using the improved accounts acquisition stage
    # with proper pagination handling and performance metrics
    accounts_pipeline = (PipelineBuilder("accounts_pipeline")
                        .add_acquisition(ImprovedAccountsDataAcquisitionStage(timeout=180))
                        # Increase max_concurrency to 10 for better performance
                        .add_batch_processor(BatchProcessor(AccountTransformer(), batch_size=100, max_concurrency=10))
                        .add_loading(CSVLoader("data_raw/accounts/accounts_all.csv"))
                        .build())

    # Verify accounts pipeline completion
    accounts_success = await verify_pipeline_completion(accounts_pipeline, None, "accounts_pipeline")

    # Calculate and log duration
    duration = time.time() - start_time
    logger.info(f"Accounts pipeline completed in {duration:.2f} seconds")

    # Alert on abnormal processing times
    if duration > 300:  # More than 5 minutes
        logger.warning(f"Accounts pipeline took {duration:.2f} seconds, which is longer than expected")

    if accounts_success:
        logger.info("Accounts pipeline completed successfully")
    else:
        logger.error("Accounts pipeline failed")

    return accounts_success

async def run_contacts_pipeline():
    """
    Run the contacts pipeline.

    This pipeline pulls all contacts using the new contacts acquisition stage
    with proper pagination handling and increased concurrency.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting contacts pipeline")
    start_time = time.time()

    # Create a pipeline for contacts using the new contacts acquisition stage
    # that has been tested to successfully fetch all contacts without timing out
    contacts_pipeline = (PipelineBuilder("contacts_pipeline")
                        .add_acquisition(NewContactsDataAcquisitionStage(timeout=180))
                        # Increase max_concurrency to 10 for better performance
                        .add_batch_processor(BatchProcessor(ContactTransformer(), batch_size=100, max_concurrency=10))
                        .add_loading(CSVLoader("data_raw/contacts/contacts_all.csv"))
                        .build())

    # Verify contacts pipeline completion
    contacts_success = await verify_pipeline_completion(contacts_pipeline, None, "contacts_pipeline")

    # Calculate and log duration
    duration = time.time() - start_time
    logger.info(f"Contacts pipeline completed in {duration:.2f} seconds")

    # Alert on abnormal processing times
    if duration > 300:  # More than 5 minutes
        logger.warning(f"Contacts pipeline took {duration:.2f} seconds, which is longer than expected")

    if contacts_success:
        logger.info("Contacts pipeline completed successfully")
    else:
        logger.error("Contacts pipeline failed")

    return contacts_success

async def run_users_pipeline():
    """
    Run the users pipeline.

    This pipeline pulls all users.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting users pipeline")

    # Create a pipeline for users
    users_pipeline = (PipelineBuilder("users_pipeline")
                     .add_acquisition(UsersDataAcquisitionStage())
                     .add_batch_processor(BatchProcessor(UserTransformer()))
                     .add_loading(CSVLoader("data_raw/users/users_all.csv"))
                     .build())

    # Verify users pipeline completion
    users_success = await verify_pipeline_completion(users_pipeline, None, "users_pipeline")

    if users_success:
        logger.info("Users pipeline completed successfully")
    else:
        logger.error("Users pipeline failed")

    logger.info("Users pipeline completed")
    return users_success

async def run_merged_data_pipeline():
    """
    Run the merged data pipeline.

    This pipeline merges the data from all the other pipelines and saves it to
    the data_real folder and S3.

    Returns:
        bool: True if the pipeline completed successfully, False otherwise
    """
    logger.info("Starting merged data pipeline")
    success = True

    try:
        # Get the S3 bucket name from environment variable
        s3_bucket_name = os.getenv("S3_BUCKET_NAME", "athena-paperless-csvs")

        # Define the files to copy to data_real and S3
        files_to_copy = [
            {
                "source": "data_raw/quotes/quotes_7900_7935.csv",
                "destination": "data_real/quotes.csv",
                "s3_key": "quotes/quotes_7900_7935.csv"
            },
            {
                "source": "data_raw/quote_items/quote_items_7900_7935.csv",
                "destination": "data_real/quote_items.csv",
                "s3_key": "quote_items/quote_items_7900_7935.csv"
            },
            {
                "source": "data_raw/orders/orders_550_571.csv",
                "destination": "data_real/orders.csv",
                "s3_key": "orders/orders_550_571.csv"
            },
            {
                "source": "data_raw/order_items/order_items_550_571.csv",
                "destination": "data_real/order_items.csv",
                "s3_key": "order_items/order_items_550_571.csv"
            },
            {
                "source": "data_raw/accounts/accounts_all.csv",
                "destination": "data_real/accounts.csv",
                "s3_key": "accounts/accounts_all.csv"
            },
            {
                "source": "data_raw/contacts/contacts_all.csv",
                "destination": "data_real/contacts.csv",
                "s3_key": "contacts/contacts_all.csv"
            },
            {
                "source": "data_raw/users/users_all.csv",
                "destination": "data_real/users.csv",
                "s3_key": "users/users_all.csv"
            }
        ]

        # Process each file
        for file_info in files_to_copy:
            source_path = file_info["source"]
            dest_path = file_info["destination"]
            s3_key = file_info["s3_key"]

            # Check if source file exists
            if not os.path.exists(source_path):
                logger.warning(f"Source file {source_path} does not exist, skipping")
                continue

            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Copy file to data_real
            with open(source_path, 'r') as source_file:
                data = source_file.read()
                with open(dest_path, 'w') as dest_file:
                    dest_file.write(data)

            logger.info(f"Copied {source_path} to {dest_path}")

            # Upload to S3
            try:
                # Read the CSV file
                with open(source_path, 'r') as f:
                    # Skip the header line
                    header = f.readline().strip().split(',')

                    # Read the rest of the lines
                    lines = f.readlines()

                    # Parse the CSV data
                    data = []
                    for line in lines:
                        values = line.strip().split(',')
                        row = {}
                        for i, key in enumerate(header):
                            if i < len(values):
                                row[key] = values[i]
                            else:
                                row[key] = ""
                        data.append(row)

                # Create an S3 loader
                s3_loader = S3Loader(
                    bucket_name=s3_bucket_name,
                    object_key=s3_key,
                    name=f"s3_loader_{os.path.basename(source_path)}"
                )

                # Upload to S3
                await s3_loader.load(data)

                logger.info(f"Uploaded {source_path} to S3 as {s3_key}")
            except Exception as e:
                logger.error(f"Error uploading {source_path} to S3: {str(e)}")
                success = False

        logger.info("Merged data pipeline completed successfully")
        return success
    except Exception as e:
        logger.error(f"Error in merged data pipeline: {str(e)}")
        return False

async def run_parallel_accounts_contacts_pipeline():
    """
    Run accounts and contacts pipelines in parallel.

    This function uses the ParallelStage class to process accounts and contacts
    in parallel, which can significantly improve performance.

    Returns:
        bool: True if both pipelines completed successfully, False otherwise
    """
    logger.info("Starting parallel accounts and contacts pipeline")
    start_time = time.time()

    # Create a parallel stage for accounts and contacts
    parallel_stage = ParallelStage("accounts_contacts_parallel")

    # Add the accounts acquisition stage with increased timeout
    accounts_acquisition = ImprovedAccountsDataAcquisitionStage(timeout=300)  # 5 minutes
    parallel_stage.add_stage("accounts", accounts_acquisition)

    # Add the contacts acquisition stage with increased timeout
    contacts_acquisition = NewContactsDataAcquisitionStage(timeout=300)  # 5 minutes
    parallel_stage.add_stage("contacts", contacts_acquisition)

    # Set a timeout for the entire parallel operation
    parallel_stage.set_timeout(600)  # 10 minutes

    # Create a pipeline for the parallel stage
    parallel_pipeline = (PipelineBuilder("accounts_contacts_parallel_pipeline")
                        .add_stage(parallel_stage)
                        .build())

    # Run the parallel pipeline
    try:
        result = await parallel_pipeline.run(None)

        # Extract accounts and contacts from the result
        accounts = result.get("accounts", [])
        contacts = result.get("contacts", [])

        logger.info(f"Parallel acquisition completed: {len(accounts)} accounts and {len(contacts)} contacts")

        # Process accounts in bulk using the new bulk transformation method
        if accounts:
            # Create an account transformer
            accounts_transformer = AccountTransformer(name="bulk_accounts_transformer")

            # Use the new transform_bulk method for better performance
            transform_start = time.time()
            transformed_accounts = await accounts_transformer.transform_bulk(accounts)
            transform_duration = time.time() - transform_start

            # Save accounts to CSV
            save_start = time.time()
            accounts_loader = CSVLoader("data_raw/accounts/accounts_all.csv")
            await accounts_loader.load(transformed_accounts)
            save_duration = time.time() - save_start

            logger.info(f"Transformed {len(transformed_accounts)} accounts in {transform_duration:.2f}s and saved in {save_duration:.2f}s")

        # Process contacts in bulk using the new bulk transformation method
        if contacts:
            # Create a contact transformer
            contacts_transformer = ContactTransformer(name="bulk_contacts_transformer")

            # Use the new transform_bulk method for better performance
            transform_start = time.time()
            transformed_contacts = await contacts_transformer.transform_bulk(contacts)
            transform_duration = time.time() - transform_start

            # Save contacts to CSV
            save_start = time.time()
            contacts_loader = CSVLoader("data_raw/contacts/contacts_all.csv")
            await contacts_loader.load(transformed_contacts)
            save_duration = time.time() - save_start

            logger.info(f"Transformed {len(transformed_contacts)} contacts in {transform_duration:.2f}s and saved in {save_duration:.2f}s")

        # Calculate and log duration
        duration = time.time() - start_time
        logger.info(f"Parallel accounts and contacts pipeline completed in {duration:.2f} seconds")

        # Alert on abnormal processing times
        if duration > 600:  # More than 10 minutes
            logger.warning(f"Parallel pipeline took {duration:.2f} seconds, which is longer than expected")

        return True
    except Exception as e:
        logger.error(f"Error in parallel accounts and contacts pipeline: {str(e)}")
        return False

async def main():
    """
    Main function to run all pipelines.
    """
    logger.info("Starting data pipeline")
    all_success = True

    try:
        # Run all pipelines and track their success
        quotes_success = await run_quotes_pipeline()
        if not quotes_success:
            all_success = False

        orders_success = await run_orders_pipeline()
        if not orders_success:
            all_success = False

        # Run accounts and contacts in parallel for better performance
        parallel_success = await run_parallel_accounts_contacts_pipeline()
        if not parallel_success:
            # Fallback to individual pipelines if parallel processing fails
            logger.warning("Parallel processing failed, falling back to individual pipelines")

            accounts_success = await run_accounts_pipeline()
            if not accounts_success:
                all_success = False

            contacts_success = await run_contacts_pipeline()
            if not contacts_success:
                all_success = False

        users_success = await run_users_pipeline()
        if not users_success:
            all_success = False

        # Run the merged data pipeline
        merged_success = await run_merged_data_pipeline()
        if not merged_success:
            all_success = False

        if all_success:
            logger.info("All pipelines completed successfully")
        else:
            logger.warning("Some pipelines failed or had issues")
    except Exception as e:
        logger.error(f"Error in data pipeline: {str(e)}")
        raise

    logger.info("Data pipeline completed")

if __name__ == "__main__":
    asyncio.run(main())
