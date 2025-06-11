"""
S3 integration for the pipeline framework.

This module provides components for integrating the pipeline with AWS S3,
including loaders for uploading data to S3 buckets.
"""

import os
import json
import csv
import tempfile
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from scripts.pipeline.base import LoadingStage
from scripts.pipeline.exceptions import LoadingError

# Import boto3 for AWS S3 integration
try:
    import boto3
    from botocore.exceptions import ClientError
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False


class S3Loader(LoadingStage[List[Dict[str, Any]]]):
    """
    Loader for saving data to CSV files in S3.
    
    This loader saves a list of dictionaries to a CSV file in an S3 bucket.
    """
    
    def __init__(self, bucket_name: str, object_key: str, 
                 region_name: Optional[str] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 name: str = "s3_csv_loader"):
        """
        Initialize the S3 CSV loader.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key (path) of the object in the bucket
            region_name: AWS region name (optional, uses environment or config if not provided)
            aws_access_key_id: AWS access key ID (optional, uses environment or config if not provided)
            aws_secret_access_key: AWS secret access key (optional, uses environment or config if not provided)
            name: Name of the loader
        """
        super().__init__(name)
        
        if not S3_AVAILABLE:
            raise ImportError("boto3 is required for S3 integration. Install it with 'pip install boto3'.")
        
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        
        # Create S3 client
        self.s3_client = self._create_s3_client()
    
    def _create_s3_client(self):
        """
        Create an S3 client with the provided credentials.
        
        Returns:
            boto3.client: S3 client
        """
        kwargs = {}
        if self.region_name:
            kwargs['region_name'] = self.region_name
        if self.aws_access_key_id and self.aws_secret_access_key:
            kwargs['aws_access_key_id'] = self.aws_access_key_id
            kwargs['aws_secret_access_key'] = self.aws_secret_access_key
        
        return boto3.client('s3', **kwargs)
    
    async def load(self, data: List[Dict[str, Any]]) -> None:
        """
        Load data to a CSV file in S3.
        
        Args:
            data: List of dictionaries to save
        """
        try:
            if not data:
                self.record_metric("rows_written", 0)
                return
            
            # Create a temporary file to store the CSV
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='', encoding='utf-8') as temp_file:
                # Get fieldnames from the first item
                fieldnames = list(data[0].keys())
                
                # Write to CSV
                writer = csv.DictWriter(temp_file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
                temp_file_path = temp_file.name
            
            # Upload the file to S3
            try:
                self.s3_client.upload_file(temp_file_path, self.bucket_name, self.object_key)
                
                # Record metrics
                self.record_metric("rows_written", len(data))
                self.record_metric("bucket_name", self.bucket_name)
                self.record_metric("object_key", self.object_key)
                self.record_metric("loading_success", True)
            except ClientError as e:
                # Record metrics
                self.record_metric("loading_success", False)
                self.record_metric("loading_error", str(e))
                
                # Raise a LoadingError
                raise LoadingError(
                    f"Error uploading to S3: {str(e)}", 
                    data=data, 
                    destination=f"s3://{self.bucket_name}/{self.object_key}"
                )
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            # Record metrics
            self.record_metric("loading_success", False)
            self.record_metric("loading_error", str(e))
            
            # Raise a LoadingError
            raise LoadingError(
                f"Error loading data to S3: {str(e)}", 
                data=data, 
                destination=f"s3://{self.bucket_name}/{self.object_key}"
            )


class S3JSONLoader(LoadingStage[Dict[str, Any]]):
    """
    Loader for saving data to JSON files in S3.
    
    This loader saves a dictionary to a JSON file in an S3 bucket.
    """
    
    def __init__(self, bucket_name: str, object_key: str, 
                 region_name: Optional[str] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 name: str = "s3_json_loader"):
        """
        Initialize the S3 JSON loader.
        
        Args:
            bucket_name: Name of the S3 bucket
            object_key: Key (path) of the object in the bucket
            region_name: AWS region name (optional, uses environment or config if not provided)
            aws_access_key_id: AWS access key ID (optional, uses environment or config if not provided)
            aws_secret_access_key: AWS secret access key (optional, uses environment or config if not provided)
            name: Name of the loader
        """
        super().__init__(name)
        
        if not S3_AVAILABLE:
            raise ImportError("boto3 is required for S3 integration. Install it with 'pip install boto3'.")
        
        self.bucket_name = bucket_name
        self.object_key = object_key
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        
        # Create S3 client
        self.s3_client = self._create_s3_client()
    
    def _create_s3_client(self):
        """
        Create an S3 client with the provided credentials.
        
        Returns:
            boto3.client: S3 client
        """
        kwargs = {}
        if self.region_name:
            kwargs['region_name'] = self.region_name
        if self.aws_access_key_id and self.aws_secret_access_key:
            kwargs['aws_access_key_id'] = self.aws_access_key_id
            kwargs['aws_secret_access_key'] = self.aws_secret_access_key
        
        return boto3.client('s3', **kwargs)
    
    async def load(self, data: Dict[str, Any]) -> None:
        """
        Load data to a JSON file in S3.
        
        Args:
            data: Dictionary to save
        """
        try:
            # Create a temporary file to store the JSON
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json', encoding='utf-8') as temp_file:
                # Write to JSON
                json.dump(data, temp_file, indent=2)
                temp_file_path = temp_file.name
            
            # Upload the file to S3
            try:
                self.s3_client.upload_file(temp_file_path, self.bucket_name, self.object_key)
                
                # Record metrics
                self.record_metric("bucket_name", self.bucket_name)
                self.record_metric("object_key", self.object_key)
                self.record_metric("loading_success", True)
            except ClientError as e:
                # Record metrics
                self.record_metric("loading_success", False)
                self.record_metric("loading_error", str(e))
                
                # Raise a LoadingError
                raise LoadingError(
                    f"Error uploading to S3: {str(e)}", 
                    data=data, 
                    destination=f"s3://{self.bucket_name}/{self.object_key}"
                )
            finally:
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
        except Exception as e:
            # Record metrics
            self.record_metric("loading_success", False)
            self.record_metric("loading_error", str(e))
            
            # Raise a LoadingError
            raise LoadingError(
                f"Error loading data to S3: {str(e)}", 
                data=data, 
                destination=f"s3://{self.bucket_name}/{self.object_key}"
            )