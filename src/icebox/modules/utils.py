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


def get_config(config_path: str) -> dict:
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config
