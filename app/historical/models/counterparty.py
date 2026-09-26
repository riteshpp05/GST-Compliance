"""
UC15 GST Compliance Agent — Counterparty Historical Intelligence Models (Sprint 5)
Provides vendor/customer compliance profiling and recurring counterparty anomaly patterns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from app.historical.models.trend import TrendDirection


@dataclass
class CounterpartyProfile:
    """
    Historical compliance trajectory and violation summary for a specific counterparty (Vendor or Customer).
    """
    counterparty_id: str                   # GSTIN or legal name
    counterparty_name: str
    gstin: str
    direction: str = "AR"                  # "AR" (outward/customer) | "AP" (inward/vendor)

    # Historical Invoicing Volume
    total_invoices: int = 0
    compliant_count: int = 0
    needs_review_count: int = 0
    non_compliant_count: int = 0
    compliance_rate: float = 0.0           # Percentage 0.0 to 100.0

    # Failure Summaries
    total_failures: int = 0
    top_failed_rules: List[Tuple[str, int]] = field(default_factory=list)  # [(rule_id, count)]

    # Temporal Activity
    first_transaction_date: Optional[date] = None
    last_transaction_date: Optional[date] = None
    periods_active: List[str] = field(default_factory=list)
    recent_trend: Optional[TrendDirection] = None

    # Lineage
    affected_invoices: List[str] = field(default_factory=list)

    # Aliases for Section 11 compatibility
    @property
    def invoice_count(self) -> int:
        return self.total_invoices

    @property
    def failure_count(self) -> int:
        return self.total_failures

    @property
    def period_trend(self) -> Optional[TrendDirection]:
        return self.recent_trend

    def calculate_rate(self) -> None:
        if self.total_invoices > 0:
            self.compliance_rate = round((self.compliant_count / self.total_invoices) * 100.0, 2)
        else:
            self.compliance_rate = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "gstin": self.gstin,
            "direction": self.direction,
            "total_invoices": self.total_invoices,
            "compliant_count": self.compliant_count,
            "needs_review_count": self.needs_review_count,
            "non_compliant_count": self.non_compliant_count,
            "compliance_rate": self.compliance_rate,
            "total_failures": self.total_failures,
            "top_failed_rules": [{"rule_id": r, "count": c} for r, c in self.top_failed_rules],
            "first_transaction_date": self.first_transaction_date.isoformat() if self.first_transaction_date else None,
            "last_transaction_date": self.last_transaction_date.isoformat() if self.last_transaction_date else None,
            "periods_active": self.periods_active,
            "recent_trend": self.recent_trend.value if self.recent_trend else None,
            "affected_invoices": self.affected_invoices,
        }


@dataclass
class RecurringCounterpartyPattern:
    """
    Identifies systemic identical compliance mismatches from a counterparty across multiple periods.
    Example: Vendor ABC consistently applies 12% IGST on HSN 8471 (statutory rate 18%) across 4 periods.
    """
    pattern_id: str
    counterparty_id: str
    counterparty_name: str
    pattern_type: str = "RECURRING_COUNTERPARTY_PATTERN"

    # Contextual specifics
    issue_type: str = ""                   # e.g. "TAX_RATE_MISMATCH", "HSN_INVALID", "BLOCKED_ITC"
    hsn_code: Optional[str] = None
    rule_id: Optional[str] = None
    expected_value: Optional[Any] = None
    applied_value: Optional[Any] = None

    # Frequency & Lineage
    occurrences: int = 0
    periods_observed: List[str] = field(default_factory=list)
    affected_invoices: List[str] = field(default_factory=list)

    # Explainable Evidence
    evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "pattern_type": self.pattern_type,
            "issue_type": self.issue_type,
            "hsn_code": self.hsn_code,
            "rule_id": self.rule_id,
            "expected_value": str(self.expected_value) if self.expected_value is not None else None,
            "applied_value": str(self.applied_value) if self.applied_value is not None else None,
            "occurrences": self.occurrences,
            "periods_observed": self.periods_observed,
            "affected_invoices": self.affected_invoices,
            "evidence": self.evidence,
        }
