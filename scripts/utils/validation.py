"""
Validation utilities for data processing.

This module provides common validation functions for checking data formats
such as email addresses, phone numbers, etc. These functions are used by
various validators throughout the application.
"""

import re
from typing import Union


def is_valid_email(email: str) -> bool:
    """
    Check if a string is a valid email address.

    Args:
        email: Email string to check

    Returns:
        True if the string is a valid email address, False otherwise
    """
    # More lenient regex for email validation
    # Allow more characters in local part and domain
    if not email:
        return True  # Empty email is considered valid

    # Very basic check: contains @ with something before and after
    email_pattern = r'.+@.+\..+'
    return bool(re.match(email_pattern, email))


def is_valid_phone(phone: str, strict: bool = False) -> bool:
    """
    Check if a string is a valid phone number.

    Args:
        phone: Phone string to check
        strict: If True, use strict validation with regex pattern.
               If False, use lenient validation (at least 7 digits).

    Returns:
        True if the string is a valid phone number, False otherwise
    """
    if not phone:
        return True  # Empty phone is considered valid

    if strict:
        # Strict regex for phone validation (allows various formats)
        phone_pattern = r'^[\+]?[(]?[0-9]{3}[)]?[-\s\.]?[0-9]{3}[-\s\.]?[0-9]{4,6}$'
        return bool(re.match(phone_pattern, phone))
    else:
        # Lenient validation: Accept any string with at least 7 digits
        digit_count = sum(c.isdigit() for c in phone)
        return digit_count >= 7


def is_valid_type(value: str, valid_types: list) -> bool:
    """
    Check if a value is one of the valid types.

    Args:
        value: Value to check
        valid_types: List of valid types

    Returns:
        True if the value is one of the valid types, False otherwise
    """
    if not value:
        return True  # Empty value is considered valid
    
    return value in valid_types