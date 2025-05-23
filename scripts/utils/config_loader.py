import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.json") -> dict:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the config file, relative to the scripts directory
        
    Returns:
        dict: Configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    # Get the scripts directory
    scripts_dir = Path(__file__).parent.parent
    config_file = scripts_dir / config_path
    
    try:
        with open(config_file) as f:
            config = json.load(f)
            logger.info(f"Loaded config from {config_file}")
            return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_file}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        raise

# Load config when module is imported
try:
    config = load_config()
except Exception as e:
    logger.error(f"Failed to load config: {e}")
    raise
