"""
UC15 GST Compliance Agent — Confidence Level Enum
"""
from __future__ import annotations
from enum import Enum


class ConfidenceLevel(str, Enum):
    """
    Confidence assessment of the risk evaluation based on evidence completeness.
    
      - HIGH: Complete invoice data, verified reference master, external 2B/portal match.
      - MEDIUM: Core data valid, but some optional master data or secondary proofs missing.
      - LOW: Critical reference data unavailable, unverified external proof, or data quality defects.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

    @classmethod
    def from_str(cls, value: str) -> "ConfidenceLevel":
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown ConfidenceLevel: {value}")
