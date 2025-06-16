import asyncio
import os
import json
import pandas as pd
from pathlib import Path

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
from scripts.pipeline.context_registry import set_global_context

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT_FILE = os.path.join(PROJECT_ROOT, "data_real", "quote_pipeline_checkpoint.json")


def load_checkpoint():
    try:
        if os.path.exists(CHECKPOINT_FILE):
            with open(CHECKPOINT_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading checkpoint: {e}")
    return {"last_processed_id": 7900}


def save_checkpoint(last_id):
    try:
        os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
        with open(CHECKPOINT_FILE, 'w') as f:
            json.dump({"last_processed_id": last_id}, f)
    except Exception as e:
        print(f"Error saving checkpoint: {e}")


class QuoteSplittingCSVLoader(CSVLoader):
    def __init__(self, quotes_path, items_path):
        super().__init__(quotes_path)
        self.file_path = None
        self.items_path = items_path

    async def load(self, data):
        if not data:
            return None

        quotes_data = []
        items_data = []

        for quote in data:
            # Extract quote items and remove them from the quote object
            quote_items = quote.pop('quote_items', [])
            # Remove quote-item specific fields from quote
            quote.pop('authenticated_pdf_quote_url', None)

            quotes_data.append(quote)

            # Add quote information to each item
            for item in quote_items:
                item['quote_number'] = quote.get('quote_number')
                items_data.append(item)

        # Save quotes to quotes CSV
        quotes_df = pd.DataFrame(quotes_data)
        quotes_df.to_csv(self.file_path, index=False)

        # Save items to items CSV
        if items_data:
            items_df = pd.DataFrame(items_data)
            items_df.to_csv(self.items_path, index=False)

        return data


async def run_pipeline():
    print("\n--- Running Quote Pipeline (7000-7950) ---")

    checkpoint = load_checkpoint()
    start_id = checkpoint["last_processed_id"]
    end_id = 7950

    print(f"Resuming from ID {start_id}")

    # Process in smaller chunks to avoid timeouts
    CHUNK_SIZE = 100
    current_start = start_id

    while current_start <= end_id:
        current_end = min(current_start + CHUNK_SIZE - 1, end_id)
        print(f"\nProcessing chunk {current_start}-{current_end}")

        quote_pipeline = (
            PipelineBuilder("quote_pipeline")
            .add_acquisition(PaperlessPartsDataAcquisitionStage(
                start_id=current_start,
                end_id=current_end
            ))
            .add_batch_processor(QuoteValidator())
            .add_batch_processor(QuoteTransformer())
            .add_loading(QuoteSplittingCSVLoader(
                quotes_path=os.path.join(PROJECT_ROOT, "data_real", f"quotes_{current_start}_{current_end}.csv"),
                items_path=os.path.join(PROJECT_ROOT, "data_real", f"quote_items_{current_start}_{current_end}.csv")
            ))
            .build()
        )

        quote_pipeline.stages[0].configure_timeout(timeout=300.0)

        try:
            print(f"Starting chunk execution...")
            quote_output = await quote_pipeline.run(None)
            print(f"Chunk completed successfully: {quote_output is not None}")

            # Save progress
            save_checkpoint(current_end)
            current_start = current_end + 1

        except asyncio.TimeoutError:
            print(f"Timeout occurred processing chunk {current_start}-{current_end}")
            await asyncio.sleep(30)  # Wait before retrying
            continue
        except Exception as e:
            print(f"Error processing chunk {current_start}-{current_end}: {e}")
            save_checkpoint(current_start - 1)
            raise

    # After all chunks are processed, merge the files
    try:
        merge_chunk_files(start_id, end_id)
    except Exception as e:
        print(f"Error merging files: {e}")


def merge_chunk_files(start_id, end_id):
    """Merge all chunk files into final CSVs"""
    data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
    quotes_dfs = []
    items_dfs = []
    chunk_size = 100

    for chunk_start in range(start_id, end_id + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, end_id)

        # Read quotes chunk
        quotes_file = os.path.join(data_real_dir, f"quotes_{chunk_start}_{chunk_end}.csv")
        if os.path.exists(quotes_file):
            try:
                quotes_dfs.append(pd.read_csv(quotes_file))
            except Exception as e:
                print(f"Error reading {quotes_file}: {e}")

        # Read items chunk
        items_file = os.path.join(data_real_dir, f"quote_items_{chunk_start}_{chunk_end}.csv")
        if os.path.exists(items_file):
            try:
                items_dfs.append(pd.read_csv(items_file))
            except Exception as e:
                print(f"Error reading {items_file}: {e}")

    # Merge and save quotes
    if quotes_dfs:
        combined_quotes = pd.concat(quotes_dfs, ignore_index=True)
        combined_quotes.to_csv(os.path.join(data_real_dir, "quotes_complete.csv"), index=False)
        print("Created combined quotes file")

    # Merge and save items
    if items_dfs:
        combined_items = pd.concat(items_dfs, ignore_index=True)
        combined_items.to_csv(os.path.join(data_real_dir, "quote_items_complete.csv"), index=False)
        print("Created combined quote items file")


async def main():
    try:
        # Ensure data_real directory exists
        data_real_dir = os.path.join(PROJECT_ROOT, "data_real")
        os.makedirs(data_real_dir, exist_ok=True)

        await run_pipeline()

    except asyncio.CancelledError:
        print("Pipeline execution was cancelled")
    except Exception as e:
        print(f"Error in main execution: {e}")


if __name__ == "__main__":
    asyncio.run(main())