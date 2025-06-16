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
    PaperlessPartsDataAcquisitionStage,
    QuoteTransformer,
    QuoteItemTransformer,
    CSVLoader
)
from scripts.pipeline.validators import (
    QuoteValidator,
    QuoteItemValidator,
)

# Initialize logger
logger = get_logger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT_FILE = os.path.join(PROJECT_ROOT, "data_real", "quote_pipeline_7900_7950_checkpoint.json")


def load_checkpoint():
    """
    Load the checkpoint file to determine the last processed quote ID.

    Returns:
        dict: Checkpoint data with last processed ID
    """
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading checkpoint: {e}")
    return {"last_processed_id": 7000}


def save_checkpoint(last_id):
    """
    Save the current processing status to the checkpoint file.

    Args:
        last_id (int): The last successfully processed quote ID
    """
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump({"last_processed_id": last_id}, f)
    except Exception as e:
        logger.error(f"Error saving checkpoint: {e}")


class QuoteSplittingCSVLoader(CSVLoader):
    """
    Custom CSV loader that splits quote data into separate quote and quote items files.

    This loader processes quote data and saves it to separate CSV files for quotes
    and quote items for downstream analysis and reporting.

    Args:
        quotes_path (str): Path to save the quotes CSV file
        items_path (str): Path to save the quote items CSV file
    """
    def __init__(self, quotes_path, items_path):
        super().__init__(quotes_path)
        self.file_path = quotes_path
        self.items_path = items_path
        self.logger = get_logger(__name__)

    async def load(self, data):
        """
        Load quote data by splitting into quotes and quote items files.

        Args:
            data (List[Dict]): List of quote dictionaries with nested quote_items

        Returns:
            List[Dict]: The original data if successful, None otherwise
        """
        if not data:
            self.logger.warning("QuoteSplittingCSVLoader received empty data")
            self.record_metric("empty_input", True)
            return None

        self.logger.info(f"Processing {len(data)} quotes for CSV export")
        self.record_metric("input_count", len(data))

        quotes_data = []
        items_data = []
        quote_items_count = 0

        for quote in data:
            # Extract quote items and remove them from the quote object
            quote_items = quote.pop('quote_items', [])
            # Remove quote-item specific fields from quote
            quote.pop('authenticated_pdf_quote_url', None)

            quotes_data.append(quote)

            if quote_items:
                quote_items_count += len(quote_items)
                self.logger.debug(f"Quote {quote.get('quote_number')} has {len(quote_items)} items")
            else:
                self.logger.debug(f"Quote {quote.get('quote_number')} has no items")

            # Add quote information to each item
            for item in quote_items:
                item['quote_number'] = quote.get('quote_number')
                items_data.append(item)

        self.record_metric("quotes_count", len(quotes_data))
        self.record_metric("items_count", len(items_data))

        # Save quotes to quotes CSV
        try:
            quotes_df = pd.DataFrame(quotes_data)
            quotes_df.to_csv(self.file_path, index=False)
            self.logger.info(f"Saved {len(quotes_data)} quotes to {self.file_path}")

            # Log column names for diagnostic purposes
            self.record_metric("quotes_columns", list(quotes_df.columns))
            self.logger.debug(f"Quotes CSV columns: {list(quotes_df.columns)}")
        except Exception as e:
            self.logger.error(f"Error saving quotes CSV: {str(e)}")
            self.record_metric("quotes_save_error", str(e))
            raise

        # Save items to items CSV
        if items_data:
            try:
                items_df = pd.DataFrame(items_data)
                items_df.to_csv(self.items_path, index=False)
                self.logger.info(f"Saved {len(items_data)} quote items to {self.items_path}")

                # Log column names for diagnostic purposes
                self.record_metric("items_columns", list(items_df.columns))
                self.logger.debug(f"Quote items CSV columns: {list(items_df.columns)}")
            except Exception as e:
                self.logger.error(f"Error saving quote items CSV: {str(e)}")
                self.record_metric("items_save_error", str(e))
                raise
        else:
            self.logger.warning("No quote items to save")

        return data


async def run_pipeline():
    """
    Run the quote pipeline for quotes 7900-7950.

    This function processes quotes in chunks to avoid timeouts and includes
    checkpoint functionality to resume processing if interrupted. It fetches
    quotes from the Paperless Parts API, validates and transforms them, and
    saves them to CSV files.

    Returns:
        bool: True if pipeline executed successfully, False otherwise
    """
    logger.info("Running Quote Pipeline (7900-7950)")

    checkpoint = load_checkpoint()
    start_id = checkpoint["last_processed_id"]
    end_id = 7950

    logger.info(f"Resuming from ID {start_id}")

    # Process in smaller chunks to avoid timeouts
    CHUNK_SIZE = 50
    current_start = start_id

    while current_start <= end_id:
        current_end = min(current_start + CHUNK_SIZE - 1, end_id)
        logger.info(f"Processing chunk {current_start}-{current_end}")

        quote_pipeline = (
            PipelineBuilder("quote_pipeline")
            .add_acquisition(PaperlessPartsDataAcquisitionStage(
                start_id=current_start,
                end_id=current_end
            ))
            .add_batch_processor(QuoteValidator())
            .add_batch_processor(QuoteTransformer())
            .add_loading(QuoteSplittingCSVLoader(
                quotes_path=os.path.join(PROJECT_ROOT, "data_real", "quotes", f"quotes_{current_start}_{current_end}.csv"),
                items_path=os.path.join(PROJECT_ROOT, "data_real", "quote_items", f"quote_items_{current_start}_{current_end}.csv")
            ))
            .build()
        )

        quote_pipeline.stages[0].configure_timeout(timeout=300.0)

        try:
            logger.info("Starting chunk execution")
            quote_output = await quote_pipeline.run(None)
            success = quote_output is not None
            logger.info(f"Chunk completed successfully: {success}")

            # Save progress
            save_checkpoint(current_end)
            current_start = current_end + 1

        except asyncio.TimeoutError:
            logger.error(f"Timeout occurred processing chunk {current_start}-{current_end}")
            await asyncio.sleep(30)  # Wait before retrying
            continue
        except Exception as e:
            logger.error(f"Error processing chunk {current_start}-{current_end}: {e}", exc_info=True)
            save_checkpoint(current_start - 1)
            raise

    # After all chunks are processed, merge the files
    try:
        success = merge_chunk_files(start_id, end_id)
        return success
    except Exception as e:
        logger.error(f"Error merging files: {e}", exc_info=True)
        return False


