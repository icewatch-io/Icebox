import logging
import re
from threading import Lock
from typing import Optional
import sys


class ColorFormatter(logging.Formatter):
    """Custom formatter with colored output for different log levels."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        if record.levelname in self.COLORS:
            message = f"{self.COLORS[record.levelname]}{message}{self.COLORS['RESET']}"

        return message


class Logger:
    _logger: Optional[logging.Logger] = None
    _lock: Lock = Lock()
    _configured = False

    @classmethod
    def configure(cls, log_file: str, log_level: str = "INFO") -> None:
        """Configure the logging system."""
        if cls._configured:
            return

        numeric_level = getattr(logging, log_level.upper(), logging.INFO)

        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s] %(levelname)s %(message)s"
        )
        console_formatter = ColorFormatter(
            "[%(asctime)s] [%(name)s] %(levelname)s %(message)s"
        )

        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with the given name."""
        if not cls._configured:
            cls.configure("/var/log/icebox/icebox.log")
        return logging.getLogger(name)


class SanitizeLogFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = re.sub(r"[\n\r\t]", "_", str(record.msg))
        return True
