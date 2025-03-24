import json
import threading
from typing import Dict, Any, Callable, Set

from modules.logger import Logger


class ConfigStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, shutdown_flag: threading.Event = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigStore, cls).__new__(cls)
                cls._instance._config = {}
                cls._instance._observers = {}
                cls._instance.logger = Logger.get_logger('config')
                cls._instance.shutdown_flag = shutdown_flag or threading.Event()
                cls._instance.logger.debug("Created new ConfigStore instance")
            return cls._instance

    def load_config(self, config_path: str) -> None:
        """Load initial config from file."""
        self.logger.debug(f"Loading config from {config_path}")
        with open(config_path) as f:
            self.update_config(json.load(f))

    def update_config(self, new_config: Dict) -> None:
        """Update the current config and notify relevant observers."""
        with self._lock:
            old_config = self._config
            self._config = new_config
            self._notify_observers(old_config, new_config)

    def get_config(self) -> Dict:
        """Get the current config."""
        with self._lock:
            return self._config.copy()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key path (e.g. 'smtp.server')."""
        with self._lock:
            try:
                value = self._config
                for k in key.split('.'):
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default

    def watch(self, key: str, callback: Callable[[Any], None]) -> None:
        """Register to be notified when a specific config key changes."""
        with self._lock:
            if key not in self._observers:
                self._observers[key] = set()
            self._observers[key].add(callback)
            self.logger.debug(f"Added observer for {key}: {callback.__qualname__}")

    def unwatch(self, key: str, callback: Callable[[Any], None]) -> None:
        """Remove a config watch callback."""
        with self._lock:
            if key in self._observers:
                self._observers[key].discard(callback)
                if not self._observers[key]:
                    del self._observers[key]

    def _notify_observers(self, old_config: Dict, new_config: Dict) -> None:
        """Notify observers of relevant config changes."""
        def get_value(config: Dict, key: str) -> Any:
            try:
                value = config
                for k in key.split('.'):
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return None

        for key, observers in self._observers.items():
            old_value = get_value(old_config, key)
            new_value = get_value(new_config, key)

            if old_value != new_value:
                self.logger.debug(f"Config change for {key}: {old_value} -> {new_value}")
                for callback in observers:
                    try:
                        callback(new_value)
                    except Exception as e:
                        self.logger.error(f"Error in config observer {callback.__qualname__}: {e}")
