import json
import hashlib
import queue
import time
import threading
import requests
import logging
from typing import Optional
from pathlib import Path

from icepick import Icepick
from modules.config_store import ConfigStore
from modules.logger import Logger
from modules.alerter import Alert
from modules.utils import get_raw_http

ALERT_ENDPOINT = "alert"


class IcewatchClient:
    _instance = None
    _lock = threading.Lock()
    _alert_queue = queue.Queue()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IcewatchClient, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(
        self,
        api_url: str = None,
        device_id: str = None,
        api_key: str = None,
        config_store: Optional[ConfigStore] = None,
    ):
        """Initialize Icewatch client."""
        if self.initialized:
            return

        if not all([api_url, device_id, api_key]):
            raise ValueError("All initialization parameters are required")

        self.api_url = api_url.rstrip("/")
        self.device_id = device_id
        self.api_key = api_key
        self.error_count = 0
        self.default_config_path = Path("/etc/icebox/config.json")
        self.cached_config_path = Path("/etc/icebox/config-icewatch.json")
        self.logger = Logger.get_logger("icewatch")
        self.initial_config_event = threading.Event()
        self.alert_queue = self._alert_queue

        # Use provided ConfigStore or create new one
        self.logger.info("Setting up configuration store")
        self.config_store = config_store or ConfigStore()
        self.shutdown_flag = self.config_store.shutdown_flag
        config = self.config_store.get("icepick", [])
        smtp_config = self.config_store.get("smtp")

        # Create and configure Icepick after ConfigStore is ready
        self.icepick = Icepick(shutdown_flag=self.shutdown_flag)
        if config:
            self.icepick.set_connections(config)
        if smtp_config:
            self.icepick.alerter.configure_smtp(smtp_config)

        # Set up config watchers
        self.config_store.watch("icepick", self.icepick.set_connections)
        self.config_store.watch(
            "smtp", lambda config: self.icepick.alerter.configure_smtp(config)
        )

        self.initialized = True

    @classmethod
    def queue_alert(
        cls, source: str, subject: str, body: str, idempotency_token: str
    ) -> bool:
        """Queue an alert for sending to Icewatch.

        Args:
            source: The source/module generating the alert
            subject: Alert subject line
            body: Alert message body
            idempotency_token: A unique ID

        Returns:
            bool: True if alert was queued successfully
        """
        try:
            alert = Alert(
                source=source,
                subject=subject,
                body=body,
                timestamp=time.time(),
                idempotency_token=idempotency_token,
            )
            cls._alert_queue.put(alert)
            return True
        except Exception:
            return False

    def _get_queued_alerts(self, max_alerts: int = 100) -> list[Alert]:
        """Get queued alerts for processing."""
        alerts = []
        try:
            while len(alerts) < max_alerts and not self._alert_queue.empty():
                alerts.append(self._alert_queue.get_nowait())
        except queue.Empty:
            pass
        return alerts

    def _read_config(self) -> Optional[dict]:
        """Read and parse local config file.

        Returns config from either disk or the config store."""
        try:
            return self.config_store.get_config()
        except (KeyError, TypeError):
            pass

        try:
            if self.cached_config_path.exists():
                with open(self.cached_config_path) as f:
                    return json.load(f)
            if self.default_config_path.exists():
                with open(self.default_config_path) as f:
                    return json.load(f)
            return None
        except json.JSONDecodeError:
            return None

    def _write_config(self, config: dict) -> None:
        """Write config to cache file and update global store."""
        with open(self.cached_config_path, "w") as f:
            json.dump(config, f, indent=2)
        self.config_store.update_config(config)
        self.initial_config_event.set()

    def _get_config_hash(self, config: Optional[dict]) -> str:
        """Generate SHA-256 hash of config JSON string."""
        if config is None:
            return ""
        config_str = json.dumps(config, separators=(",", ":"))
        config_hash = hashlib.sha256(config_str.encode("utf-8")).hexdigest()
        return config_hash

    def _load_cached_config(self) -> bool:
        """Load config from cache file."""
        try:
            if self.cached_config_path.exists():
                self.logger.info("Loading cached Icewatch config")
                with open(self.cached_config_path) as f:
                    config = json.load(f)
                self.config_store.update_config(config)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error loading cached config: {e}")
            return False

    def wait_for_initial_config(self, timeout: int = 30) -> bool:
        """Wait for initial config to be received."""
        return self.initial_config_event.wait(timeout)

    def _format_alerts_data(self, alerts: list[Alert]) -> dict:
        """Format alerts for the Icewatch API."""
        formatted_alerts = []
        idempotency_tokens = []
        for alert in alerts:
            if alert.idempotency_token in idempotency_tokens:
                continue
            idempotency_tokens.append(alert.idempotency_token)
            formatted_alerts.append(
                {
                    "source": alert.source,
                    "subject": alert.subject,
                    "body": alert.body,
                    "timestamp": alert.timestamp,
                    "idempotencyToken": alert.idempotency_token,
                }
            )

        return {
            "id": self.device_id,
            "alerts": formatted_alerts,
        }

    def _make_api_request(
        self, endpoint: str, method: str, data: dict = None, headers: dict = None
    ) -> dict:
        """Make an API request to the Icebox server."""

        request_headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        if headers:
            request_headers.update(headers)

        response = requests.request(
            method=method,
            url=f"{self.api_url}/{endpoint}",
            headers=request_headers,
            json=data,
            timeout=30,
        )

        if self.logger.isEnabledFor(logging.DEBUG):
            raw_request, raw_response = get_raw_http(response)
            self.logger.debug(
                f"\nHTTP Request:\n{raw_request}\n\n" f"HTTP Response:\n{raw_response}"
            )

        return response

    def check_in(self) -> bool:
        """Perform check-in with Icebox server.

        Returns:
            bool: True if check-in was successful
        """
        current_config = self._read_config()
        config_hash = self._get_config_hash(current_config)

        icepick_results = self.icepick.get_latest_results()
        data = {
            "id": self.device_id,
            "configHash": config_hash,
            "icepickResults": icepick_results,
        }

        try:
            response = self._make_api_request(
                endpoint="check-in",
                method="POST",
                data=data,
            )

            if response.status_code == 200:
                response_data = response.json()

                if "config" in response_data:
                    new_config = response_data["config"]
                    self._write_config(new_config)

                self.icepick.latest_results.clear()

                return True

            elif response.status_code == 401:
                message = "Authentication failed. Please check your API key."
                self.logger.error(message)
                raise Exception(message)
            else:
                message = (
                    f"Check in failed: {response.json().get('error', 'Unknown error')}"
                )
                self.logger.error(message)
                raise Exception(message)

        except requests.RequestException as e:
            message = f"Network error during check in: {str(e)}"
            self.logger.error(message)
            raise Exception(message)

        return False

    def send_alerts(self) -> bool:
        """Send queued alerts to Icewatch server."""
        alerts = self._get_queued_alerts(max_alerts=100)
        if not alerts:
            return True

        data = self._format_alerts_data(alerts)

        try:
            response = self._make_api_request(
                endpoint=ALERT_ENDPOINT, method="POST", data=data
            )

            if response.status_code == 200:
                self.logger.info(f"Successfully sent {len(alerts)} alerts")
                return True
            else:
                self.logger.error(f"Failed to send alerts: {response.status_code}")
                for alert in alerts:
                    self._alert_queue.put(alert)
                return False

        except requests.RequestException as e:
            self.logger.error(f"Network error sending alerts: {e}")
            for alert in alerts:
                self._alert_queue.put(alert)
            return False

    def run(self) -> None:
        """Run the Icewatch client loop."""
        self.logger.info("Starting Icewatch client")
        last_alert_time = 0
        last_check_in_time = 0

        while not self.shutdown_flag.is_set():
            try:
                current_time = time.time()

                if current_time - last_check_in_time >= 60:
                    last_check_in_time = current_time
                    self.check_in()

                if current_time - last_alert_time >= 10:
                    last_alert_time = current_time
                    self.send_alerts()

            except Exception as e:
                self.error_count += 1
                self.logger.error(f"Error in Icewatch loop: {e}")
                self.logger.error(f"Error count: {self.error_count}")

            time.sleep(1)

    def stop(self) -> None:
        """Stop the Icewatch client."""
        self.logger.info("Stopping Icewatch client")
        self.shutdown_flag.set()
