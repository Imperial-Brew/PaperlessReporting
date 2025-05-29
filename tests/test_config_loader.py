import pytest
import json
import os
from unittest.mock import patch, mock_open
from pathlib import Path

from scripts.utils.config_loader import (
    ConfigLoader, 
    ConfigurationError,
    config_loader,
    get_config,
    get
)

@pytest.fixture
def sample_config():
    return {
        "api_key": "test_key",
        "api_base_url": "https://api.test.com",
        "logging": {
            "level": "DEBUG"
        }
    }

@pytest.fixture
def default_config():
    return {
        "retry": {
            "max_attempts": 3,
            "delay": 1.0
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }

def test_load_config_from_file(sample_config):
    """Test loading configuration from a file."""
    with patch("builtins.open", mock_open(read_data=json.dumps(sample_config))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader()
            config = loader.load_config()
            
            assert config["api_key"] == "test_key"
            assert config["api_base_url"] == "https://api.test.com"
            assert config["logging"]["level"] == "DEBUG"

def test_merge_with_defaults(sample_config, default_config):
    """Test merging file configuration with defaults."""
    with patch("builtins.open", mock_open(read_data=json.dumps(sample_config))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader(default_config=default_config)
            config = loader.load_config()
            
            # From file config
            assert config["api_key"] == "test_key"
            assert config["api_base_url"] == "https://api.test.com"
            assert config["logging"]["level"] == "DEBUG"  # Overridden from default
            
            # From default config
            assert config["retry"]["max_attempts"] == 3
            assert config["retry"]["delay"] == 1.0
            assert config["logging"]["format"] == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

def test_required_fields_validation():
    """Test validation of required fields."""
    empty_config = {}
    with patch("builtins.open", mock_open(read_data=json.dumps(empty_config))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader(required_fields=["api_key", "api_base_url"])
            
            with pytest.raises(ConfigurationError) as excinfo:
                loader.load_config()
            
            assert "Missing required configuration fields" in str(excinfo.value)
            assert "api_key" in str(excinfo.value)
            assert "api_base_url" in str(excinfo.value)

def test_nested_required_fields_validation(default_config):
    """Test validation of nested required fields using dot notation."""
    with patch("builtins.open", mock_open(read_data=json.dumps({}))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader(
                default_config=default_config,
                required_fields=["logging.level", "logging.format", "missing.field"]
            )
            
            with pytest.raises(ConfigurationError) as excinfo:
                loader.load_config()
            
            assert "Missing required configuration fields" in str(excinfo.value)
            assert "missing.field" in str(excinfo.value)
            assert "logging.level" not in str(excinfo.value)  # This is in default_config

def test_file_not_found():
    """Test handling of missing configuration file."""
    with patch("builtins.open", side_effect=FileNotFoundError()):
        with patch("pathlib.Path.exists", return_value=False):
            loader = ConfigLoader(default_config={"default": "value"})
            config = loader.load_config()
            
            assert config == {"default": "value"}

def test_invalid_json():
    """Test handling of invalid JSON in configuration file."""
    with patch("builtins.open", mock_open(read_data="invalid json")):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader()
            
            with pytest.raises(ConfigurationError) as excinfo:
                loader.load_config()
            
            assert "Invalid JSON in config file" in str(excinfo.value)

def test_get_method(sample_config):
    """Test the get method for accessing configuration values."""
    with patch("builtins.open", mock_open(read_data=json.dumps(sample_config))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader()
            
            assert loader.get("api_key") == "test_key"
            assert loader.get("non_existent", "default") == "default"

def test_getitem_method(sample_config):
    """Test dictionary-like access to configuration values."""
    with patch("builtins.open", mock_open(read_data=json.dumps(sample_config))):
        with patch("pathlib.Path.exists", return_value=True):
            loader = ConfigLoader()
            
            assert loader["api_key"] == "test_key"
            
            with pytest.raises(KeyError):
                _ = loader["non_existent"]

def test_global_config_loader():
    """Test the global config_loader instance."""
    test_config = {"api_key": "global_test", "logging": {"level": "DEBUG"}}
    
    with patch("builtins.open", mock_open(read_data=json.dumps(test_config))):
        with patch("pathlib.Path.exists", return_value=True):
            # Test get_config function
            config = get_config()
            assert config["api_key"] == "global_test"
            
            # Test get function
            assert get("api_key") == "global_test"
            assert get("non_existent", "default") == "default"