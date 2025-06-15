"""
Data processors for orders and order items in the pipeline framework.

This module provides processors for acquiring, validating, and transforming
order and order item data from the Paperless Parts API.
"""

import asyncio
import re
from typing import Any, Dict, List, Optional, Union, TypeVar, Generic

from scripts.pipeline.base import DataAcquisitionStage, TransformationStage, ValidationStage
from scripts.pipeline.exceptions import TransformationError, ValidationError
from scripts.utils.logging_config import get_logger
from scripts.utils.utils import safe_get

# Get logger for this module
logger = get_logger(__name__)

# Type variables for generic stages
T = TypeVar('T')
U = TypeVar('U')


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