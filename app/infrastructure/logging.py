"""
UC15 GST Compliance Agent — Infrastructure Logging & Structured Observability (Sprint 19)
Provides structured application logging with sensitive data masking and correlation ID injection.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any, Dict, Optional
from app.infrastructure.correlation import get_correlation_id

_INITIALIZED = False
DEFAULT_LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s] [corr=%(correlation_id)s]: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Sensitive data masking pattern (API keys, bearer tokens, passwords)
SENSITIVE_PATTERNS = [
    (re.compile(r"(api[-_]?key|secret|token|password)\s*[:=]\s*['\"]?([^'\"\s&]+)['\"]?", re.IGNORECASE), r"\1=***MASKED***"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), r"Bearer ***MASKED***"),
]


class MaskingFormatter(logging.Formatter):
    """Custom logging formatter that injects correlation ID and masks sensitive fields."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = get_correlation_id()
        msg = super().format(record)
        for pattern, replacement in SENSITIVE_PATTERNS:
            msg = pattern.sub(replacement, msg)
        return msg


def setup_logging(level: Optional[str] = None) -> None:
    """Initialize application logging configuration."""
    global _INITIALIZED
    if _INITIALIZED:
        return

    log_level_str = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = MaskingFormatter(fmt=DEFAULT_LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Avoid duplicate handlers if root logger already has some
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured with application defaults."""
    if not _INITIALIZED:
        setup_logging()
    return logging.getLogger(name)
