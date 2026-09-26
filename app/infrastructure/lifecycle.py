"""
app.infrastructure.lifecycle
===========================
Graceful Shutdown and Lifecycle Manager for UC15 (Sprint 19).
Manages signal handling, in-flight operation flushing, and database connection cleanup.
"""

from __future__ import annotations

import signal
import sys
from typing import Callable, List
from app.db.connection import reset_db_connection
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

_SHUTDOWN_HOOKS: List[Callable[[], None]] = []
_SHUTDOWN_INITIATED = False


def register_shutdown_hook(hook: Callable[[], None]) -> None:
    """Register a callback hook to run on graceful application shutdown."""
    _SHUTDOWN_HOOKS.append(hook)


def initiate_graceful_shutdown(sig: int = 0, frame: Any = None) -> None:
    """
    Execute graceful shutdown pipeline: run hooks and close database resources.
    """
    global _SHUTDOWN_INITIATED
    if _SHUTDOWN_INITIATED:
        return
    _SHUTDOWN_INITIATED = True

    logger.info(f"Initiating UC15 graceful shutdown (Signal: {sig})...")

    # 1. Execute registered hooks
    for hook in _SHUTDOWN_HOOKS:
        try:
            hook()
        except Exception as e:
            logger.error(f"Error executing shutdown hook: {e}")

    # 2. Reset database connection pool
    try:
        reset_db_connection()
        logger.info("Database connection pool cleanly closed.")
    except Exception as e:
        logger.error(f"Error closing database pool: {e}")

    logger.info("UC15 Graceful Shutdown Complete.")


def setup_signal_handlers() -> None:
    """Register SIGINT and SIGTERM OS signal handlers for graceful shutdown."""
    try:
        signal.signal(signal.SIGINT, initiate_graceful_shutdown)
        signal.signal(signal.SIGTERM, initiate_graceful_shutdown)
        logger.info("Registered SIGINT/SIGTERM OS signal handlers.")
    except Exception as e:
        logger.warning(f"Could not register signal handlers: {e}")
