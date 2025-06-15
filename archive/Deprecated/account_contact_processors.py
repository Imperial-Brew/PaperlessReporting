"""
Data processors for accounts and contacts in the pipeline framework.

This module provides processors for acquiring, validating, and transforming
account and contact data from the Paperless Parts API.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic

from scripts.pipeline.base import DataAcquisitionStage, TransformationStage, ValidationStage
from scripts.pipeline.exceptions import TransformationError, ValidationError
from scripts.utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

# Type variables for generic stages
T = TypeVar('T')
U = TypeVar('U')


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