def merge_chunk_files(start_id, end_id):
    """
    Merge all chunk files into final CSVs.

    This function combines all the individual chunk CSV files into
    consolidated files for quotes and quote items. It handles empty
    files and missing data gracefully.

    Args:
        start_id (int): The starting quote ID
        end_id (int): The ending quote ID

    Returns:
        bool: True if merging was successful, False otherwise
    """
    data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
    quotes_dfs = []
    items_dfs = []
    chunk_size = 50

    logger.info(f"Merging chunk files from quote ID {start_id} to {end_id}")

    for chunk_start in range(start_id, end_id + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, end_id)

        # Read quotes chunk
        quotes_file = os.path.join(data_real_dir, "quotes", f"quotes_{chunk_start}_{chunk_end}.csv")
        if os.path.exists(quotes_file):
            try:
                df = pd.read_csv(quotes_file)
                quotes_dfs.append(df)
                logger.debug(f"Added quotes file: {quotes_file} with {len(df)} records")
            except Exception as e:
                logger.error(f"Error reading {quotes_file}: {e}")

        # Read items chunk
        items_file = os.path.join(data_real_dir, "quote_items", f"quote_items_{chunk_start}_{chunk_end}.csv")
        if os.path.exists(items_file):
            try:
                df = pd.read_csv(items_file)
                items_dfs.append(df)
                logger.debug(f"Added quote items file: {items_file} with {len(df)} records")
            except Exception as e:
                logger.error(f"Error reading {items_file}: {e}")

    # Merge and save quotes
    if quotes_dfs:
        combined_quotes = pd.concat(quotes_dfs, ignore_index=True)
        output_file = os.path.join(data_real_dir, "quotes", "quotes_7900_7950_complete.csv")
        combined_quotes.to_csv(output_file, index=False)
        logger.info(f"Created combined quotes file with {len(combined_quotes)} records at {output_file}")
    else:
        logger.warning("No quote files found to merge")

    # Merge and save items
    logger.info(f"Found {len(items_dfs)} quote item files to merge")
    if items_dfs:
        combined_items = pd.concat(items_dfs, ignore_index=True)
        output_file = os.path.join(data_real_dir, "quote_items", "quote_items_7900_7950_complete.csv")
        combined_items.to_csv(output_file, index=False)
        logger.info(f"Created combined quote items file with {len(combined_items)} records at {output_file}")
    else:
        logger.warning("No quote item files found to merge")
        # Create an empty file to ensure it exists
        output_file = os.path.join(data_real_dir, "quote_items", "quote_items_7900_7950_complete.csv")
        pd.DataFrame().to_csv(output_file, index=False)
        logger.info(f"Created empty quote items file at {output_file}")

    return True


async def main():
    """
    Main entry point for the quote pipeline script.

    This function handles the setup of directories and provides top-level
    error handling for the pipeline execution. It ensures the data_real
    directory and its subdirectories exist before running the pipeline.

    Returns:
        int: 0 for success, 1 for failure
    """
    try:
        # Ensure data_real directory and subdirectories exist
        data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
        quotes_dir = os.path.join(data_real_dir, "quotes")
        quote_items_dir = os.path.join(data_real_dir, "quote_items")

        os.makedirs(data_real_dir, exist_ok=True)
        os.makedirs(quotes_dir, exist_ok=True)
        os.makedirs(quote_items_dir, exist_ok=True)
        logger.info(f"Ensured data directories exist: {data_real_dir}, {quotes_dir}, {quote_items_dir}")

        # Clean up old files in data_real directory if they exist
        # Remove complete files
        old_quotes_file = os.path.join(data_real_dir, "quotes_7900_7950_complete.csv")
        old_items_file = os.path.join(data_real_dir, "quote_items_7900_7950_complete.csv")

        if os.path.exists(old_quotes_file):
            os.remove(old_quotes_file)
            logger.info(f"Removed old quotes file from data_real directory: {old_quotes_file}")

        if os.path.exists(old_items_file):
            os.remove(old_items_file)
            logger.info(f"Removed old items file from data_real directory: {old_items_file}")

        # Remove chunk files
        for file in os.listdir(data_real_dir):
            if file.startswith("quotes_") and file.endswith(".csv") and not os.path.isdir(os.path.join(data_real_dir, file)):
                os.remove(os.path.join(data_real_dir, file))
                logger.info(f"Removed old quotes chunk file from data_real directory: {file}")
            elif file.startswith("quote_items_") and file.endswith(".csv") and not os.path.isdir(os.path.join(data_real_dir, file)):
                os.remove(os.path.join(data_real_dir, file))
                logger.info(f"Removed old quote items chunk file from data_real directory: {file}")

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
