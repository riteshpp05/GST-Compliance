"""
app.infrastructure.correlation
===============================
Thread-safe ContextVar Correlation ID Manager for end-to-end trace correlation (Sprint 19).
Allows tracing an incoming HTTP request across threads, agent loops, tools, and DB operations.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from typing import Optional

_CORRELATION_ID: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """Retrieve current correlation ID or generate new UUID if unset."""
    cid = _CORRELATION_ID.get()
    if not cid:
        cid = f"corr-{uuid.uuid4().hex[:12]}"
        _CORRELATION_ID.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set explicit correlation ID for current context."""
    _CORRELATION_ID.set(correlation_id)


def reset_correlation_id() -> None:
    """Clear correlation ID context."""
    _CORRELATION_ID.set(None)
