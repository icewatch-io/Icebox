import socket
import time
import random
import signal
import threading
import sys

from modules.alerter import Alerter
from modules.logger import Logger
from modules.config_store import ConfigStore


class Icepick:

    def __init__(self) -> None:
        self.config_store = ConfigStore()
        self.shutdown_flag = threading.Event()
        self.logger = Logger.get_logger('icepick')

        self.config_store.watch('smtp', self._handle_smtp_config_change)
        self.config_store.watch('icepick', self._handle_icepick_config_change)

        self.alerter = Alerter()
        if self.config_store.get('smtp'):
            self.alerter.configure_smtp(self.config_store.get('smtp'))

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

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

    def run(self) -> None:
        self.logger.info('Starting icepick')
        while not self.shutdown_flag.is_set():
            for connection in self.config_store.get('icepick'):
                self.process_connection(connection)
            time.sleep(random.randint(60, 90))

    def check_tcp(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=5):
                return True
        except Exception as e:
            return False

    def process_connection(self, connection: dict) -> None:
        failure_action = connection['failure_action']
        success_action = connection['success_action']

        connection_status = self.check_tcp(
            host=connection['host'],
            port=connection['port']
        )

        result = 'succeeded' if connection_status else 'failed'
        subject = f'{connection["name"]}: Connection {result.upper()}'
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
