import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, Any
import threading
from queue import Queue
import time
from dataclasses import dataclass
from uuid import uuid4

from modules.logger import Logger
from modules.config_store import ConfigStore


@dataclass
class Alert:
    """An alert from an Icebox module."""

    source: str
    subject: str
    body: str
    timestamp: float
    idempotency_token: str


class Alerter:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Alerter, cls).__new__(cls)
                cls._instance.logger = Logger.get_logger("alerter")
                cls._instance._alert_methods = {}
                cls._instance.logger.debug("Created new Alerter instance")
                cls._instance.config_store = ConfigStore()
            return cls._instance

    def alert(self, source: str, subject: str, body: str) -> bool:
        """Send an alert through all enabled methods.

        Args:
            source: The source/module generating the alert
            subject: Alert subject line
            body: Alert message body

        Returns:
            bool: True if at least one method succeeded
        """
        self.logger.debug(f"Processing alert: {subject}")
        success = False

        alert_filters = self.config_store.get("alert_filters")
        if alert_filters:
            filtered = False
            for filter in alert_filters:
                if filter["source"] == source:
                    if filter["subject"] and filter["body"]:
                        if filter["subject"] in subject and filter["body"] in body:
                            filtered = True
                    elif filter["subject"] and filter["subject"] in subject:
                        filtered = True
                    elif filter["body"] and filter["body"] in body:
                        filtered = True
            if filtered:
                self.logger.debug(f"Alert filtered: {subject}")
                return False

        with self._lock:
            if not self._alert_methods:
                self.logger.warning("No alert methods configured")
                return False

            for method, settings in self._alert_methods.items():
                if not settings["enabled"]:
                    self.logger.debug(f"Skipping disabled alert method: {method}")
                    continue

                alert = {
                    "source": source,
                    "subject": subject,
                    "body": body,
                    "config": settings["config"],
                    "idempotency_token": str(uuid4()),
                }

                try:
                    if method == "smtp":
                        if self._send_smtp_alert(**alert):
                            success = True
                    if method == "icewatch":
                        if self._send_icewatch_alert(**alert):
                            success = True
                except Exception as e:
                    self.logger.error(f"Error sending {method} alert: {e}")

        return success

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
                self._alert_methods[method]["enabled"] = True

    def disable_method(self, method: str) -> None:
        """Disable an alert method."""
        with self._lock:
            if method in self._alert_methods:
                self.logger.debug(f"Disabling alert method: {method}")
                self._alert_methods[method]["enabled"] = False

    def configure_icewatch(self, queue: Queue) -> None:
        """Configure Icewatch alerting with external queue."""
        with self._lock:
            self.logger.debug("Configuring Icewatch alerting")
            self._alert_methods["icewatch"] = {
                "config": {"queue": queue},
                "enabled": True,
            }

    def _send_icewatch_alert(
        self, source: str, subject: str, body: str, config: dict, idempotency_token: str
    ) -> bool:
        """Queue an alert for Icewatch."""
        from icewatch import IcewatchClient

        try:
            success = IcewatchClient.queue_alert(
                source, subject, body, idempotency_token
            )
            if success:
                self.logger.debug(f"Queued alert for Icewatch: {subject}")
            return success
        except Exception as e:
            self.logger.error(f"Failed to queue alert: {e}")
            return False

    def configure_smtp(self, smtp_config: dict) -> None:
        """Configure SMTP alerting."""
        with self._lock:
            self.logger.debug("Configuring SMTP alerting")
            self._alert_methods["smtp"] = {
                "config": smtp_config,
                "enabled": smtp_config.get("sending_enabled", False),
            }

    def _send_smtp_alert(
        self, source: str, subject: str, body: str, config: dict, idempotency_token: str
    ) -> bool:
        """Send an alert via SMTP."""
        smtp_config = config
        msg = MIMEMultipart()
        msg["From"] = smtp_config["from"]
        msg["To"] = smtp_config["to"]
        msg["Subject"] = f"[{source}] {subject}"
        msg.attach(MIMEText(body, "plain"))

        try:
            with socket.setdefaulttimeout(10):
                server = smtplib.SMTP(
                    host=smtp_config["smtp_server"],
                    port=smtp_config["smtp_port"],
                    timeout=10,
                )
                if smtp_config["tls"]:
                    server.starttls()
                server.login(smtp_config["smtp_user"], smtp_config["smtp_password"])
                server.sendmail(smtp_config["from"], smtp_config["to"], msg.as_string())
                server.quit()
                self.logger.info("Alert email sent successfully")
                return True
        except Exception as e:
            self.logger.error(f"Failed to send alert email: {e}")
            return False
