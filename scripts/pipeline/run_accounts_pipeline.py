import asyncio
import os
import json
import pandas as pd
from pathlib import Path
import sys
import logging
from scripts.utils.logging_config import get_logger

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.processors import (
    ImprovedAccountsDataAcquisitionStage,
    AccountTransformer,
    CSVLoader,
    AccountValidator
)

# Initialize logger
logger = get_logger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT_FILE = os.path.join(PROJECT_ROOT, "data_real", "account_pipeline_checkpoint.json")


def load_checkpoint():
    """
    Load the checkpoint file to determine processing status.

    Returns:
        dict: Checkpoint data with processing status
    """
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading checkpoint: {e}")
    return {"last_processed": False}


def save_checkpoint(processed=True):
    """
    Save the current processing status to the checkpoint file.

    Args:
        processed (bool): Whether processing has completed successfully
    """
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump({"last_processed": processed}, f)
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")


class AccountSplittingCSVLoader(CSVLoader):
    """
    Custom CSV loader that saves account data to a CSV file.

    This loader processes account data and saves it to a CSV file
    for downstream analysis and reporting.

    Args:
        accounts_path (str): Path to save the accounts CSV file
    """
    def __init__(self, accounts_path):
        super().__init__(accounts_path)
        self.file_path = accounts_path
        self.logger = get_logger(__name__)

    async def load(self, data):
        """
        Load account data to a CSV file.

        Args:
            data (List[Dict]): List of account dictionaries

        Returns:
            List[Dict]: The original data if successful, None otherwise
        """
        if not data:
            self.logger.warning("AccountSplittingCSVLoader received empty data")
            self.record_metric("empty_input", True)
            return None

        self.logger.info(f"Processing {len(data)} accounts for CSV export")
        self.record_metric("input_count", len(data))

        accounts_data = []

        for account in data:
            accounts_data.append(account)

        # Save accounts to CSV
        try:
            accounts_df = pd.DataFrame(accounts_data)
            accounts_df.to_csv(self.file_path, index=False)
            self.logger.info(f"Saved {len(accounts_data)} accounts to {self.file_path}")

            # Log column names for diagnostic purposes
            self.record_metric("accounts_columns", list(accounts_df.columns))
            self.logger.debug(f"Accounts CSV columns: {list(accounts_df.columns)}")
        except Exception as e:
            self.logger.error(f"Error saving accounts CSV: {str(e)}")
            self.record_metric("accounts_save_error", str(e))
            raise

        return data


async def run_pipeline():
    """
    Run the accounts pipeline.

    This function processes all accounts from the Paperless Parts API and 
    saves them to a CSV file. It includes checkpoint functionality to track 
    processing status and avoid reprocessing data unnecessarily.

    Returns:
        bool: True if pipeline executed successfully, False otherwise
    """
    logger.info("Running Accounts Pipeline")

    checkpoint = load_checkpoint()
    already_processed = checkpoint.get("last_processed", False)

    if already_processed:
        logger.info("Accounts have already been processed. To reprocess, delete the checkpoint file.")
        return False

    logger.info("Starting accounts processing")

    accounts_pipeline = (
        PipelineBuilder("accounts_pipeline")
        .add_acquisition(ImprovedAccountsDataAcquisitionStage())
        .add_batch_processor(AccountValidator())
        .add_batch_processor(AccountTransformer())
        .add_loading(AccountSplittingCSVLoader(
            accounts_path=os.path.join(PROJECT_ROOT, "data_real", "accounts_complete.csv")
        ))
        .build()
    )

    # Configure timeout for the acquisition stage
    accounts_pipeline.stages[0].configure_timeout(timeout=300.0)

    try:
        logger.info("Starting pipeline execution")
        accounts_output = await accounts_pipeline.run(None)
        success = accounts_output is not None
        logger.info(f"Pipeline completed successfully: {success}")

        # Save progress
        save_checkpoint(True)
        return success

    except asyncio.TimeoutError:
        logger.error("Timeout occurred processing accounts")
        await asyncio.sleep(30)  # Wait before retrying
        return False
    except Exception as e:
        logger.error(f"Error processing accounts: {e}", exc_info=True)
        raise


async def main():
    """
    Main entry point for the accounts pipeline script.

    This function handles the setup of directories and provides top-level
    error handling for the pipeline execution. It ensures the data_real
    directory exists before running the pipeline.

    Returns:
        int: 0 for success, 1 for failure
    """
    try:
        # Ensure data_real directory exists
        data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
        os.makedirs(data_real_dir, exist_ok=True)
        logger.info(f"Ensured data directory exists: {data_real_dir}")

        success = await run_pipeline()
        return 0 if success else 1

    except asyncio.CancelledError:
        logger.warning("Pipeline execution was cancelled")
        return 1
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    asyncio.run(main())
