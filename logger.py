"""
utils/logger.py
---------------
Centralized logging setup with rotating file handler.
Logs are saved to logs/agent.log with automatic rotation at 5MB.
Console output uses a clean format.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name):
    """Returns a configured logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # File handler - rotating at 5MB, keeps 3 backups
    fh = RotatingFileHandler(
        os.path.join(LOG_DIR, "agent.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False
    return logger
