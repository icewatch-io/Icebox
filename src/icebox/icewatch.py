import json
import hashlib
import requests
from typing import Optional
from pathlib import Path

from modules.config_store import ConfigStore
from modules.logger import Logger


class IcewatchClient:
    def __init__(self, api_url: str, device_id: str, api_key: str, config_path: str):
        """Initialize Icebox client.

        Args:
            api_url: Base URL for Icebox API
            device_id: Device's unique identifier
            api_key: Device's API key for authentication
            config_path: Path to local config file
        """
        self.api_url = api_url.rstrip('/')
        self.device_id = device_id
        self.config_store = ConfigStore()
        self.api_key = api_key
        self.config_path = Path(config_path)
        self.logger = Logger.get_logger('icewatch')

    def _read_config(self) -> Optional[dict]:
        """Read and parse local config file.

        Returns config from either disk or the config store."""
        store_config = self.config_store.get_config()
        if store_config:
            return store_config
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    return json.load(f)
            return None
        except json.JSONDecodeError:
            return None

    def _write_config(self, config: dict) -> None:
        """Write config to local file and update global store."""
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
        self.config_store.update_config(config)

    def _get_config_hash(self, config: Optional[dict]) -> str:
        """Generate SHA-256 hash of config JSON string."""
        if config is None:
            return ''
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def check_in(self) -> bool:
        """Perform check-in with Icebox server.

        Returns:
            bool: True if check-in was successful
        """
        current_config = self._read_config()
        config_hash = self._get_config_hash(current_config)

        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

        data = {
            'id': self.device_id,
            'configHash': config_hash
        }

        self.logger.info(f"Sending check-in request to {self.api_url}/check-in")
        self.logger.debug(f"data: {data}")

        try:
            response = requests.post(
                f'{self.api_url}/check-in',
                headers=headers,
                json=data
            )

            if response.status_code == 200:
                response_data = response.json()

                if 'config' in response_data:
                    new_config = json.loads(response_data['config'])
                    self._write_config(new_config)

                return True

            elif response.status_code == 401:
                message = "Authentication failed. Please check your API key."
                self.logger.error(message)
                raise Exception(message)
            else:
                message = f"Check-in failed: {response.json().get('error', 'Unknown error')}"
                self.logger.error(message)
                raise Exception(message)

        except requests.RequestException as e:
            message = f"Network error during check-in: {str(e)}"
            self.logger.error(message)
            raise Exception(message)

        return False
