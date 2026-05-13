"""Provide logging utilities for the analytics automation tool.

This module configures both console and file logging. Daily log files are
written into the project-level logs directory with names formatted as
YYYY-MM-DD.log.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


DEFAULT_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(module)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _ensure_log_directory(log_dir: Path) -> Path:
    """Ensure the log directory exists and return its Path."""
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _daily_log_file_path(log_dir: Path | None = None) -> Path:
    """Return the full path to the daily log file."""
    log_dir = Path(log_dir) if log_dir is not None else DEFAULT_LOG_DIR
    _ensure_log_directory(log_dir)
    file_name = f"{datetime.now():%Y-%m-%d}.log"
    return log_dir / file_name


def configure_logger(name: str, log_dir: Path | str | None = None, level: int = logging.INFO) -> logging.Logger:
    """Configure and return a logger with console and daily file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(_daily_log_file_path(log_dir), encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


def get_logger(name: str, log_dir: Path | str | None = None) -> logging.Logger:
    """Return a configured logger for the given module name."""
    return configure_logger(name, log_dir)


def log_message(level: int, message: str, logger_name: str = __name__) -> None:
    """Log a message at the given severity level using the named logger."""
    logger = get_logger(logger_name)
    logger.log(level, message)
