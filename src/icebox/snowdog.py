import re
import time
import threading

from modules.alerter import Alerter
from modules.logger import Logger
from modules.sqlite import SQLiteDB
from modules.log_watcher import LogWatcher
from modules.config_store import ConfigStore


class Snowdog:

    def __init__(self) -> None:
        try:
            self.config_store = ConfigStore()

            self.shutdown_flag = threading.Event()
            self.logger = Logger.get_logger('snowdog')

            self.config_store.watch('iptables.log_file', self._handle_log_file_change)
            self.config_store.watch('smtp', self._handle_smtp_config_change)
            self.config_store.watch('snowdog', self._handle_snowdog_config_change)

            self.iptables_log = self.config_store.get('iptables.log_file')
            self.alerter = Alerter()
            if self.config_store.get('smtp'):
                self.alerter.configure_smtp(self.config_store.get('smtp'))

            self.db = SQLiteDB(self.config_store.get('snowdog.db_file'))
            self.log_watcher = LogWatcher(
                file_path=self.iptables_log,
                tag='SNOWDOG',
                message_handler=self.handle_message
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Snowdog: {e}")
            raise

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

    def _handle_snowdog_config_change(self, new_config: dict) -> None:
        """Handle changes to Snowdog configuration."""
        if hasattr(self, 'db'):
            self.logger.info(f"Updating Snowdog database file path to {new_config['db_file']}")
            self.db = SQLiteDB(new_config['db_file'])

    def stop(self) -> None:
        self.logger.info('Stopping snowdog')
        self.shutdown_flag.set()
        try:
            if hasattr(self, 'log_watcher'):
                self.log_watcher.stop()
            if hasattr(self, 'db'):
                self.db.close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            raise

    def run(self) -> None:
        try:
            if self.config_store.get('snowdog.learning'):
                self.logger.info("Starting snowdog in learning mode")
            else:
                self.logger.info("Starting snowdog")
                if not self.config_store.get('snowdog.alerting'):
                    self.logger.warning("Alerting is disabled")
            self.log_watcher.start()


            while not self.shutdown_flag.is_set():
                time.sleep(10)
        except Exception as e:
            self.logger.error(f"Error running Snowdog: {e}")
            raise

    def handle_message(self, message: str) -> None:
        try:
            self.logger.debug(f"Detected broadcast traffic: {message}")

            if self.config_store.get('snowdog.learning'):
                self.learn_mac_addresses(message)
            elif self.has_unknown_macs(message):
                if self.config_store.get('snowdog.alerting'):
                    self.alerter.alert(
                        f'Snowdog Alert: {self.config_store.get("icebox.name")}',
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

    def learn_mac_addresses(self, message: str) -> None:
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

    def has_unknown_macs(self, message: str) -> None:
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

    def get_mac_addresses(self, message: str) -> None:
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
