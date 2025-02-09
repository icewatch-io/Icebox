import json


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


def get_config() -> dict:
    """Get the current config from the ConfigStore singleton."""
    from .config_store import ConfigStore
    config_store = ConfigStore()
    return config_store.get_config()
