"""
Pipeline orchestrators for accounts and contacts in the pipeline framework.

This module provides orchestrators for creating pipelines for processing
account and contact data from the Paperless Parts API.
"""

from typing import Any, Dict, List, Optional, Union

from scripts.pipeline.orchestrator import Pipeline, WrapInList
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class AccountPipeline:
    """
    Factory for creating account processing pipelines.

    This class provides methods for creating pipelines for processing
    account data with different configurations.
    """

    @staticmethod
    def create_validation_pipeline(name: str = "account_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating account data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import AccountValidator

        pipeline = Pipeline(name)
        pipeline.add_stage(AccountValidator())

        return pipeline

    @staticmethod
    def create_transformation_pipeline(name: str = "account_transformation_pipeline") -> Pipeline:
        """
        Create a pipeline for transforming account data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import AccountValidator, AccountTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(AccountValidator())
        pipeline.add_stage(AccountTransformer())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "account_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for validating, transforming, and exporting account data to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import AccountValidator, AccountTransformer
        from scripts.pipeline.processors import CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(AccountValidator())
        pipeline.add_stage(AccountTransformer())

        # Wrap the transformed account in a list for the CSV loader
        pipeline.add_stage(WrapInList())
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_acquisition_pipeline(output_path: str = None, name: str = "account_acquisition_pipeline") -> Pipeline:
        """
        Create a pipeline for acquiring, validating, transforming, and exporting account data.

        This pipeline performs a full pull of all accounts to ensure we catch any updates.
        Accounts are much smaller replies from the API, so we don't need to batch them.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import AccountsDataAcquisitionStage, AccountValidator, AccountTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(AccountsDataAcquisitionStage())
        pipeline.add_stage(BatchProcessor(AccountValidator()))
        pipeline.add_stage(BatchProcessor(AccountTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline


class ContactPipeline:
    """
    Factory for creating contact processing pipelines.

    This class provides methods for creating pipelines for processing
    contact data with different configurations.
    """

    @staticmethod
    def create_validation_pipeline(name: str = "contact_validation_pipeline") -> Pipeline:
        """
        Create a pipeline for validating contact data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import ContactValidator

        pipeline = Pipeline(name)
        pipeline.add_stage(ContactValidator())

        return pipeline

    @staticmethod
    def create_transformation_pipeline(name: str = "contact_transformation_pipeline") -> Pipeline:
        """
        Create a pipeline for transforming contact data.

        Args:
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import ContactValidator, ContactTransformer

        pipeline = Pipeline(name)
        pipeline.add_stage(ContactValidator())
        pipeline.add_stage(ContactTransformer())

        return pipeline

    @staticmethod
    def create_csv_export_pipeline(output_path: str, name: str = "contact_csv_export_pipeline") -> Pipeline:
        """
        Create a pipeline for validating, transforming, and exporting contact data to CSV.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import ContactValidator, ContactTransformer
        from scripts.pipeline.processors import CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(ContactValidator())
        pipeline.add_stage(ContactTransformer())

        # Wrap the transformed contact in a list for the CSV loader
        pipeline.add_stage(WrapInList())
        pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_acquisition_pipeline(output_path: str = None, name: str = "contact_acquisition_pipeline") -> Pipeline:
        """
        Create a pipeline for acquiring, validating, transforming, and exporting contact data.

        This pipeline performs a full pull of all contacts to ensure we catch any updates.
        Contacts are much smaller replies from the API, so we don't need to batch them.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import ContactsDataAcquisitionStage, ContactValidator, ContactTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(ContactsDataAcquisitionStage())
        pipeline.add_stage(BatchProcessor(ContactValidator()))
        pipeline.add_stage(BatchProcessor(ContactTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline

    @staticmethod
    def create_acquisition_pipeline_with_new_script(output_path: str = None, name: str = "contact_acquisition_pipeline_new") -> Pipeline:
        """
        Create a pipeline for acquiring, validating, transforming, and exporting contact data using the new pull_contacts script.

        This pipeline uses the new pull_contacts.py script which correctly handles pagination
        and has been tested to successfully fetch all contacts without timing out.

        Args:
            output_path: Path to the output CSV file
            name: Name of the pipeline

        Returns:
            Pipeline instance
        """
        from scripts.pipeline.account_contact_processors import NewContactsDataAcquisitionStage, ContactValidator, ContactTransformer
        from scripts.pipeline.processors import BatchProcessor, CSVLoader

        pipeline = Pipeline(name)
        pipeline.add_stage(NewContactsDataAcquisitionStage())
        pipeline.add_stage(BatchProcessor(ContactValidator()))
        pipeline.add_stage(BatchProcessor(ContactTransformer()))

        if output_path:
            pipeline.add_stage(CSVLoader(output_path))

        return pipeline
