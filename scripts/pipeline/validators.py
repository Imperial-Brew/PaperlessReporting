"""
Data validators for the pipeline framework.

This module provides validators for different data types processed by the pipeline.
"""

import re
from typing import Any, Dict, List, Optional, Union
import datetime

from scripts.pipeline.base import ValidationStage


class QuoteValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for quote data.

    This validator checks that quote data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "quote_validator"):
        """
        Initialize the quote validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "quote_number": str,
            "revision_number": (str, int),
            "status": str,
        }

        # Define optional fields and their types
        self.optional_fields = {
            "created": str,
            "due_date": str,
            "sent_date": str,
            "expired_date": str,
            "expired": bool,
            "rfq_number": str,
            "priority": str,
            "private_notes": str,
            "authenticated_pdf_quote_url": str,
            "contact_name": str,
            "contact_email": str,
            "customer_name": str,
            "estimator_email": str,
            "salesperson_email": str,
        }

        # Define valid status values
        self.valid_statuses = [
            "draft",
            "pending",
            "sent",
            "accepted",
            "rejected",
            "expired",
            "ordered",
            "outstanding",  # Added to support additional status values
            "trash",        # Added to support additional status values
        ]

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate quote data.

        Args:
            data: Quote data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if data is a dictionary, if not, return an error
        if not isinstance(data, dict):
            error_msg = f"Invalid data type: {type(data).__name__}, expected dict"
            return [error_msg]

        # Pre-process data to handle type conversions
        processed_data = data.copy()

        # Convert quote_number to string if it's not already
        if "quote_number" in processed_data and processed_data["quote_number"] is not None:
            processed_data["quote_number"] = str(processed_data["quote_number"])

        # Handle revision_number being None by setting a default value of 0
        if "revision_number" in processed_data and processed_data["revision_number"] is None:
            processed_data["revision_number"] = 0

        # Convert priority to string if it's an integer
        if "priority" in processed_data and processed_data["priority"] is not None:
            if isinstance(processed_data["priority"], int):
                processed_data["priority"] = str(processed_data["priority"])

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in processed_data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(processed_data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(processed_data[field], t) for t in field_type):
                        errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                else:
                    errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected {field_type.__name__}")

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in processed_data and processed_data[field] is not None:
                if not isinstance(processed_data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(processed_data[field], t) for t in field_type):
                            errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                    else:
                        errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected {field_type.__name__}")

        # Check for valid status
        if "status" in processed_data and processed_data["status"] not in self.valid_statuses:
            errors.append(f"Invalid status: {processed_data['status']}, expected one of {self.valid_statuses}")

        # Check date formats
        date_fields = ["created", "due_date", "sent_date", "expired_date"]
        for field in date_fields:
            if field in processed_data and processed_data[field]:
                if not self._is_valid_date_format(processed_data[field]):
                    errors.append(f"Invalid date format for {field}: {processed_data[field]}")

        # Check email formats
        email_fields = ["contact_email", "estimator_email", "salesperson_email"]
        for field in email_fields:
            if field in processed_data and processed_data[field]:
                if not self._is_valid_email(processed_data[field]):
                    errors.append(f"Invalid email format for {field}: {processed_data[field]}")

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        return errors

    def _is_valid_date_format(self, date_str: str) -> bool:
        """
        Check if a string is in a valid date format.

        Args:
            date_str: Date string to check

        Returns:
            True if the string is in a valid date format, False otherwise
        """
        try:
            # Try to parse the date string
            datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return True
        except (ValueError, TypeError):
            return False

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


class QuoteItemValidator(ValidationStage[Dict[str, Any]]):
    """
    Validator for quote item data.

    This validator checks that quote item data contains all required fields
    and that the values are of the correct type and format.
    """

    def __init__(self, name: str = "quote_item_validator"):
        """
        Initialize the quote item validator.

        Args:
            name: Name of the validator
        """
        super().__init__(name)

        # Define required fields and their types
        self.required_fields = {
            "quote_number": str,
            "item_id": (str, int),
        }

        # Define optional fields and their types
        self.optional_fields = {
            "quote_revision": (str, int, type(None)),
            "workflow_status": str,
            "part_number": str,
            "revision": str,
            "description": str,
            "type": str,
            "material": str,
            "process": str,
            "is_fully_configured": bool,
            "part_uuid": str,
            "export_controlled": bool,
            "quantity": (int, float),
            "unit_price": (int, float),
            "total_price": (int, float),
            "total_price_with_add_ons": (int, float),
            "lead_time": (int, str),
        }

    async def validate(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate quote item data.

        Args:
            data: Quote item data to validate

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check if data is a dictionary, if not, return an error
        if not isinstance(data, dict):
            error_msg = f"Invalid data type: {type(data).__name__}, expected dict"
            return [error_msg]

        # Pre-process data to handle type conversions
        processed_data = data.copy()

        # Convert quote_number to string if it's not already
        if "quote_number" in processed_data and processed_data["quote_number"] is not None:
            processed_data["quote_number"] = str(processed_data["quote_number"])

        # Convert item_id to string if it's not already
        if "item_id" in processed_data and processed_data["item_id"] is not None:
            if not isinstance(processed_data["item_id"], (str, int)):
                processed_data["item_id"] = str(processed_data["item_id"])

        # Handle quote_revision being None (it's already in optional_fields with type(None))

        # Check for required fields
        for field, field_type in self.required_fields.items():
            if field not in processed_data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(processed_data[field], field_type):
                if isinstance(field_type, tuple):
                    if not any(isinstance(processed_data[field], t) for t in field_type):
                        errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                else:
                    errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected {field_type.__name__}")

        # Check for optional fields with correct types
        for field, field_type in self.optional_fields.items():
            if field in processed_data and processed_data[field] is not None:
                if not isinstance(processed_data[field], field_type):
                    if isinstance(field_type, tuple):
                        if not any(isinstance(processed_data[field], t) for t in field_type):
                            errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected one of {[t.__name__ for t in field_type]}")
                    else:
                        errors.append(f"Field {field} has invalid type: {type(processed_data[field]).__name__}, expected {field_type.__name__}")

        # Record validation metrics
        self.record_metric("validation_errors", len(errors))
        self.record_metric("has_errors", len(errors) > 0)

        return errors
