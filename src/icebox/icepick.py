import socket
import time
import random
import signal
import threading
import sys

from modules.smtp import SMTP
from modules.logger import Logger
from modules.config_store import ConfigStore
from modules.utils import get_config


class Icepick:

    def __init__(self) -> None:
        self.config_store = ConfigStore()
        self.config_store.add_observer(self._handle_config_update)
        self.config = self.config_store.get_config()

        self.shutdown_flag = threading.Event()
        self.logger = Logger.get_logger('icepick')
        self.smtp = SMTP(self.config['smtp'])
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def _handle_config_update(self, new_config: dict) -> None:
        """Handle updates to the configuration."""
        self.config = new_config
        self.smtp = SMTP(new_config['smtp'])

    def stop(self) -> None:
        self.logger.info('Stopping icepick')
        self.shutdown_flag.set()

    def run(self) -> None:
        self.logger.info('Starting icepick')
        while not self.shutdown_flag.is_set():
            for connection in self.config['icepick']:
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
        subject = f'Icepick Alarm: {connection["name"]}: Connection {result.upper()}'
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
        elif action == 'email':
            self.smtp.send_email(subject, body)
        else:
            message = f"Unknown action for {connection['name']}: {action}, connection {result}"
            self.logger.error(message)
            raise ValueError(message)


if __name__ == '__main__':
    icepick = Icepick('config.json')
    icepick.run()
