"""
UC15 GST Compliance Agent — Trend Analysis Models (Sprint 5)
Provides deterministic period-over-period comparison metrics and trend classifications.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class TrendDirection(str, Enum):
    """Deterministic classification of period-over-period compliance rate trajectory."""
    IMPROVING = "IMPROVING"              # Compliance rate increased >= threshold pp
    STABLE = "STABLE"                    # Compliance rate remained within tolerance
    DETERIORATING = "DETERIORATING"      # Compliance rate dropped <= threshold pp
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"  # Only 1 period available or 0 volume


@dataclass
class PeriodTrend:
    """
    Detailed period-over-period delta and trajectory evaluation.
    """
    current_period: str
    previous_period: Optional[str] = None

    # Compliance Rates
    current_compliance_rate: float = 0.0
    previous_compliance_rate: Optional[float] = None

    # Deltas
    absolute_change_pp: Optional[float] = None     # Percentage points difference (e.g. +8.0 pp or -6.0 pp)
    percentage_change: Optional[float] = None      # Relative % change of the compliance rate

    # Trajectory Classification
    direction: TrendDirection = TrendDirection.INSUFFICIENT_DATA

    # Volume and Financial Context
    current_invoice_count: int = 0
    previous_invoice_count: Optional[int] = None
    volume_change: Optional[int] = None

    # Explainable description
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_period": self.current_period,
            "previous_period": self.previous_period,
            "current_compliance_rate": self.current_compliance_rate,
            "previous_compliance_rate": self.previous_compliance_rate,
            "absolute_change_pp": self.absolute_change_pp,
            "percentage_change": self.percentage_change,
            "direction": self.direction.value,
            "current_invoice_count": self.current_invoice_count,
            "previous_invoice_count": self.previous_invoice_count,
            "volume_change": self.volume_change,
            "description": self.description,
        }
