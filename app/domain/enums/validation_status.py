"""
UC15 GST Compliance Agent — Validation Status Enum
"""
from __future__ import annotations
from enum import Enum


class ValidationStatus(str, Enum):
    """
    Status of an individual rule validation.
    """
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ERROR = "ERROR"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    @classmethod
    def from_str(cls, value: str) -> "ValidationStatus":
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown ValidationStatus: {value}")
