import os
import pandas as pd
import logging
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
import psutil

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('merge_process.log'),
        logging.StreamHandler()
    ]
)

MERGE_CONFIG = [
    {
        "name": "quotes",
        "pattern": "quotes_*.csv",
        "input_dir": r"P:/WORK/PaperlessReporting/data_raw/quotes",
        "output_file": r"P:/WORK/PaperlessReporting/data_cleaned/quotes.csv"
    },
    {
        "name": "quote_items",
        "pattern": "quote_items_*.csv",
        "input_dir": r"P:/WORK/PaperlessReporting/data_raw/quote_items",
        "output_file": r"P:/WORK/PaperlessReporting/data_cleaned/quote_items.csv"
    },
    {
        "name": "orders",
        "pattern": "orders_*.csv",
        "input_dir": r"P:/WORK/PaperlessReporting/data_raw/orders",
        "output_file": r"P:/WORK/PaperlessReporting/data_cleaned/orders.csv"
    },
    {
        "name": "order_items",
        "pattern": "order_items_*.csv",
        "input_dir": r"P:/WORK/PaperlessReporting/data_raw/order_items",
        "output_file": r"P:/WORK/PaperlessReporting/data_cleaned/order_items.csv"
    }
]

def get_memory_usage():
    """Return current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def validate_dataframe(df, expected_columns=None):
    """Validate dataframe structure and content."""
    if expected_columns and set(df.columns) != set(expected_columns):
        raise ValueError(f"Column mismatch. Expected: {expected_columns}, Got: {df.columns}")
    return df

def process_file(file_path):
    """Process a single CSV file."""
    try:
        df = pd.read_csv(file_path, dtype=str)
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
        return df
    except Exception as e:
        logging.error(f"Failed to process {file_path}: {str(e)}")
        return None

def merge_table(config):
    """Merge CSV files according to configuration."""
    logging.info(f"Starting merge process for {config['name']}")
    raw_folder = Path(config["input_dir"])
    output_file = Path(config["output_file"])
    all_dfs = []
    
    # Get list of files
    files = list(raw_folder.glob(config["pattern"]))
    if not files:
        logging.warning(f"No files found for {config['name']}")
        return

    # Process files in parallel
    with ProcessPoolExecutor() as executor:
        results = list(tqdm(
            executor.map(process_file, files),
            total=len(files),
            desc=f"Processing {config['name']}"
        ))
    
    # Filter out None results and combine DataFrames
    all_dfs = [df for df in results if df is not None]
    
    if all_dfs:
        try:
            merged = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save merged data
            merged.to_csv(output_file, index=False)
            
            logging.info(f"Successfully merged {len(merged)} rows to {output_file}")
            logging.info(f"Memory usage: {get_memory_usage():.2f} MB")
        except Exception as e:
            logging.error(f"Failed to save merged file: {str(e)}")
    else:
        logging.warning(f"No valid data to merge for {config['name']}")

def main():
    logging.info("Starting merge process")
    for config in MERGE_CONFIG:
        merge_table(config)
    logging.info("Merge process completed")

if __name__ == "__main__":
    main()