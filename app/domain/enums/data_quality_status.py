"""
UC15 GST Compliance Agent — Data Quality Usability Status Enum (Phase 2)
"""
from enum import Enum


class DataQualityStatus(str, Enum):
    """Data Quality usability classifications."""
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
