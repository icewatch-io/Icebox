import json
from typing import Any
from modules.logger import Logger
from modules.config_store import ConfigStore


def validate_config(config: dict, required_keys: list) -> None:
    """
    Validate the configuration dictionary.

    :param config: Configuration dictionary.
    :param required_keys: List of required keys.
    :raises ValueError: If the configuration is invalid.
    """
    missing_keys = []
    for key in required_keys:
        if key not in config:
            missing_keys.append(key)
    if len(missing_keys) > 0:
        raise ValueError(f"Missing required config keys: {missing_keys}")


def get_config(config_path: str) -> dict:
    """Load configuration from file."""
    logger = Logger.get_logger('utils')
    logger.debug(f"Loading config from {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.debug(f"Successfully loaded config with keys: {list(config.keys())}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        raise


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value from the ConfigStore singleton."""
    return ConfigStore().get(key, default)
