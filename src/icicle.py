from datetime import datetime, timedelta
import threading
import time
import re

from modules.smtp import SMTP
from modules.logger import Logger
from modules.utils import get_config
from modules.log_watcher import LogWatcher

class Icicle:

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self.shutdown_flag = threading.Event()
        self.config = get_config(config_path)
        self.iptables_log = self.config['iptables']['log_file']
        self.logger = Logger.get_logger('icicle')
        self.smtp = SMTP(self.config['smtp'])
        self.connection_tracker = {}
        self.new_message_event = threading.Event()

        self.log_watcher = LogWatcher(
            file_path=self.iptables_log,
            tag='ICICLE',
            message_handler=self.handle_message
        )

    def stop(self) -> None:
        self.logger.info('Stopping icicle')
        self.shutdown_flag.set()

    def run(self) -> None:
        self.logger.info('Starting icicle')
        self.log_watcher.start()

        while not self.shutdown_flag.is_set():
            now = datetime.now()
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
            dest_port = re.search(r'DPT=([0-9]*)', message)[1]
            if src_address in self.connection_tracker:
                self.connection_tracker[src_address]['connected_ports'].append(
                    dest_port
                )
            else:
                self.connection_tracker[src_address] = {
                    'connected_ports': [dest_port],
                    'first_connection': datetime.now()
                }
            self.new_message_event.set()
        except Exception as e:
            self.logger.error(
                f'Error parsing message: {e}, {message}'
            )

    def send_alert(self, src_address: str, connection_info: dict) -> None:
        icebox_name = self.config['icebox']['name']
        ports = connection_info['connected_ports']
        start_time = str(connection_info['first_connection'])

        subject = f'Icicle Alarm: {self.config["icebox"]["name"]}'
        if len(ports) > 5:
            subject = f'Icicle Alarm: PORT SCAN DETECTED: {icebox_name}'

        self.smtp.send_email(
            subject=subject,
            body=(
                f'Incoming connection detected from {src_address}.\n\n'
                f'{len(ports)} connections were observed to '
                f'{len(set(ports))} unique ports, starting at {start_time}.'
            )
        )
