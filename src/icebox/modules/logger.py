import logging
import re
from threading import Lock
from typing import Optional

class Logger:
    _logger: Optional[logging.Logger] = None
    _lock: Lock = Lock()

    @staticmethod
    def configure(log_file: str, log_level: int = logging.DEBUG) -> None:
        with Logger._lock:
            if Logger._logger is None:
                Logger._logger = logging.getLogger()
                Logger._logger.setLevel(log_level)

                fh = logging.FileHandler(log_file)
                fh.setLevel(log_level)

                ch = logging.StreamHandler()
                ch.setLevel(log_level)

                formatter = logging.Formatter(
                    '[%(asctime)s] [%(name)s] %(levelname)s %(message)s'
                )
                fh.setFormatter(formatter)
                ch.setFormatter(formatter)

                Logger._logger.addHandler(fh)
                Logger._logger.addHandler(ch)

                Logger._logger.addFilter(SanitizeLogFilter())

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        if Logger._logger is None:
            raise RuntimeError("Logger not configured. Call Logger.configure() first.")
        return Logger._logger.getChild(name)


class SanitizeLogFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = re.sub(r'[\n\r\t]', '_', str(record.msg))
        return True
