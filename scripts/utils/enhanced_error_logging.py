"""
Enhanced error logging utilities for the PaperlessReporting application.

This module provides functions for logging errors with more context information,
including entity IDs, error types, timestamps, and other relevant details.
It also provides functions for writing structured error logs to files.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from scripts.utils.logging_config import get_logger

logger = get_logger(__name__)

# Default error log directory
ERROR_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs", "errors")


def ensure_error_log_dir() -> str:
    """
    Ensure the error log directory exists.
    
    Returns:
        str: Path to the error log directory
    """
    os.makedirs(ERROR_LOG_DIR, exist_ok=True)
    return ERROR_LOG_DIR


def log_entity_error(
    entity_type: str,
    entity_id: Union[str, int],
    error_type: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None,
    source: Optional[str] = None,
    log_to_file: bool = True,
    file_suffix: str = "public"
) -> Dict[str, Any]:
    """
    Log an error related to a specific entity with context information.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        entity_id: ID of the entity
        error_type: Type of error (validation, api, transformation, etc.)
        error_message: Error message
        details: Additional details about the error
        source: Source of the error (function, method, etc.)
        log_to_file: Whether to log the error to a file
        file_suffix: Suffix for the error log file
        
    Returns:
        Dict[str, Any]: Error information as a dictionary
    """
    # Create error information dictionary
    error_info = {
        "timestamp": datetime.datetime.now().isoformat(),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "error_type": error_type,
        "error_message": error_message,
        "source": source or "unknown",
    }
    
    if details:
        error_info["details"] = details
    
    # Log the error
    logger.error(
        f"Error processing {entity_type} {entity_id}: {error_message}",
        extra={"error_info": error_info}
    )
    
    # Write to error log file if requested
    if log_to_file:
        write_entity_error_to_file(entity_type, entity_id, error_info, file_suffix)
    
    return error_info


def write_entity_error_to_file(
    entity_type: str,
    entity_id: Union[str, int],
    error_info: Dict[str, Any],
    file_suffix: str = "public"
) -> None:
    """
    Write error information to a file.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        entity_id: ID of the entity
        error_info: Error information dictionary
        file_suffix: Suffix for the error log file
    """
    try:
        # Ensure error log directory exists
        error_log_dir = ensure_error_log_dir()
        
        # Determine file path
        file_name = f"failed_{entity_type.lower()}s_{file_suffix}.json"
        file_path = os.path.join(error_log_dir, file_name)
        
        # Load existing errors if file exists
        errors = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    errors = json.load(f)
                    if not isinstance(errors, list):
                        errors = []
            except json.JSONDecodeError:
                # If file exists but is not valid JSON, start with empty list
                errors = []
        
        # Add new error
        errors.append(error_info)
        
        # Write errors to file
        with open(file_path, 'w') as f:
            json.dump(errors, f, indent=2)
        
        # Also write to simple ID list for backward compatibility
        simple_file_name = f"failed_{entity_type.lower()}s_{file_suffix}.txt"
        simple_file_path = os.path.join(error_log_dir, simple_file_name)
        
        # Get existing IDs
        existing_ids = set()
        if os.path.exists(simple_file_path):
            with open(simple_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_ids.add(line)
        
        # Add new ID if not already present
        if str(entity_id) not in existing_ids:
            with open(simple_file_path, 'a') as f:
                f.write(f"{entity_id}\n")
        
        logger.debug(f"Wrote error information for {entity_type} {entity_id} to {file_path}")
    
    except Exception as e:
        logger.error(f"Error writing error information to file: {e}", exc_info=True)


def log_batch_errors(
    entity_type: str,
    errors: List[Dict[str, Any]],
    file_suffix: str = "public"
) -> None:
    """
    Log a batch of errors for entities of the same type.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        errors: List of error dictionaries
        file_suffix: Suffix for the error log file
    """
    try:
        # Ensure error log directory exists
        error_log_dir = ensure_error_log_dir()
        
        # Determine file path
        file_name = f"failed_{entity_type.lower()}s_{file_suffix}.json"
        file_path = os.path.join(error_log_dir, file_name)
        
        # Load existing errors if file exists
        existing_errors = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    existing_errors = json.load(f)
                    if not isinstance(existing_errors, list):
                        existing_errors = []
            except json.JSONDecodeError:
                # If file exists but is not valid JSON, start with empty list
                existing_errors = []
        
        # Add new errors
        existing_errors.extend(errors)
        
        # Write errors to file
        with open(file_path, 'w') as f:
            json.dump(existing_errors, f, indent=2)
        
        # Also write to simple ID list for backward compatibility
        simple_file_name = f"failed_{entity_type.lower()}s_{file_suffix}.txt"
        simple_file_path = os.path.join(error_log_dir, simple_file_name)
        
        # Get existing IDs
        existing_ids = set()
        if os.path.exists(simple_file_path):
            with open(simple_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_ids.add(line)
        
        # Add new IDs if not already present
        with open(simple_file_path, 'a') as f:
            for error in errors:
                entity_id = error.get("entity_id")
                if entity_id and str(entity_id) not in existing_ids:
                    f.write(f"{entity_id}\n")
                    existing_ids.add(str(entity_id))
        
        logger.debug(f"Wrote {len(errors)} error records for {entity_type} to {file_path}")
    
    except Exception as e:
        logger.error(f"Error writing batch errors to file: {e}", exc_info=True)


def get_entity_errors(
    entity_type: str,
    file_suffix: str = "public"
) -> List[Dict[str, Any]]:
    """
    Get all errors for a specific entity type.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        file_suffix: Suffix for the error log file
        
    Returns:
        List[Dict[str, Any]]: List of error dictionaries
    """
    try:
        # Ensure error log directory exists
        error_log_dir = ensure_error_log_dir()
        
        # Determine file path
        file_name = f"failed_{entity_type.lower()}s_{file_suffix}.json"
        file_path = os.path.join(error_log_dir, file_name)
        
        # Load errors if file exists
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    errors = json.load(f)
                    if not isinstance(errors, list):
                        return []
                    return errors
            except json.JSONDecodeError:
                return []
        
        return []
    
    except Exception as e:
        logger.error(f"Error reading error information from file: {e}", exc_info=True)
        return []


def get_entity_error_ids(
    entity_type: str,
    file_suffix: str = "public"
) -> List[str]:
    """
    Get IDs of all entities with errors.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        file_suffix: Suffix for the error log file
        
    Returns:
        List[str]: List of entity IDs
    """
    try:
        # Ensure error log directory exists
        error_log_dir = ensure_error_log_dir()
        
        # Determine file path
        file_name = f"failed_{entity_type.lower()}s_{file_suffix}.txt"
        file_path = os.path.join(error_log_dir, file_name)
        
        # Load IDs if file exists
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        
        return []
    
    except Exception as e:
        logger.error(f"Error reading error IDs from file: {e}", exc_info=True)
        return []


def clear_entity_errors(
    entity_type: str,
    file_suffix: str = "public"
) -> None:
    """
    Clear all errors for a specific entity type.
    
    Args:
        entity_type: Type of entity (quote, order, contact, etc.)
        file_suffix: Suffix for the error log file
    """
    try:
        # Ensure error log directory exists
        error_log_dir = ensure_error_log_dir()
        
        # Determine file paths
        json_file_name = f"failed_{entity_type.lower()}s_{file_suffix}.json"
        json_file_path = os.path.join(error_log_dir, json_file_name)
        
        txt_file_name = f"failed_{entity_type.lower()}s_{file_suffix}.txt"
        txt_file_path = os.path.join(error_log_dir, txt_file_name)
        
        # Remove files if they exist
        if os.path.exists(json_file_path):
            os.remove(json_file_path)
        
        if os.path.exists(txt_file_path):
            os.remove(txt_file_path)
        
        logger.info(f"Cleared error logs for {entity_type}")
    
    except Exception as e:
        logger.error(f"Error clearing error logs: {e}", exc_info=True)