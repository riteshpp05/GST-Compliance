"""
UC15 GST Compliance Agent — Time Period Aggregation Models (Sprint 5)
Provides deterministic time period aggregation for Daily, Weekly, Monthly, and Quarterly views.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class PeriodType(str, Enum):
    """Supported deterministic time period intervals."""
    DAILY = "DAILY"          # YYYY-MM-DD
    WEEKLY = "WEEKLY"        # YYYY-Www (ISO calendar week)
    MONTHLY = "MONTHLY"      # YYYY-MM (Primary statutory filing interval)
    QUARTERLY = "QUARTERLY"  # YYYY-Q# (Statutory composition/QRMP interval)


@dataclass
class PeriodMetrics:
    """
    Deterministic compliance and financial metrics aggregated over a specific time window.
    """
    period_key: str                     # e.g. "2026-06", "2026-Q2", "2026-W24"
    period_type: PeriodType
    start_date: date
    end_date: date

    # Volume Counts
    total_invoices: int = 0
    compliant_count: int = 0
    needs_review_count: int = 0
    non_compliant_count: int = 0

    # Rates (Percentages 0.0 to 100.0)
    compliance_rate: float = 0.0
    needs_review_rate: float = 0.0
    non_compliance_rate: float = 0.0

    # Financial Aggregates
    total_taxable_value: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")

    # Gate & Rule Failure Counts
    failed_gate_count: int = 0          # Total gate failure instances in period
    rule_failure_counts: Dict[str, int] = field(default_factory=dict)
    gate_failure_counts: Dict[int, int] = field(default_factory=dict)

    # Lineage: Supporting Invoice IDs
    invoices: List[str] = field(default_factory=list)

    def calculate_rates(self) -> None:
        """Calculate compliance, review, and non-compliance rates from counts."""
        if self.total_invoices > 0:
            self.compliance_rate = round((self.compliant_count / self.total_invoices) * 100.0, 2)
            self.needs_review_rate = round((self.needs_review_count / self.total_invoices) * 100.0, 2)
            self.non_compliance_rate = round((self.non_compliant_count / self.total_invoices) * 100.0, 2)
        else:
            self.compliance_rate = 0.0
            self.needs_review_rate = 0.0
            self.non_compliance_rate = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "period_key": self.period_key,
            "period_type": self.period_type.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "total_invoices": self.total_invoices,
            "compliant_count": self.compliant_count,
            "needs_review_count": self.needs_review_count,
            "non_compliant_count": self.non_compliant_count,
            "compliance_rate": self.compliance_rate,
            "needs_review_rate": self.needs_review_rate,
            "non_compliance_rate": self.non_compliance_rate,
            "total_taxable_value": float(self.total_taxable_value),
            "total_tax": float(self.total_tax),
            "total_amount": float(self.total_amount),
            "failed_gate_count": self.failed_gate_count,
            "rule_failure_counts": self.rule_failure_counts,
            "gate_failure_counts": {str(k): v for k, v in self.gate_failure_counts.items()},
            "invoices": self.invoices,
        }
