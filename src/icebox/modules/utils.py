import json
from typing import Any
from modules.logger import Logger
from modules.config_store import ConfigStore


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value from the ConfigStore singleton."""
    return ConfigStore().get(key, default)
