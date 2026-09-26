"""
app.data.deduplication
======================
Deduplication Engine & Fingerprinting for UC15 (Sprint 17).
"""

from app.data.deduplication.deduplication_engine import (
    DeduplicationEngine,
    DuplicateCheckResult,
    DuplicateStatus,
)

__all__ = ["DeduplicationEngine", "DuplicateCheckResult", "DuplicateStatus"]
