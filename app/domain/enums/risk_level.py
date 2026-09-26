"""
UC15 GST Compliance Agent — Risk Level Enum
"""
from __future__ import annotations
from enum import Enum


class RiskLevel(str, Enum):
    """
    Standard risk level classification based on normalized 0-100 risk score.
    Separated from statutory compliance status (COMPLIANT / NEEDS_REVIEW / NON_COMPLIANT).
    
      - LOW: Minimal compliance or business risk (0–19).
      - MODERATE: Minor issues or warning observations (20–39).
      - MEDIUM: Notable compliance discrepancy requiring standard handling (40–59).
      - HIGH: Serious non-compliance, substantial tax or penalty risk (60–79).
      - CRITICAL: Severe statutory violation, hard stop or filing blocker (80–100).
    """
    LOW = "LOW"
    MODERATE = "MODERATE"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_str(cls, value: str) -> "RiskLevel":
        normalized = value.strip().upper()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"Unknown RiskLevel: {value}")
