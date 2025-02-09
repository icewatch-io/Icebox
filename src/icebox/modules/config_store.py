import json
from typing import Optional, Dict
import threading


class ConfigStore:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigStore, cls).__new__(cls)
                cls._instance._config = None
                cls._instance._observers = []
            return cls._instance

    def __init__(self):
        pass

    def load_config(self, config_path: str) -> None:
        """Load initial config from file."""
        with open(config_path) as f:
            self.update_config(json.load(f))

    def update_config(self, new_config: Dict) -> None:
        """Update the current config and notify observers."""
        with self._lock:
            self._config = new_config
            self._notify_observers()

    def get_config(self) -> Optional[Dict]:
        """Get the current config."""
        with self._lock:
            return self._config

    def add_observer(self, callback) -> None:
        """Add an observer to be notified of config changes."""
        with self._lock:
            self._observers.append(callback)

    def remove_observer(self, callback) -> None:
        """Remove an observer."""
        with self._lock:
            self._observers.remove(callback)

    def _notify_observers(self) -> None:
        """Notify all observers of config change."""
        for observer in self._observers:
            observer(self._config)
