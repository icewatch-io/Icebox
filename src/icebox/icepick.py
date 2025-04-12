import socket
import time
import random
import threading
import sys

from modules.alerter import Alerter
from modules.logger import Logger



class Icepick:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, shutdown_flag: threading.Event = None) -> None:
        if not Icepick._initialized:
            self.shutdown_flag = shutdown_flag or threading.Event()
            self._results_lock = threading.Lock()
            self.latest_results = []
            self.connections = []

            self.logger = Logger.get_logger('icepick')
            self.alerter = Alerter()
            Icepick._initialized = True

    def _handle_smtp_config_change(self, new_config: dict) -> None:
        """Handle changes to SMTP configuration."""
        if hasattr(self, 'alerter'):
            self.logger.info("Updating SMTP configuration")
            self.alerter.configure_smtp(new_config)

    def _handle_icepick_config_change(self, new_config: list) -> None:
        """Handle changes to Icepick configuration."""
        self.logger.info(f"Icepick configuration updated: {new_config}")

    def stop(self) -> None:
        self.logger.info('Stopping icepick')
        self.shutdown_flag.set()

    def set_connections(self, connections: list) -> None:
        """Update the list of connections to monitor."""
        self.connections = connections

    def run(self) -> None:
        self.logger.info('Starting icepick')
        while not self.shutdown_flag.is_set():
            results = []
            for connection in self.connections:
                result = self.process_connection(connection)
                if result:
                    results.append(result)
            with self._results_lock:
                self.latest_results += results
            time.sleep(random.randint(60, 90))

    def check_tcp(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except Exception as e:
            return False

    def get_latest_results(self) -> list:
        """Get the latest monitoring results in a thread-safe way."""
        with self._results_lock:
            return self.latest_results.copy()

    def process_connection(self, connection: dict) -> dict:
        failure_action = connection['failure_action']
        success_action = connection['success_action']
        connection_status = self.check_tcp(
            host=connection['host'],
            port=connection['port']
        )

        status = 'success' if connection_status else 'failure'
        result = {'ruleId': connection['id'], 'timestamp': time.time(), 'result': status}
        self.latest_results.append(result)

        result_text = 'succeeded' if connection_status else 'failed'
        subject = f'{connection["name"]}: Connection {result_text.upper()}'
        body = (
            f'{connection["name"]} ({connection["host"]}: {connection["port"]})\n'
            f'Config: {connection}'
        )
        action = success_action if connection_status else failure_action

        self.logger.info(
            f"Processing {connection['name']}: connection {result}, action: {action}"
        )

        if action == 'pass':
            self.logger.info(f"Passing for {connection['name']}")
        elif action == 'alert':
            self.alerter.alert(
                source='icepick',
                subject=subject,
                body=body
            )
        else:
            message = f"Unknown action for {connection['name']}: {action}, connection {result}"
            self.logger.error(message)
            raise ValueError(message)


if __name__ == '__main__':
    icepick = Icepick()
    icepick.run()
