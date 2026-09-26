"""
UC15 GST Compliance Agent — Compliance Status Enum
"""
from __future__ import annotations
from enum import Enum


class ComplianceStatus(str, Enum):
    """
    Overall compliance classification for an invoice.
    
    Compatible with existing statuses:
      - COMPLIANT: Passed all checks, ready for GSTR filing.
      - NEEDS_REVIEW: Exactly 1 non-fatal failure, flagged for same-cycle review.
      - NON_COMPLIANT: 2+ failures or Gate 1 hard override, blocked from filing.
      - BLOCKED: Explicitly blocked for severe/fraud/statutory hold (future extension).
    """
    COMPLIANT = "COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REVIEW = "NEEDS_REVIEW"  # Alias for target architecture compatibility
    NON_COMPLIANT = "NON_COMPLIANT"
    BLOCKED = "BLOCKED"

    @classmethod
    def from_str(cls, value: str) -> "ComplianceStatus":
        normalized = value.strip().upper()
        if normalized == "REVIEW":
            return cls.NEEDS_REVIEW
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown ComplianceStatus: {value}")
