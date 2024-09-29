import re
import time

from modules.smtp import SMTP
from modules.logger import Logger
from modules.sqlite import SQLiteDB
from modules.log_watcher import LogWatcher
from modules.utils import validate_config, get_config

class Snowdog:

    def __init__(self, config_path):
        self.config_path = config_path
        try:
            self.config = get_config(config_path)
            self.iptables_log = self.config['iptables']['log_file']
            self.logger = Logger.get_logger('snowdog')
            self.smtp = SMTP(self.config['smtp'])
            self.db = SQLiteDB(self.config['snowdog']['db_file'])

            validate_config(self.config, ['iptables', 'smtp', 'snowdog'])

            self.log_watcher = LogWatcher(
                file_path=self.iptables_log,
                tag='SNOWDOG',
                message_handler=self.handle_message
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Snowdog: {e}")
            raise

    def __del__(self):
        try:
            if hasattr(self, 'log_watcher'):
                self.log_watcher.stop()
            if hasattr(self, 'db'):
                self.db.close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            raise

    def run(self):
        try:
            if self.config['snowdog']['learning']:
                self.logger.info("Starting snowdog in learning mode")
            else:
                self.logger.info("Starting snowdog")
                if not self.config['snowdog']['alerting']:
                    self.logger.warning("Alerting is disabled")
            self.log_watcher.start()

            while True:
                time.sleep(10)
        except Exception as e:
            self.logger.error(f"Error running Snowdog: {e}")
            raise

    def handle_message(self, message):
        try:
            self.logger.debug(f"Detected broadcast traffic: {message}")

            if self.config['snowdog']['learning']:
                self.learn_mac_addresses(message)
            elif self.has_unknown_macs(message):
                if self.config['snowdog']['alerting']:
                    self.smtp.send_email(
                        f'Snowdog Alarm: {self.config["icebox"]["name"]}',
                        f'Unknown MAC address detected.\n{message}'
                    )
                else:
                    self.logger.warn(
                        f"Not alerting as alerting is disabled"
                        f"{message}"
                    )
                self.learn_mac_addresses(message)
        except Exception as e:
            self.logger.error(
                f"Error handling message: {e}, "
                f"message: {message}"
            )

    def learn_mac_addresses(self, message):
        try:
            source_mac, destination_mac = self.get_mac_addresses(message)
            if source_mac and destination_mac:
                for mac_address in [source_mac, destination_mac]:
                    if self.db.insert_mac_address(mac_address):
                        self.logger.info(
                            f"Learned MAC address: {mac_address}"
                        )
        except Exception as e:
            self.logger.error(
                f"Error learning MAC addresses: {e}, "
                f"message: {message}"
            )

    def has_unknown_macs(self, message):
        try:
            source_mac, destination_mac = self.get_mac_addresses(message)
            if not source_mac or not destination_mac:
                self.logger.error(
                    f"Unsupported message format: {message}"
                )
                return False
            return not (
                self.db.is_known_mac(source_mac) and
                self.db.is_known_mac(destination_mac)
            )
        except Exception as e:
            self.logger.error(
                f"Error checking for unknown MAC addresses: {e}, "
                f"message: {message}"
            )
            return False

    def get_mac_addresses(self, message):
            mac = re.search(r'MAC=([a-f0-9:]{77})', message)
            if mac:
                try:
                    mac = mac[1]
                    components = mac.split(':')
                    destination_mac = ':'.join(components[0:6])
                    source_mac = ':'.join(components[6:12])
                    return source_mac, destination_mac
                except Exception as e:
                    self.logger.error(
                        f"Error extracting MAC addresses from message: {e}, "
                        f"message: {message}"
                    )
            return None, None
