import os
import pandas as pd
from pathlib import Path

RAW_FOLDER = Path(r"P:/WORK/PaperlessReporting/data_raw/orders")
OUTPUT_FILE = Path(r"P:/WORK/PaperlessReporting/data_cleaned/orders.csv")


def merge_batches():
    all_dfs = []
    for file in RAW_FOLDER.glob("orders_*.csv"):
        try:
            # Force all to str and trim whitespace to normalize duplicates
            df = pd.read_csv(file, dtype=str).apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            all_dfs.append(df)
        except Exception as e:
            print(f"❌ Failed to read {file.name}: {e}")

    if all_dfs:
        merged = pd.concat(all_dfs, ignore_index=True)
        merged = merged.drop_duplicates()
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Merged {len(merged)} unique orders to {OUTPUT_FILE}")
    else:
        print("⚠️ No order files found.")


if __name__ == "__main__":
    merge_batches()
