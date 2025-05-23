# PaperlessReporting – Cursor Context

## What this repo does
- Python scripts under `scripts/` pull data (quotes, orders, quote_items, etc.) from the PaperlessParts API.
- Utilities in `scripts/utils/` merge batches of CSVs into cleaned outputs.
- A GitHub Actions CI pipeline (`.github/workflows/ci.yml`) lints, tests, and builds docs.
- Data lands in `data_raw/` then is consolidated in `data_cleaned/`.

## Key scripts
- `scripts/pull_quotes.py`, `pull_orders.py`, `pull_quote_items.py`  
  → each uses the same API-Token header, paginates/rate-limits, writes CSVs under `data_raw/`.
- `scripts/utils/merge_*.py`  
  → read all `*_*.csv` in `data_raw/…`, drop duplicates, output a single `data_cleaned/*.csv`.
- `scripts/utils/token_bucket.py`  
  → simple rate-limiter used by the pull scripts.

## Environment & config
- `config.json` holds `{ "api_key": "...", "api_base_url": "https://api.paperlessparts.com" }`
- CI relies on Python 3.9+, pytest for tests, flake8 for linting.

## Workflow
1. `git pull` latest.  
2. `python scripts/pull_quotes.py` (etc.) to regenerate raw CSVs.  
3. `python scripts/utils/merge_all_batches.py` to consolidate.  
4. Commit CSVs, push → CI runs and validates formatting + simple smoke tests.

## What you might ask Cursor
- “In `pull_quote_items.py`, how do I surface the root component correctly?”  
- “Add a new workflow that runs daily to fetch new orders.”  
- “Refactor `.utils/token_bucket` into an async version.”

