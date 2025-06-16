import asyncio
import os
import json
import pandas as pd
from pathlib import Path
import sys
import logging

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from scripts.utils.logging_config import get_logger
from scripts.pipeline.builder import PipelineBuilder
from scripts.pipeline.processors import CSVLoader
from scripts.pipeline.base import DataAcquisitionStage, ValidationStage, TransformationStage
from typing import Dict, Any, List
import re

# Initialize logger
logger = get_logger(__name__)

# Get the project root directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKPOINT_FILE = os.path.join(PROJECT_ROOT, "data_real", "user_pipeline_checkpoint.json")


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


class UsersDataAcquisitionStage(DataAcquisitionStage[List[Dict[str, Any]]]):
    """
    Data acquisition stage for fetching users from the Paperless Parts API.

    This stage uses the fetch_users function from pull_users.py to fetch all users.
    """

    def __init__(self, name: str = "users_acquisition", timeout: int = 180):
        """
        Initialize the users data acquisition stage.

        Args:
            name: Name of the stage
            timeout: Timeout in seconds for the stage operation (default: 180)
        """
        super().__init__(name)
        # Configure stage-level timeout
        self.configure_timeout(float(timeout))
        self.start_time = None

    async def acquire(self) -> List[Dict[str, Any]]:
        """
        Fetch users using the fetch_users function from pull_users.py.

        Returns:
            List of user dictionaries
        """
        import time
        from scripts.pull_users import fetch_users

        # Record start time for performance metrics
        self.start_time = time.time()

        # Call fetch_users to get all users
        users = fetch_users()

        # Map "uuid" to "id" for compatibility with UserValidator
        for user in users:
            if "uuid" in user and "id" not in user:
                user["id"] = user["uuid"]

        # Calculate and record duration
        duration = time.time() - self.start_time
        self.record_metric("acquisition_duration", duration)

        if users:
            # Record metrics
            self.record_metric("total_users", len(users))
            self.record_metric("users_fetched", len(users))

            # Log performance information
            logger.info(f"Fetched {len(users)} users in {duration:.2f} seconds")

            # Alert on abnormal processing times (more than 5 minutes)
            if duration > 300:
                logger.warning(f"User acquisition took {duration:.2f} seconds, which is longer than expected")

            return users
        else:
            # If no users were returned, return an empty list
            self.record_metric("total_users", 0)
            self.record_metric("users_fetched", 0)
            return []


class UserValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for user data.

    This validator checks that user data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "user_validator"):
        """
        Initialize the user validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "id": (str, int),
            "email": str,
        }

        # Define optional fields and their types
        self.optional_fields = {
            "first_name": str,
            "last_name": str,
        }

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate user data.

        Args:
            data: User data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in data:
                error_msg = f"Missing required field: {field}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
            elif not isinstance(data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(data[field], t) for t in field_type):
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)
                else:
                    error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                    errors.append(error_msg)
                    self.logger.warning(error_msg)

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in data and data[field] is not None:
                if not isinstance(data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(data[field], t) for t in field_type):
                            error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}"
                            errors.append(error_msg)
                            self.logger.warning(error_msg)
                    else:
                        error_msg = f"Field {field} has invalid type: {type(data[field]).__name__}, expected {field_type.__name__}"
                        errors.append(error_msg)
                        self.logger.warning(error_msg)


        # Check for valid email format
        if "email" in data and data["email"]:
            if not self._is_valid_email(data["email"]):
                error_msg = f"Invalid email format: {data['email']}"
                errors.append(error_msg)
                self.logger.warning(error_msg)

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
        # Simple regex for email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, email))


class UserTransformer(TransformationStage[Dict[str, Any], Dict[str, Any]]):
    """
    Transformer for user data.

    This transformer processes raw user data from the API and transforms
    it into a standardized format for downstream processing.
    """

    def __init__(self, name: str = "user_transformer"):
        """
        Initialize the user transformer.

        Args:
            name: Name of the transformer
        """
        super().__init__(name)
        self.logger = get_logger(__name__)

    async def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform user data.

        Args:
            data: Raw user data to transform

        Returns:
            Transformed user data
        """
        try:
            import time
            start_time = time.time()

            # Create a new dictionary with the transformed data
            transformed = {
                "id": data.get("id", ""),
                "email": data.get("email", ""),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", "")
            }

            # Record metrics
            self.record_metric("transformation_success", True)

            # Record transformation time
            duration = time.time() - start_time
            self.record_metric("transformation_time", duration)

            # Log detailed performance information for slow transformations
            if duration > 0.1:  # More than 100ms
                self.logger.warning(f"User transformation took {duration:.4f} seconds for user {data.get('id')}")

            return transformed
        except Exception as e:
            # Record metrics
            self.record_metric("transformation_success", False)
            self.record_metric("transformation_error", str(e))

            # Raise a TransformationError
            from scripts.pipeline.exceptions import TransformationError
            raise TransformationError(f"Error transforming user data: {str(e)}", data=data)


