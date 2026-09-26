"""
UC15 GST Compliance Agent — Severity Enum
"""
from __future__ import annotations
from enum import Enum


class Severity(str, Enum):
    """
    Severity level of a rule violation or check.
    """
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_str(cls, value: str) -> "Severity":
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown Severity: {value}")
