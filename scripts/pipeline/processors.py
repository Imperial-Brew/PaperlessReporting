"""
Data processors for the pipeline framework.

This module provides processors for transforming and enriching data
as it flows through the pipeline.
"""

import csv
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic, Tuple
from pathlib import Path
from scripts.pipeline.base import PipelineStage, DataAcquisitionStage, TransformationStage, LoadingStage
from scripts.pipeline.exceptions import TransformationError, LoadingError, PipelineError

# Type variables for generic stages
T = TypeVar('T')
U = TypeVar('U')
V = TypeVar('V')  # Additional type variable for ParallelStage


class QuoteTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for quote data.

    This transformer processes raw quote data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "quote_transformer"):
        """
        Initialize the quote transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform quote data.

        Args:
            data: Raw quote data to transform

        Returns:
            Transformed quote data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "quote_number": data.get("number") or data.get("quote_number", ""),
                "revision_number": data.get("revision_number") or data.get("revision", 0),
                "status": data.get("status", ""),
                "created": data.get("created", ""),
                "due_date": data.get("due_date", ""),
                "sent_date": data.get("sent_date", ""),
                "expired_date": data.get("expired_date", ""),
                "expired": data.get("expired", False),
                "rfq_number": data.get("rfq_number", ""),
                "priority": data.get("priority", ""),
                "private_notes": data.get("private_notes", ""),
                "authenticated_pdf_quote_url": data.get("authenticated_pdf_quote_url", ""),
            }

            # Extract contact information
            contact = data.get("contact", {})
            if contact:
                transformed["contact_name"] = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
                transformed["contact_email"] = contact.get("email", "")

                # Extract customer information
                account = contact.get("account", {})
                if account:
                    transformed["customer_name"] = account.get("name", "")

            # Extract estimator information
            estimator = data.get("estimator", {})
            if estimator:
                transformed["estimator_email"] = estimator.get("email", "")

            # Extract salesperson information
            salesperson = data.get("salesperson", {})
            if salesperson:
                transformed["salesperson_email"] = salesperson.get("email", "")

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming quote data: {str(e)}", data=data)


class QuoteItemTransformer(TransformationStage[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Transformer for quote item data.

    This transformer extracts quote items from a quote and transforms
    them into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "quote_item_transformer"):
        """
        Initialize the quote item transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform quote item data.

        Args:
            data: Quote data containing quote items

        Returns:
            List of transformed quote items
        """
        try:
            quote_items = []

            # Extract quote number and revision
            quote_number = data.get("number") or data.get("quote_number", "")
            revision_number = data.get("revision_number") or data.get("revision", 0)

            # Process quote items if they exist
            raw_items = data.get("quote_items", [])
            if not isinstance(raw_items, list):
                self.record_metric("quote_items_count", 0)
                return quote_items

            self.record_metric("quote_items_count", len(raw_items))

            for item in raw_items:
                # Extract the root component
                components = item.get("components", [])
                root = next((c for c in components if c.get("is_root_component")), {})

                # Create base row with common fields
                base_item = {
                    "quote_number": str(quote_number),  # Convert to string
                    "quote_revision": revision_number,
                    "item_id": item.get("id", ""),
                    "workflow_status": item.get("workflow_status", ""),
                    "part_number": root.get("part_number", ""),
                    "revision": root.get("revision", ""),
                    "description": root.get("description", ""),
                    "type": root.get("type", ""),
                    "material": root.get("material", {}).get("name", "") if root.get("material") else "",
                    "process": root.get("process", {}).get("name", "") if root.get("process") else "",
                    "is_fully_configured": all([
                        root.get("part_number"),
                        root.get("description"),
                        root.get("material", {}).get("name") if root.get("material") else "",
                        root.get("process", {}).get("name") if root.get("process") else ""
                    ]),
                    "part_uuid": root.get("part_uuid", ""),
                    "export_controlled": item.get("export_controlled", False)
                }

                # Handle quantities - each quantity creates a separate row
                quantities = root.get("quantities", [])
                if quantities:
                    for q in quantities:
                        item_with_quantity = base_item.copy()
                        # Convert numeric fields to appropriate types
                        try:
                            unit_price = float(q.get("unit_price", 0))
                            total_price = float(q.get("total_price", 0))
                            total_price_with_add_ons = float(q.get("total_price_with_required_add_ons", 0))
                        except (ValueError, TypeError):
                            # If conversion fails, use default values
                            unit_price = 0.0
                            total_price = 0.0
                            total_price_with_add_ons = 0.0

                        item_with_quantity.update({
                            "quantity": q.get("quantity", 0),
                            "unit_price": unit_price,
                            "total_price": total_price,
                            "total_price_with_add_ons": total_price_with_add_ons,
                            "lead_time": q.get("lead_time", "")
                        })
                        quote_items.append(item_with_quantity)
                else:
                    # If no quantities, still add the base row
                    quote_items.append(base_item)

            # Record metrics
            self.record_metric("transformation_success", True)

            return quote_items
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming quote item data: {str(e)}", data=data)


class CSVLoader(LoadingStage[List[Dict[str, Any]]]):
    """
    Loader for saving data to CSV files.

    This loader saves a list of dictionaries to a CSV file.
    """

    def __init__(self, output_path: str, name: str = "csv_loader"):
        """
        Initialize the CSV loader.

        Args:
            output_path: Path to the output CSV file
            name: Name of the loader
        """
        super().__init__(name)
        self.output_path = output_path

    async def load(self, data: List[Dict[str, Any]]) -> None:
        """
        Load data to a CSV file.

        Args:
            data: List of dictionaries to save
        """
        try:
            if not data:
                self.record_metric("rows_written", 0)
                return

            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Get fieldnames from the first item
            fieldnames = list(data[0].keys())

            # Write to CSV
            with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)

            # Record metrics
            self.record_metric("rows_written", len(data))
            self.record_metric("output_path", self.output_path)
            self.record_metric("loading_success", True)
        except Exception as e:
            # Record metrics
            self.record_metric("loading_success", False)
            self.record_metric("loading_error", str(e))

            # Raise a LoadingError
            raise LoadingError(f"Error loading data to CSV: {str(e)}", data=data, destination=self.output_path)


class JSONLoader(LoadingStage[Dict[str, Any]]):
    """
    Loader for saving data to JSON files.

    This loader saves a dictionary to a JSON file.
    """

    def __init__(self, output_path: str, name: str = "json_loader"):
        """
        Initialize the JSON loader.

        Args:
            output_path: Path to the output JSON file
            name: Name of the loader
        """
        super().__init__(name)
        self.output_path = output_path

    async def load(self, data: Dict[str, Any]) -> None:
        """
        Load data to a JSON file.

        Args:
            data: Dictionary to save
        """
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Write to JSON
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            # Record metrics
            self.record_metric("output_path", self.output_path)
            self.record_metric("loading_success", True)
        except Exception as e:
            # Record metrics
            self.record_metric("loading_success", False)
            self.record_metric("loading_error", str(e))

            # Raise a LoadingError
            raise LoadingError(f"Error loading data to JSON: {str(e)}", data=data, destination=self.output_path)


class BatchProcessor(PipelineStage[List[T], List[U]]):
    """
    Pipeline stage that processes a batch of items using another stage.

    This stage takes a list of items, processes each one with the provided
    stage, and returns a list of results. It supports parallel processing
    using asyncio.gather to process multiple items concurrently.
    """

    def __init__(self, stage: PipelineStage[T, U], name: str = None, 
                 batch_size: int = 100, max_concurrency: int = 5):
        """
        Initialize the batch processor.

        Args:
            stage: Stage to use for processing each item
            name: Name of the stage (defaults to f"batch_{stage.name}")
            batch_size: Maximum number of items to process in a single batch
            max_concurrency: Maximum number of items to process concurrently
        """
        super().__init__(name or f"batch_{stage.name}")
        self.stage = stage
        self.configure_batch_processing(batch_size=batch_size, parallel_workers=max_concurrency)

    async def process_core(self, data: List[T]) -> List[U]:
        """
        Process each item in the batch, with support for parallel processing.

        This method processes items in parallel using asyncio.gather, with
        the level of parallelism controlled by the configured batch_size and
        parallel_workers settings.

        Args:
            data: List of items to process

        Returns:
            List of processed items
        """
        results = []
        errors = []

        # Process items in batches with parallel execution
        for i in range(0, len(data), self._batch_size):
            batch = data[i:i + self._batch_size]

            # Create tasks for parallel processing
            tasks = []
            for item in batch:
                tasks.append(self.stage.process(item))

            # Use asyncio.gather to run tasks in parallel
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and handle exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    item_index = i + j
                    errors.append((item_index, batch[j], str(result)))
                else:
                    results.append(result)

        # Record metrics
        self.record_metric("total_items", len(data))
        self.record_metric("successful_items", len(results))
        self.record_metric("failed_items", len(errors))
        self.record_metric("batch_size", self._batch_size)
        self.record_metric("max_concurrency", self._parallel_workers)

        if errors:
            self.record_metric("errors", errors)

        return results


class ParallelStage(PipelineStage[T, Dict[str, Any]]):
    """
    Pipeline stage that runs multiple stages concurrently.

    This stage takes input data and processes it through multiple stages
    in parallel, returning a dictionary with the results from each stage.
    Each stage is run independently, and the results are combined into
    a dictionary with the stage names as keys.
    """

    def __init__(self, name: str = "parallel_stage"):
        """
        Initialize the parallel stage.

        Args:
            name: Name of the stage
        """
        super().__init__(name)
        self.stages: Dict[str, PipelineStage] = {}
        self.timeout = 60.0  # Default timeout for parallel execution

    def add_stage(self, name: str, stage: PipelineStage) -> 'ParallelStage':
        """
        Add a stage to be run in parallel.

        Args:
            name: Name to use as the key in the results dictionary
            stage: Pipeline stage to add

        Returns:
            The ParallelStage instance for method chaining
        """
        self.stages[name] = stage
        return self

    def set_timeout(self, timeout: float) -> 'ParallelStage':
        """
        Set the timeout for parallel execution.

        Args:
            timeout: Timeout in seconds

        Returns:
            The ParallelStage instance for method chaining
        """
        self.timeout = timeout
        return self

    async def process_core(self, data: T) -> Dict[str, Any]:
        """
        Process the input data through all stages in parallel.

        Args:
            data: Input data to process

        Returns:
            Dictionary with results from each stage, keyed by stage name
        """
        if not self.stages:
            return {}

        # Create tasks for each stage
        tasks = {}
        for name, stage in self.stages.items():
            tasks[name] = asyncio.create_task(stage.process(data))

        # Wait for all tasks to complete or timeout
        try:
            # Use asyncio.wait with timeout
            done, pending = await asyncio.wait(
                tasks.values(),
                timeout=self.timeout,
                return_when=asyncio.ALL_COMPLETED
            )

            # Cancel any pending tasks
            for task in pending:
                task.cancel()

            # Collect results
            results = {}
            errors = []

            for name, task in tasks.items():
                if task in done:
                    try:
                        results[name] = task.result()
                    except Exception as e:
                        results[name] = None
                        errors.append((name, str(e)))
                else:
                    # Task was cancelled due to timeout
                    results[name] = None
                    errors.append((name, "Timeout"))

            # Record metrics
            self.record_metric("total_stages", len(self.stages))
            self.record_metric("completed_stages", len(done))
            self.record_metric("timeout_stages", len(pending))
            self.record_metric("error_stages", len(errors))

            if errors:
                self.record_metric("errors", errors)

            return results

        except asyncio.TimeoutError:
            # This shouldn't happen with the way we're using asyncio.wait,
            # but just in case
            for task in tasks.values():
                if not task.done():
                    task.cancel()

            self.record_metric("timeout", True)
            from scripts.pipeline.exceptions import TimeoutError
            raise TimeoutError(
                f"Parallel execution timed out after {self.timeout}s",
                timeout=self.timeout
            )


class PaperlessPartsDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching quotes from the Paperless Parts API.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None,
                 include_revisions: bool = True, name: str = "paperless_parts_acquisition"):
        super().__init__(name)
        self.start_id = start_id
        self.end_id = end_id
        self.include_revisions = include_revisions

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch quotes from the Paperless Parts API.

        Returns:
            List of quote dictionaries
        """
        from scripts.pull_quotes_async import QuotesPuller

        # Create a puller instance
        puller = QuotesPuller(
            start_id=self.start_id,
            end_id=self.end_id,
            include_revisions=self.include_revisions
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

        # Record metrics
        self.record_metric("total_quotes", len(quotes))
        self.record_metric("quote_items", len(puller.quote_items))

        # Store quote items in context for later stages
        self.set_context("quote_items", puller.quote_items)

        return quotes
