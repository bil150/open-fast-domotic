import logging
import os
from logging.handlers import RotatingFileHandler

FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_configured = False


def setup_logging(log_file: str, max_bytes: int = 1_048_576, backup_count: int = 2) -> None:
    """Console + rotating file. Safe to call several times (e.g. in tests)."""
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    formatter = logging.Formatter(FORMAT)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count),
        logging.StreamHandler(),
    ]
    for handler in handlers:
        handler.setFormatter(formatter)
        root.addHandler(handler)
