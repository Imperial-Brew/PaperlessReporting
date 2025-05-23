import os
import pandas as pd
from pathlib import Path

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


def merge_table(config):
    print(f"🔄 Merging {config['name']}...")
    raw_folder = Path(config["input_dir"])
    output_file = Path(config["output_file"])
    all_dfs = []

    for file in raw_folder.glob(config["pattern"]):
        try:
            df = pd.read_csv(file, dtype=str)
            df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)
            all_dfs.append(df)
        except Exception as e:
            print(f"❌ Failed to read {file.name}: {e}")

    if all_dfs:
        merged = pd.concat(all_dfs, ignore_index=True).drop_duplicates()
        output_file.parent.mkdir(parents=True, exist_ok=True)
        merged.to_csv(output_file, index=False)
        print(f"✅ Merged {len(merged)} rows to {output_file}")
    else:
        print(f"⚠️ No files found for {config['name']}.")


def main():
    for config in MERGE_CONFIG:
        merge_table(config)


if __name__ == "__main__":
    main()