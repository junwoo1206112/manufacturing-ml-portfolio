"""Project-wide logging configuration."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, Union


DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: Union[int, str] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    fmt: str = DEFAULT_FORMAT,
) -> logging.Logger:
    """Configure root logger with a stream handler and optional file handler.

    Args:
        level: Logging level (e.g., logging.INFO or "INFO").
        log_file: Optional path to a log file.
        fmt: Log record format string.

    Returns:
        The configured root logger.
    """
    root = logging.getLogger()
    root.setLevel(level)

    if root.handlers:
        root.handlers.clear()

    formatter = logging.Formatter(fmt, datefmt=DATE_FORMAT)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    return root


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)
