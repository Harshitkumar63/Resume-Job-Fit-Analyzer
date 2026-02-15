"""
Structured logging configuration.

Uses stdlib logging with a JSON-like formatter for production
and a human-readable formatter for local dev.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", json_format: bool = False) -> None:
    """
    Configure root logger.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, emit structured JSON lines (for log aggregators).
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Avoid duplicate handlers on repeated calls
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(root.level)

    if json_format:
        fmt = (
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
    root.addHandler(handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "httpcore", "httpx", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a named logger. Prefer module __name__ as *name*."""
    return logging.getLogger(name or __name__)
