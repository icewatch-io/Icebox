from datetime import datetime, timedelta, timezone
import threading
import re

from modules.alerter import Alerter
from modules.logger import Logger
from modules.log_watcher import LogWatcher
from modules.config_store import ConfigStore


class Icicle:

    def __init__(self) -> None:
        self.config_store = ConfigStore()
        self.shutdown_flag = threading.Event()
        self.logger = Logger.get_logger('icicle')

        self.config_store.watch('iptables.log_file', self._handle_log_file_change)
        self.config_store.watch('smtp', self._handle_smtp_config_change)

        self.iptables_log = self.config_store.get('iptables.log_file')
        self.alerter = Alerter()
        if self.config_store.get('smtp'):
            self.alerter.configure_smtp(self.config_store.get('smtp'))

        self.connection_tracker = {}
        self.new_message_event = threading.Event()

        self.log_watcher = LogWatcher(
            file_path=self.iptables_log,
            tag='ICICLE',
            message_handler=self.handle_message
        )

    def _handle_log_file_change(self, new_path: str) -> None:
        """Handle changes to log file path."""
        self.iptables_log = new_path
        if hasattr(self, 'log_watcher'):
            self.logger.info(f"Updating log file path to {new_path}")
            self.log_watcher.file_path = new_path

    def _handle_smtp_config_change(self, new_config: dict) -> None:
        """Handle changes to SMTP configuration."""
        if hasattr(self, 'alerter'):
            self.logger.info(f"Updating SMTP configuration")
            self.alerter.configure_smtp(new_config)

    def stop(self) -> None:
        self.logger.info('Stopping icicle')
        self.shutdown_flag.set()
        if hasattr(self, 'log_watcher'):
            self.log_watcher.stop()

    def run(self) -> None:
        self.logger.info('Starting icicle')
        self.log_watcher.start()

        while not self.shutdown_flag.is_set():
            now = datetime.now(timezone.utc)
            for src_address in list(self.connection_tracker.keys()):
                connection_info = self.connection_tracker[src_address]
                time_since = now - connection_info['first_connection']
                if time_since > timedelta(seconds=1):
                    del self.connection_tracker[src_address]
                    self.send_alert(src_address, connection_info)

            self.new_message_event.wait(timeout=1)
            self.new_message_event.clear()

    def handle_message(self, message: str) -> None:
        try:
            proto = re.search(r'PROTO=([0-9A-Za-z]*)', message)[1]
            if proto == 'ICMP':
                message += ' DPT=0'

                type = int(re.search(r'PROTO=ICMP TYPE=([0-9]*)', message)[1])
                filtered_types = [
                    0,  # Echo Reply
                    3,  # Destination Unreachable - due to Icepick checks
                    4,  # Source Quench
                    11, # Time Exceeded
                ]
                if type in filtered_types:
                    return

            self.logger.info(f'Detected incoming connection: {message}')
            src_address = re.search(r'SRC=([0-9A-Fa-f:\.]*)', message)[1]
            dest_port = int(re.search(r'DPT=([0-9]*)', message)[1])
            if src_address in self.connection_tracker:
                self.connection_tracker[src_address]['connected_ports'].append(
                    dest_port
                )
            else:
                self.connection_tracker[src_address] = {
                    'connected_ports': [dest_port],
                    'first_connection': datetime.now(timezone.utc)
                }
            self.new_message_event.set()
        except Exception as e:
            self.logger.error(
                f'Error parsing message: {e}, {message}'
            )

    def send_alert(self, src_address: str, connection_info: dict) -> None:
        icebox_name = self.config_store.get('icebox.name')

        start_time = str(connection_info['first_connection'])
        ports = connection_info['connected_ports']
        num_ports = len(ports)
        unique_ports = set(ports)
        num_unique_ports = len(unique_ports)

        subject = f'CONNECTION DETECTED'
        if num_unique_ports > 3:
            subject = f'PORT SCAN DETECTED'
        elif num_unique_ports == 1 and 0 in unique_ports:
            subject = f'PING DETECTED'

        self.alerter.alert(
            source='icicle',
            subject=subject,
            body=(
                f'Incoming connection detected from {src_address}.\n\n'
                f'{num_ports} connections were observed to '
                f'{num_unique_ports} unique ports, starting at {start_time}.'
            )
        )
