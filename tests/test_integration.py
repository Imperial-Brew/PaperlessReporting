import pytest
import os
import csv
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import json

from scripts.pull_users import main as pull_users_main
from scripts.utils.config_loader import ConfigLoader

@pytest.fixture
def mock_users_response():
    """Mock response for users API endpoint."""
    return [
        {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "role": "Admin"
        },
        {
            "id": 2,
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
            "role": "Sales"
        }
    ]

@pytest.fixture
def mock_config():
    """Mock configuration."""
    return {
        "api_key": "test_api_key",
        "api_base_url": "https://api.test.com",
        "logging": {
            "level": "INFO"
        }
    }

class MockResponse:
    """Mock HTTP response."""
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        
    def json(self):
        return self.json_data
        
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")

def test_pull_users_end_to_end(mock_users_response, mock_config, tmp_path):
    """Test the end-to-end flow of pulling users and writing to CSV."""
    # Mock the requests.get function
    with patch('requests.get', return_value=MockResponse(mock_users_response)):
        # Mock the config loader
        with patch.object(ConfigLoader, 'load_config', return_value=mock_config):
            # Create a temporary directory for output
            data_dir = tmp_path / "data_raw" / "users" / "public"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Mock the output path
            with patch('pathlib.Path', side_effect=lambda *args: tmp_path / args[0] if args else tmp_path):
                # Run the main function
                pull_users_main()
                
                # Check that the CSV file was created
                csv_file = data_dir / "users_all.csv"
                assert csv_file.exists()
                
                # Read the CSV file and verify its contents
                with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    # Verify the number of rows
                    assert len(rows) == 2
                    
                    # Verify the content of the rows
                    assert rows[0]['id'] == '1'
                    assert rows[0]['first_name'] == 'John'
                    assert rows[0]['last_name'] == 'Doe'
                    assert rows[0]['email'] == 'john@example.com'
                    assert rows[0]['role'] == 'Admin'
                    
                    assert rows[1]['id'] == '2'
                    assert rows[1]['first_name'] == 'Jane'
                    assert rows[1]['last_name'] == 'Smith'
                    assert rows[1]['email'] == 'jane@example.com'
                    assert rows[1]['role'] == 'Sales'

def test_pull_users_with_pagination(mock_config, tmp_path):
    """Test pulling users with pagination."""
    # Create paginated responses
    first_response = {
        "results": [{"id": 1, "first_name": "John", "last_name": "Doe"}],
        "next": "next_url"
    }
    second_response = {
        "results": [{"id": 2, "first_name": "Jane", "last_name": "Smith"}],
        "next": None
    }
    
    # Mock the requests.get function to return different responses
    mock_responses = [
        MockResponse(first_response),
        MockResponse(second_response)
    ]
    
    with patch('requests.get', side_effect=mock_responses):
        # Mock the config loader
        with patch.object(ConfigLoader, 'load_config', return_value=mock_config):
            # Create a temporary directory for output
            data_dir = tmp_path / "data_raw" / "users" / "public"
            data_dir.mkdir(parents=True, exist_ok=True)
            
            # Mock the output path
            with patch('pathlib.Path', side_effect=lambda *args: tmp_path / args[0] if args else tmp_path):
                # Run the main function
                pull_users_main()
                
                # Check that the CSV file was created
                csv_file = data_dir / "users_all.csv"
                assert csv_file.exists()
                
                # Read the CSV file and verify its contents
                with open(csv_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
                    
                    # Verify the number of rows
                    assert len(rows) == 2
                    
                    # Verify the content of the rows
                    assert rows[0]['id'] == '1'
                    assert rows[0]['first_name'] == 'John'
                    
                    assert rows[1]['id'] == '2'
                    assert rows[1]['first_name'] == 'Jane'

def test_pull_users_error_handling(mock_config):
    """Test error handling when pulling users."""
    # Mock the requests.get function to raise an exception
    with patch('requests.get', side_effect=Exception("API Error")):
        # Mock the config loader
        with patch.object(ConfigLoader, 'load_config', return_value=mock_config):
            # Mock print to capture output
            with patch('builtins.print') as mock_print:
                # Run the main function
                pull_users_main()
                
                # Verify that the error was handled
                mock_print.assert_any_call("❌ Failed to fetch users: API Error")