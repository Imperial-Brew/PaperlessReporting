"""
Incremental processing for the pipeline framework.

This module provides components for incremental processing, allowing
the pipeline to process only new or changed data since the last run.
"""

import os
import json
import csv
import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pathlib import Path

from scripts.pipeline.processors import PaperlessPartsDataAcquisitionStage
from scripts.pipeline.exceptions import DataAcquisitionError


class IncrementalDataAcquisitionStage(PaperlessPartsDataAcquisitionStage):
    """
    Data acquisition stage for fetching only new or changed quotes from the Paperless Parts API.

    This stage extends PaperlessPartsDataAcquisitionStage to add incremental processing
    capabilities, allowing it to fetch only quotes that are new or have changed since
    the last run.
    """

    def __init__(self, 
                 start_id: Optional[int] = None, 
                 end_id: Optional[int] = None,
                 include_revisions: bool = True, 
                 state_file: Optional[str] = None,
                 name: str = "incremental_acquisition",
                 output_dir: str = "data_real"):
        """
        Initialize the incremental data acquisition stage.

        Args:
            start_id: Starting quote ID
            end_id: Ending quote ID
            include_revisions: Whether to include revised quotes
            state_file: Path to the state file for tracking processed quotes
            name: Name of the stage
            output_dir: Directory to save output files (default: "data_real")
        """
        super().__init__(
            start_id=start_id,
            end_id=end_id,
            include_revisions=include_revisions,
            name=name,
            output_dir=output_dir
        )
        self.state_file = state_file or "pipeline_state.json"
        self.processed_quotes = set()
        self.processed_revisions = set()
        self.load_state()

    def load_state(self) -> None:
        """
        Load the state from the state file.

        This method loads the set of processed quote IDs and revisions from
        the state file, if it exists.
        """
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.processed_quotes = set(state.get("processed_quotes", []))
                    self.processed_revisions = set(tuple(r) for r in state.get("processed_revisions", []))
                    self.record_metric("state_loaded", True)
                    self.record_metric("processed_quotes_count", len(self.processed_quotes))
                    self.record_metric("processed_revisions_count", len(self.processed_revisions))
            except Exception as e:
                self.record_metric("state_loaded", False)
                self.record_metric("state_load_error", str(e))

    def save_state(self) -> None:
        """
        Save the state to the state file.

        This method saves the set of processed quote IDs and revisions to
        the state file.
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)

            # Save the state
            with open(self.state_file, 'w') as f:
                state = {
                    "processed_quotes": list(self.processed_quotes),
                    "processed_revisions": [list(r) for r in self.processed_revisions],
                    "last_updated": datetime.datetime.now().isoformat()
                }
                json.dump(state, f, indent=2)
                self.record_metric("state_saved", True)
        except Exception as e:
            self.record_metric("state_saved", False)
            self.record_metric("state_save_error", str(e))

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch only new or changed quotes from the Paperless Parts API.

        This method extends the base acquire method to filter out quotes
        that have already been processed.

        Returns:
            List of quote dictionaries
        """
        from scripts.pull_quotes_async import QuotesPuller

        # Create a puller instance
        puller = QuotesPuller(
            start_id=self.start_id,
            end_id=self.end_id,
            include_revisions=self.include_revisions,
            output_dir=self.output_dir
        )

        # Override the save_to_csv method to return data instead of saving it
        quotes = []

        original_save_to_csv = puller.save_to_csv

        def collect_quotes(items, _):
            nonlocal quotes
            quotes.extend(items)
            self.record_metric("quotes_fetched", len(items))

        puller.save_to_csv = collect_quotes

        # Run the puller
        await puller.run()

        # Restore the original method
        puller.save_to_csv = original_save_to_csv

        # Filter out quotes that have already been processed
        new_quotes = []
        for quote in quotes:
            quote_number = quote.get("quote_number")
            revision_number = quote.get("revision_number")

            if quote_number is None:
                continue

            # Check if this is a new quote or a new revision
            is_new = False

            if revision_number is not None:
                # This is a revised quote
                revision_key = (quote_number, revision_number)
                if revision_key not in self.processed_revisions:
                    is_new = True
                    self.processed_revisions.add(revision_key)
            else:
                # This is a regular quote
                if quote_number not in self.processed_quotes:
                    is_new = True
                    self.processed_quotes.add(quote_number)

            if is_new:
                new_quotes.append(quote)

        # Record metrics
        self.record_metric("total_quotes", len(quotes))
        self.record_metric("new_quotes", len(new_quotes))
        self.record_metric("quote_items", len(puller.quote_items))

        # Store quote items in context for later stages
        self.set_context("quote_items", puller.quote_items)

        # Save the updated state
        self.save_state()

        return new_quotes


class IncrementalCSVLoader:
    """
    Utility for loading and comparing CSV data for incremental processing.

    This class provides methods for loading CSV data and comparing it with
    new data to identify changes.
    """

    @staticmethod
    def load_csv(file_path: str) -> List[Dict[str, Any]]:
        """
        Load data from a CSV file.

        Args:
            file_path: Path to the CSV file

        Returns:
            List of dictionaries representing the CSV rows
        """
        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except Exception:
            return []

    @staticmethod
    def find_changes(existing_data: List[Dict[str, Any]], 
                    new_data: List[Dict[str, Any]], 
                    key_field: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Find changes between existing and new data.

        Args:
            existing_data: List of dictionaries representing existing data
            new_data: List of dictionaries representing new data
            key_field: Field to use as the key for comparison

        Returns:
            Tuple of (added, updated, unchanged) items
        """
        existing_dict = {item.get(key_field): item for item in existing_data if item.get(key_field)}
        new_dict = {item.get(key_field): item for item in new_data if item.get(key_field)}

        added = []
        updated = []
        unchanged = []

        for key, new_item in new_dict.items():
            if key not in existing_dict:
                added.append(new_item)
            elif new_item != existing_dict[key]:
                updated.append(new_item)
            else:
                unchanged.append(new_item)

        return added, updated, unchanged
