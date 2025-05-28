import json
from typing import Any, Optional, Dict, Union
from pathlib import Path
import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass

class ConfigLoader:
    """Configuration loader class with support for defaults and validation."""
    
    def __init__(
        self,
        config_path: Union[str, Path] = "config.json",
        default_config: Optional[Dict[str, Any]] = None,
        required_fields: Optional[list[str]] = None
    ):
        self.config_path = Path(config_path)
        self.default_config = default_config or {}
        self.required_fields = required_fields or []
        self._config: Optional[Dict[str, Any]] = None

    @lru_cache(maxsize=1)
    def load_config(self, reload: bool = False) -> Dict[str, Any]:
        """
        Load configuration from a JSON file with caching support.
        
        Args:
            reload: Force reload configuration from disk
            
        Returns:
            dict: Merged configuration data (file config + defaults)
            
        Raises:
            ConfigurationError: If config loading fails or validation fails
        """
        if self._config is not None and not reload:
            return self._config

        # Get the scripts directory
        scripts_dir = Path(__file__).parent.parent
        config_file = scripts_dir / self.config_path
        
        try:
            with open(config_file) as f:
                file_config = json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found at {config_file}, using defaults")
            file_config = {}
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        
        # Merge with defaults
        self._config = {**self.default_config, **file_config}
        
        # Validate required fields
        missing_fields = [field for field in self.required_fields 
                         if field not in self._config]
        if missing_fields:
            raise ConfigurationError(
                f"Missing required configuration fields: {', '.join(missing_fields)}"
            )
            
        logger.info(f"Loaded config from {config_file}")
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Safely get a configuration value.
        
        Args:
            key: Configuration key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        config = self.load_config()
        return config.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-like access to configuration values."""
        config = self.load_config()
        return config[key]

# Default configuration
DEFAULT_CONFIG = {
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "retry": {
        "max_attempts": 3,
        "delay": 1.0
    }
}

# Required configuration fields
REQUIRED_FIELDS = [
    "logging.level"
]

# Create a global config instance
config_loader = ConfigLoader(
    default_config=DEFAULT_CONFIG,
    required_fields=REQUIRED_FIELDS
)

# Provide a simple interface for importing
get_config = config_loader.load_config
get = config_loader.get