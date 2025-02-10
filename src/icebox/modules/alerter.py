import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional
import threading

from modules.logger import Logger


class Alerter:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Alerter, cls).__new__(cls)
                cls._instance.logger = Logger.get_logger('alerter')
                cls._instance._alert_methods = {}
                cls._instance.logger.debug("Created new Alerter instance")
            return cls._instance

    def configure_smtp(self, smtp_config: dict) -> None:
        """Configure SMTP alerting."""
        with self._lock:
            self.logger.debug("Configuring SMTP alerting")
            self._alert_methods['smtp'] = {
                'config': smtp_config,
                'enabled': smtp_config.get('sending_enabled', False)
            }

    def remove_method(self, method: str) -> None:
        """Remove an alert method."""
        with self._lock:
            if method in self._alert_methods:
                self.logger.debug(f"Removing alert method: {method}")
                del self._alert_methods[method]

    def enable_method(self, method: str) -> None:
        """Enable an alert method."""
        with self._lock:
            if method in self._alert_methods:
                self.logger.debug(f"Enabling alert method: {method}")
                self._alert_methods[method]['enabled'] = True

    def disable_method(self, method: str) -> None:
        """Disable an alert method."""
        with self._lock:
            if method in self._alert_methods:
                self.logger.debug(f"Disabling alert method: {method}")
                self._alert_methods[method]['enabled'] = False

    def alert(self, subject: str, body: str) -> bool:
        """Send an alert through all enabled methods.

        Returns:
            bool: True if at least one method succeeded
        """
        self.logger.debug(f"Processing alert: {subject}")
        success = False

        with self._lock:
            if not self._alert_methods:
                self.logger.warning("No alert methods configured")
                return False

            for method, settings in self._alert_methods.items():
                if not settings['enabled']:
                    self.logger.debug(f"Skipping disabled alert method: {method}")
                    continue

                try:
                    if method == 'smtp':
                        if self._send_smtp_alert(subject, body, settings['config']):
                            success = True
                    # Add other alert methods here
                except Exception as e:
                    self.logger.error(f"Error sending {method} alert: {e}")

        return success

    def _send_smtp_alert(self, subject: str, body: str, smtp_config: dict) -> bool:
        """Send an alert via SMTP."""
        msg = MIMEMultipart()
        msg['From'] = smtp_config['from']
        msg['To'] = smtp_config['to']
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        try:
            with socket.setdefaulttimeout(10):
                server = smtplib.SMTP(
                    host=smtp_config['smtp_server'],
                    port=smtp_config['smtp_port'],
                    timeout=10
                )
                if smtp_config['tls']:
                    server.starttls()
                server.login(
                    smtp_config['smtp_user'],
                    smtp_config['smtp_password']
                )
                server.sendmail(
                    smtp_config['from'],
                    smtp_config['to'],
                    msg.as_string()
                )
                server.quit()
                self.logger.info("Alert email sent successfully")
                return True
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
            return False