class UserSplittingCSVLoader(CSVLoader):
    """
    Custom CSV loader that saves user data to a CSV file.

    This loader processes user data and saves it to a CSV file
    for downstream analysis and reporting.

    Args:
        users_path (str): Path to save the users CSV file
    """
    def __init__(self, users_path):
        super().__init__(users_path)
        self.file_path = users_path
        self.logger = get_logger(__name__)

    async def load(self, data):
        """
        Load user data to a CSV file.

        Args:
            data (List[Dict]): List of user dictionaries

        Returns:
            List[Dict]: The original data if successful, empty list if data is None
        """
        if not data:
            self.logger.warning("UserSplittingCSVLoader received empty data")
            self.record_metric("empty_input", True)
            return []  # Return empty list instead of None

        self.logger.info(f"Processing {len(data)} users for CSV export")
        self.record_metric("input_count", len(data))

        users_data = []

        for user in data:
            users_data.append(user)

        # Save users to CSV
        try:
            users_df = pd.DataFrame(users_data)
            users_df.to_csv(self.file_path, index=False)
            self.logger.info(f"Saved {len(users_data)} users to {self.file_path}")

            # Log column names for diagnostic purposes
            self.record_metric("users_columns", list(users_df.columns))
            self.logger.debug(f"Users CSV columns: {list(users_df.columns)}")
        except Exception as e:
            self.logger.error(f"Error saving users CSV: {str(e)}")
            self.record_metric("users_save_error", str(e))
            raise

        return data  # Return the original data


async def run_pipeline():
    """
    Run the users pipeline.

    This function processes all users from the Paperless Parts API and 
    saves them to a CSV file. It includes checkpoint functionality to track 
    processing status and avoid reprocessing data unnecessarily.

    Returns:
        bool: True if pipeline executed successfully, False otherwise
    """
    logger.info("Running Users Pipeline")

    checkpoint = load_checkpoint()
    already_processed = checkpoint.get("last_processed", False)
    logger.debug(f"Checkpoint loaded. Already processed: {already_processed}")

    if already_processed:
        logger.info("Users have already been processed. To reprocess, delete the checkpoint file.")
        return False

    logger.info("Starting users processing")

    users_pipeline = (
        PipelineBuilder("users_pipeline")
        .add_acquisition(UsersDataAcquisitionStage())
        .add_batch_processor(UserValidator())
        .add_batch_processor(UserTransformer())
        .add_loading(UserSplittingCSVLoader(
            users_path=os.path.join(PROJECT_ROOT, "data_real", "users_complete.csv")
        ))
        .build()
    )

    # Configure timeout for the acquisition stage
    users_pipeline.stages[0].configure_timeout(timeout=300.0)

    try:
        logger.info("Starting pipeline execution")
        logger.debug(f"Pipeline stages: {[stage.name for stage in users_pipeline.stages]}")

        users_output = await users_pipeline.run(None)

        # Check if the CSV file was created
        csv_file_path = os.path.join(PROJECT_ROOT, "data_real", "users_complete.csv")
        csv_file_exists = os.path.exists(csv_file_path)

        # Consider the pipeline successful if either the output is not None or the CSV file exists
        success = users_output is not None or csv_file_exists

        logger.info(f"Pipeline completed successfully: {success}")

        if csv_file_exists:
            logger.info(f"CSV file created at {csv_file_path}")
        else:
            logger.warning(f"CSV file not found at {csv_file_path}")

        # Save progress
        save_checkpoint(True)
        logger.debug("Checkpoint saved")
        return success

    except asyncio.TimeoutError:
        logger.error("Timeout occurred processing users")
        await asyncio.sleep(30)  # Wait before retrying
        return False
    except Exception as e:
        logger.error(f"Error processing users: {e}", exc_info=True)
        raise


async def main():
    """
    Main entry point for the users pipeline script.

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
