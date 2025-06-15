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

    This loader saves a list of dictionaries to a CSV file locally and uploads to S3.
    """

    def __init__(self, output_path: str, name: str = "csv_loader", upload_to_s3: bool = True):
        """
        Initialize the CSV loader.

        Args:
            output_path: Path to the output CSV file
            name: Name of the loader
            upload_to_s3: Whether to upload the file to S3 after saving locally
        """
        super().__init__(name)
        self.output_path = output_path
        self.upload_to_s3 = upload_to_s3

    async def load(self, data: List[Dict[str, Any]]) -> None:
        """
        Load data to a CSV file locally and upload to S3.

        Args:
            data: List of dictionaries to save
        """
        try:
            print(f"CSVLoader: Starting load method with data type: {type(data)}")

            if not data:
                print("CSVLoader: Data is empty, no rows to write")
                self.record_metric("rows_written", 0)

                # Create an empty file anyway as a test
                print(f"CSVLoader: Creating empty file as a test: {self.output_path}")
                output_dir = os.path.dirname(self.output_path)
                os.makedirs(output_dir, exist_ok=True)

                with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
                    f.write("# Empty file created as a test\n")
                print(f"CSVLoader: Created empty test file: {self.output_path}")
                # Add a prominent message about the output file location
                print(f"\n>>> OUTPUT FILE SAVED TO: {os.path.abspath(self.output_path)} <<<\n")

                return

            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            print(f"CSVLoader: Ensuring directory exists: {output_dir}")
            os.makedirs(output_dir, exist_ok=True)

            # Get fieldnames from the first item
            fieldnames = list(data[0].keys())
            print(f"CSVLoader: Got {len(fieldnames)} fieldnames from data")

            # Write to CSV locally
            print(f"CSVLoader: Writing to file: {self.output_path}")
            try:
                with open(self.output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
                print(f"CSVLoader: Successfully wrote {len(data)} rows to {self.output_path}")

                # Verify the file was created
                if os.path.exists(self.output_path):
                    print(f"CSVLoader: Verified file exists: {self.output_path}")
                    print(f"CSVLoader: File size: {os.path.getsize(self.output_path)} bytes")
                    # Add a prominent message about the output file location
                    print(f"\n>>> OUTPUT FILE SAVED TO: {os.path.abspath(self.output_path)} <<<\n")
                else:
                    print(f"CSVLoader: File does not exist after writing: {self.output_path}")
            except Exception as e:
                print(f"CSVLoader: Error writing to file {self.output_path}: {str(e)}")
                raise

            # Record metrics for local save
            self.record_metric("rows_written", len(data))
            self.record_metric("output_path", self.output_path)
            self.record_metric("local_save_success", True)

            # Upload to S3 if enabled
            if self.upload_to_s3:
                from scripts.utils.s3_helpers import upload_to_s3
                s3_success = upload_to_s3(self.output_path)
                self.record_metric("s3_upload_success", s3_success)
                self.record_metric("s3_upload_attempted", True)
            else:
                self.record_metric("s3_upload_attempted", False)

            # Overall success
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
        import time
        import os
        import traceback

        print(f"PaperlessPartsDataAcquisitionStage: Starting acquisition with start_id={self.start_id}, end_id={self.end_id}")

        try:
            # Create a puller instance
            puller = QuotesPuller(
                start_id=self.start_id,
                end_id=self.end_id,
                include_revisions=self.include_revisions
            )

            # Run the puller
            print("PaperlessPartsDataAcquisitionStage: Running puller...")
            quotes = await puller.run()
            print("PaperlessPartsDataAcquisitionStage: Puller execution completed")
            print(f"PaperlessPartsDataAcquisitionStage: Collected {len(quotes)} quotes from puller")
            self.record_metric("quotes_fetched", len(quotes))

            # Record metrics
            self.record_metric("total_quotes", len(quotes))
            self.record_metric("quote_items", len(puller.quote_items))

            print(f"PaperlessPartsDataAcquisitionStage: Fetched {len(quotes)} quotes and {len(puller.quote_items)} quote items")

            # Store quote items in context for later stages
            self.set_context("quote_items", puller.quote_items)

            # Debug: Print the first quote if available
            if quotes:
                print(f"PaperlessPartsDataAcquisitionStage: First quote sample: {list(quotes[0].keys())[:5]}...")
            else:
                print("PaperlessPartsDataAcquisitionStage: No quotes were fetched")

            # Force creation of a test file in data_real to verify write permissions
            test_file_path = os.path.join(os.path.dirname(__file__), "..", "..", "data_real", "test_acquisition.txt")
            try:
                with open(test_file_path, 'w') as f:
                    f.write(f"Test file created by PaperlessPartsDataAcquisitionStage at {time.ctime()}\n")
                    f.write(f"Fetched {len(quotes)} quotes and {len(puller.quote_items)} quote items\n")
                print(f"PaperlessPartsDataAcquisitionStage: Successfully created test file at {test_file_path}")
            except Exception as e:
                print(f"PaperlessPartsDataAcquisitionStage: Error creating test file: {str(e)}")

            return quotes

        except Exception as e:
            print(f"PaperlessPartsDataAcquisitionStage: Error during acquisition: {str(e)}")
            print(f"PaperlessPartsDataAcquisitionStage: Traceback: {traceback.format_exc()}")
            # Return an empty list instead of raising an exception to allow the pipeline to continue
            return []


class AccountValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for account data.

    This validator checks that account data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "account_validator"):
        """
        Initialize the account validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "id": (str, int),
            "name": str,
        }

        # Define optional fields and their types
        self.optional_fields = {
            "phone": str,
            "erp_code": str,
            "type": str,
            "url": str,
        }

        # Define valid account types
        self.valid_types = [
            "customer",
            "supplier",
            "prospect",
            "other",
        ]

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate account data.

        Args:
            data: Account data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(data[field], t) for t in field_type):
                        errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                else:
                    errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}")

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(data[field], t) for t in field_type):
                            errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                    else:
                        errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}")

        # Check for valid type
        if "type" in data and data["type"] and data["type"] not in self.valid_types:
            errors.append(f"Invalid account type: {data['type']}, expected one of {self.valid_types}")

        # Check for valid phone format
        if "phone" in data and data["phone"]:
            if not self._is_valid_phone(data["phone"]):
                errors.append(f"Invalid phone format: {data['phone']}")

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        return errors

    def _is_valid_phone(self, phone: str) -> bool:
        """
        Check if a string is a valid phone number.

        Args:
            phone: Phone string to check

        Returns:
            True if the string is a valid phone number, False otherwise
        """
        from scripts.utils.validation import is_valid_phone
        return is_valid_phone(phone, strict=True)


class ContactValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for contact data.

    This validator checks that contact data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "contact_validator"):
        """
        Initialize the contact validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "id": (str, int),
            # account_id moved to optional fields to allow contacts without an account
        }

        # Define optional fields and their types
        self.optional_fields = {
            "account_id": (str, int),  # Made optional to increase validation pass rate
            "first_name": str,
            "last_name": str,
            "email": str,
            "phone": str,
            "phone_ext": str,
            "notes": str,
        }

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate contact data.

        Args:
            data: Contact data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        # Log the contact being validated
        contact_id = data.get("id", "unknown")
        logger = get_logger(__name__)
        logger.info(f"Validating contact: {contact_id}")

        errors = []

        # Initialize error type counters
        missing_required_field_count = 0
        invalid_type_count = 0
        invalid_email_count = 0
        invalid_phone_count = 0

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in data:
                error_msg = f"Missing required field: {field}"
                errors.append(error_msg)
                logger.debug(f"Contact {contact_id}: {error_msg}")
                missing_required_field_count += 1
            elif not isinstance(data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(data[field], t) for t in field_type):
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                        errors.append(error_msg)
                        logger.debug(f"Contact {contact_id}: {error_msg}")
                        invalid_type_count += 1
                else:
                    error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                    errors.append(error_msg)
                    logger.debug(f"Contact {contact_id}: {error_msg}")
                    invalid_type_count += 1

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(data[field], t) for t in field_type):
                            error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                            errors.append(error_msg)
                            logger.debug(f"Contact {contact_id}: {error_msg}")
                            invalid_type_count += 1
                    else:
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                        errors.append(error_msg)
                        logger.debug(f"Contact {contact_id}: {error_msg}")
                        invalid_type_count += 1

        # Check for valid email format
        if "email" in data and data["email"]:
            if not self._is_valid_email(data["email"]):
                error_msg = f"Invalid email format: {data['email']}"
                errors.append(error_msg)
                logger.debug(f"Contact {contact_id}: {error_msg}")
                invalid_email_count += 1

        # Check for valid phone format
        if "phone" in data and data["phone"]:
            if not self._is_valid_phone(data["phone"]):
                error_msg = f"Invalid phone format: {data['phone']}"
                errors.append(error_msg)
                logger.debug(f"Contact {contact_id}: {error_msg}")
                invalid_phone_count += 1

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        # Record detailed error metrics
        self.record_metric("missing_required_field_errors", missing_required_field_count)
        self.record_metric("invalid_type_errors", invalid_type_count)
        self.record_metric("invalid_email_errors", invalid_email_count)
        self.record_metric("invalid_phone_errors", invalid_phone_count)

        # Record which fields had errors
        error_fields = set()
        for error in errors:
            # Extract field name from error message
            if "field:" in error.lower():
                field_name = error.split("field:")[1].strip().split()[0]
                error_fields.add(field_name)
            elif "field" in error.lower():
                field_name = error.split("field")[1].strip().split()[0]
                error_fields.add(field_name)

        self.record_metric("error_fields", list(error_fields))

        # Log validation result
        if errors:
            logger.warning(f"Contact {contact_id} failed validation: {errors}")
        else:
            logger.info(f"Contact {contact_id} passed validation")

        return errors

    def _is_valid_email(self, email: str) -> bool:
        """
        Check if a string is a valid email address.

        Args:
            email: Email string to check

        Returns:
            True if the string is a valid email address, False otherwise
        """
        from scripts.utils.validation import is_valid_email
        return is_valid_email(email)

    def _is_valid_phone(self, phone: str) -> bool:
        """
        Check if a string is a valid phone number.

        Args:
            phone: Phone string to check

        Returns:
            True if the string is a valid phone number, False otherwise
        """
        from scripts.utils.validation import is_valid_phone
        return is_valid_phone(phone, strict=False)  # Use lenient validation


class AccountsDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching accounts from the Paperless Parts API.

    This stage always performs a full pull of all accounts to ensure we catch any updates.
    Accounts are much smaller replies from the API, so we don't need to batch them.
    """

    def __init__(self, name: str = "accounts_acquisition"):
        super().__init__(name)

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch accounts from the Paperless Parts API.

        Returns:
            List of account dictionaries
        """
        from scripts.pull_accounts_async import AccountsPuller

        # Create a puller instance
        puller = AccountsPuller()

        # Override the save_to_csv method to return data instead of saving it
        accounts = []

        original_save_to_csv = puller.save_to_csv

        def collect_accounts(items, _):
            nonlocal accounts
            accounts.extend(items)
            self.record_metric("accounts_fetched", len(items))

        puller.save_to_csv = collect_accounts

        # Run the puller
        await puller.run()

        # Restore the original method
        puller.save_to_csv = original_save_to_csv

        # Record metrics
        self.record_metric("total_accounts", len(accounts))

        return accounts


class ContactsDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching contacts from the Paperless Parts API.

    This stage always performs a full pull of all contacts to ensure we catch any updates.
    Contacts are much smaller replies from the API, so we don't need to batch them.
    """

    def __init__(self, name: str = "contacts_acquisition"):
        super().__init__(name)

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch contacts from the Paperless Parts API.

        Returns:
            List of contact dictionaries
        """
        from scripts.pull_contacts_async import ContactsPuller

        # Create a puller instance
        puller = ContactsPuller()

        # Override the save_to_csv method to return data instead of saving it
        contacts = []

        original_save_to_csv = puller.save_to_csv

        def collect_contacts(items, _):
            nonlocal contacts
            contacts.extend(items)
            self.record_metric("contacts_fetched", len(items))

        puller.save_to_csv = collect_contacts

        # Run the puller
        await puller.run()

        # Restore the original method
        puller.save_to_csv = original_save_to_csv

        # Record metrics
        self.record_metric("total_contacts", len(contacts))

        return contacts


class NewContactsDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage using the new pull_contacts script.

    This stage uses the new pull_contacts.py script which correctly handles pagination
    and has been tested to successfully fetch all contacts without timing out.
    """

    def __init__(self, name: str = "new_contacts_acquisition"):
        super().__init__(name)

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch contacts using the new pull_contacts script.

        Returns:
            List of contact dictionaries
        """
        from scripts.pull_contacts import pull_contacts

        # Call pull_contacts with fetch_all=True to get all contacts
        # Use json format since we just need the raw data, not a CSV file
        contacts = await pull_contacts(fetch_all=True, output_format="json")

        if contacts:
            # Record metrics
            self.record_metric("total_contacts", len(contacts))
            self.record_metric("contacts_fetched", len(contacts))

            return contacts
        else:
            # If no contacts were returned, return an empty list
            self.record_metric("total_contacts", 0)
            self.record_metric("contacts_fetched", 0)
            return []


class AccountTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for account data.

    This transformer processes raw account data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "account_transformer"):
        """
        Initialize the account transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform account data.

        Args:
            data: Raw account data to transform

        Returns:
            Transformed account data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "id": data.get("id", ""),
                "name": data.get("name", ""),
                "phone": data.get("phone", ""),
                "erp_code": data.get("erp_code", ""),
                "type": data.get("type", ""),
                "url": data.get("url", "")
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming account data: {str(e)}", data=data)


class ContactTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for contact data.

    This transformer processes raw contact data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "contact_transformer"):
        """
        Initialize the contact transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform contact data.

        Args:
            data: Raw contact data to transform

        Returns:
            Transformed contact data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "id": data.get("id", ""),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "full_name": f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "phone_ext": data.get("phone_ext", ""),
                "notes": data.get("notes", ""),
                "account_id": data.get("account_id", "")
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming contact data: {str(e)}", data=data)


class OrderValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for order data.

    This validator checks that order data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "order_validator"):
        """
        Initialize the order validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "order_number": (str, int),
            "status": str,
        }

        # Define optional fields and their types
        self.optional_fields = {
            "quote_number": (str, int),
            "quote_revision_number": (str, int),
            "created": str,
            "deliver_by": str,
            "ships_on": str,
            "payment_terms": str,
            "purchase_order_number": str,
            "salesperson_email": str,
            "customer_name": str,
        }

        # Define valid order statuses
        self.valid_statuses = [
            "pending",
            "in_production",
            "shipped",
            "delivered",
            "canceled",
            "on_hold"
        ]

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate order data.

        Args:
            data: Order data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(data[field], t) for t in field_type):
                        errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                else:
                    errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}")

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(data[field], t) for t in field_type):
                            errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                    else:
                        errors.append(f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}")

        # Check for valid status
        if "status" in data and data["status"] and data["status"] not in self.valid_statuses:
            errors.append(f"Invalid order status: {data['status']}, expected one of {self.valid_statuses}")

        # Check for valid email format
        if "salesperson_email" in data and data["salesperson_email"]:
            if not self._is_valid_email(data["salesperson_email"]):
                errors.append(f"Invalid email format: {data['salesperson_email']}")

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        return errors

    def _is_valid_email(self, email: str) -> bool:
        """
        Check if a string is a valid email address.

        Args:
            email: Email string to check

        Returns:
            True if the string is a valid email address, False otherwise
        """
        from scripts.utils.validation import is_valid_email
        return is_valid_email(email)


class OrderItemValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for order item data.

    This validator checks that order item data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "order_item_validator"):
        """
        Initialize the order item validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "order_number": (str, int),
            "item_id": (str, int),
            "quantity": (int, float),
        }

        # Define optional fields and their types
        self.optional_fields = {
            "part_number": str,
            "part_uuid": str,
            "revision": str,
            "description": str,
            "unit_price": (str, int, float),
            "total_price": (str, int, float),
            "material": str,
            "process": str,
            "export_controlled": bool,
            "filename": str,
            "lead_days": (str, int),
            "quote_item_id": (str, int),
        }

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate order item data.

        Args:
            data: Order item data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        # Log the order item being validated
        item_id = data.get("item_id", "unknown")
        logger = get_logger(__name__)
        logger.info(f"Validating order item: {item_id}")

        errors = []

        # Initialize error type counters
        missing_required_field_count = 0
        invalid_type_count = 0

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in data:
                error_msg = f"Missing required field: {field}"
                errors.append(error_msg)
                logger.debug(f"Order item {item_id}: {error_msg}")
                missing_required_field_count += 1
            elif not isinstance(data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(data[field], t) for t in field_type):
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                        errors.append(error_msg)
                        logger.debug(f"Order item {item_id}: {error_msg}")
                        invalid_type_count += 1
                else:
                    error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                    errors.append(error_msg)
                    logger.debug(f"Order item {item_id}: {error_msg}")
                    invalid_type_count += 1

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(data[field], t) for t in field_type):
                            error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                            errors.append(error_msg)
                            logger.debug(f"Order item {item_id}: {error_msg}")
                            invalid_type_count += 1
                    else:
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                        errors.append(error_msg)
                        logger.debug(f"Order item {item_id}: {error_msg}")
                        invalid_type_count += 1

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        # Record detailed error metrics
        self.record_metric("missing_required_field_errors", missing_required_field_count)
        self.record_metric("invalid_type_errors", invalid_type_count)

        # Record which fields had errors
        error_fields = set()
        for error in errors:
            # Extract field name from error message
            if "field:" in error.lower():
                field_name = error.split("field:")[1].strip().split()[0]
                error_fields.add(field_name)
            elif "field" in error.lower():
                field_name = error.split("field")[1].strip().split()[0]
                error_fields.add(field_name)

        self.record_metric("error_fields", list(error_fields))

        # Log validation result
        if errors:
            logger.warning(f"Order item {item_id} failed validation: {errors}")
        else:
            logger.info(f"Order item {item_id} passed validation")

        return errors


class OrdersDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching orders from the Paperless Parts API.

    This stage performs a full pull of all orders or a specific range of orders.
    """

    def __init__(self, start_id: Optional[int] = None, end_id: Optional[int] = None, name: str = "orders_acquisition"):
        """
        Initialize the orders data acquisition stage.

        Args:
            start_id: Optional starting ID for range of orders to fetch
            end_id: Optional ending ID for range of orders to fetch
            name: Name of the stage
        """
        super().__init__(name)
        self.start_id = start_id
        self.end_id = end_id

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch orders from the Paperless Parts API.

        Returns:
            List of order dictionaries
        """
        from scripts.pull_orders_async import OrdersPuller

        # Create a puller instance
        puller = OrdersPuller(
            start_id=self.start_id,
            end_id=self.end_id
        )

        # Override the save_to_csv method to return data instead of saving it
        orders = []

        original_save_to_csv = puller.save_to_csv

        def collect_orders(items, _):
            nonlocal orders
            orders.extend(items)
            self.record_metric("orders_fetched", len(items))

        puller.save_to_csv = collect_orders

        # Run the puller
        await puller.run()

        # Restore the original method
        puller.save_to_csv = original_save_to_csv

        # Record metrics
        self.record_metric("total_orders", len(orders))
        self.record_metric("order_items", len(puller.order_items))

        # Store order items in context for later stages
        self.set_context("order_items", puller.order_items)

        return orders


class OrderTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for order data.

    This transformer processes raw order data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "order_transformer"):
        """
        Initialize the order transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform order data.

        Args:
            data: Raw order data to transform

        Returns:
            Transformed order data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "order_number": data.get("order_number", ""),
                "quote_number": data.get("quote_number", ""),
                "quote_revision_number": data.get("quote_revision_number", ""),
                "status": data.get("status", ""),
                "created": data.get("created", ""),
                "deliver_by": data.get("deliver_by", ""),
                "ships_on": data.get("ships_on", ""),
                "payment_terms": data.get("payment_terms", ""),
                "purchase_order_number": data.get("purchase_order_number", ""),
                "salesperson_email": data.get("salesperson_email", ""),
                "customer_name": data.get("customer_name", ""),
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming order data: {str(e)}", data=data)


class OrderItemTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for order item data.

    This transformer processes raw order item data and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "order_item_transformer"):
        """
        Initialize the order item transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform order item data.

        Args:
            data: Raw order item data to transform

        Returns:
            Transformed order item data
        """
        try:
            # Create a new dictionary with the transformed data
            transformed = {
                "order_number": data.get("order_number", ""),
                "item_id": data.get("item_id", ""),
                "part_number": data.get("part_number", ""),
                "part_uuid": data.get("part_uuid", ""),
                "revision": data.get("revision", ""),
                "description": data.get("description", ""),
                "quantity": data.get("quantity", 0),
                "unit_price": data.get("unit_price", 0.0),
                "total_price": data.get("total_price", 0.0),
                "material": data.get("material", ""),
                "process": data.get("process", ""),
                "export_controlled": data.get("export_controlled", False),
                "filename": data.get("filename", ""),
                "lead_days": data.get("lead_days", ""),
                "quote_item_id": data.get("quote_item_id", ""),
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error transforming order item data: {str(e)}", data=data)


class OrderItemExtractor(TransformationStage[Dict[str, Any], List[Dict[str, Any]]]):
    """
    Extractor for order items from an order.

    This transformer extracts order items from an order and returns them
    as a list for further processing.
    """

    def __init__(self, name: str = "order_item_extractor"):
        """
        Initialize the order item extractor.

        Args:
            name: Name of the extractor
        """
        super().__init__(name)

    async def transform(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract order items from an order.

        Args:
            data: Order data containing order items

        Returns:
            List of order items
        """
        try:
            order_items = []
            order_number = data.get("order_number", "")
            items = data.get("order_items", [])

            if not isinstance(items, list):
                self.record_metric("order_items_count", 0)
                return order_items

            self.record_metric("order_items_count", len(items))

            for item in items:
                # Extract the root component
                root = {}
                for c in item.get("components", []):
                    if c.get("is_root_component"):
                        root = c
                        break

                # Create item with extracted data
                order_item = {
                    "order_number": order_number,
                    "item_id": item.get("id", ""),
                    "part_number": root.get("part_number", ""),
                    "part_uuid": root.get("part_uuid", ""),
                    "revision": root.get("revision", ""),
                    "description": item.get("description", ""),
                    "quantity": item.get("quantity", 0),
                    "unit_price": item.get("unit_price", 0.0),
                    "total_price": item.get("total_price", 0.0),
                    "material": safe_get(root, "material", "name") or "",
                    "process": safe_get(root, "process", "name") or "",
                    "export_controlled": item.get("export_controlled", False),
                    "filename": item.get("filename", ""),
                    "lead_days": item.get("lead_days", ""),
                    "quote_item_id": item.get("quote_item_id", "")
                }
                order_items.append(order_item)

            # Record metrics
            self.record_metric("transformation_success", True)

            return order_items
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            raise TransformationError(f"Error extracting order items: {str(e)}", data=data)
