"""
UC15 GST Compliance Agent — Risk Priority Enum
"""
from __future__ import annotations
from enum import Enum


class RiskPriority(str, Enum):
    """
    Investigation priority classification.
    Distinguishes operational urgency from intrinsic risk severity.
    
      - P1: Immediate intervention required (same day / blocker).
      - P2: High priority investigation (within 24 hours / filing cycle).
      - P3: Normal queue review (standard operational turnaround).
      - P4: Low priority / informational (routine filing audit).
    """
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"

    @classmethod
    def from_str(cls, value: str) -> "RiskPriority":
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown RiskPriority: {value}")
