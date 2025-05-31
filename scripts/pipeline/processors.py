"""
Data processors for the pipeline framework.

This module provides processors for transforming and enriching data
as it flows through the pipeline.
"""

import csv
import os
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from scripts.pipeline.base import TransformationStage, LoadingStage
from scripts.pipeline.exceptions import TransformationError, LoadingError


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
                    "quote_number": quote_number,
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
                        item_with_quantity.update({
                            "quantity": q.get("quantity", 0),
                            "unit_price": q.get("unit_price", 0),
                            "total_price": q.get("total_price", 0),
                            "total_price_with_add_ons": q.get("total_price_with_required_add_ons", 0),
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