"""
UC15 GST Compliance Agent — Rule Failure Pattern Models (Sprint 5)
Provides deterministic classification of recurring, persistent, emerging, improving, and resolved rule violations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class RulePatternClassification(str, Enum):
    """Deterministic classification of rule failure patterns across time periods."""
    PERSISTENT = "PERSISTENT"    # Fails repeatedly across consecutive periods
    EMERGING = "EMERGING"        # Previously absent or low, sharply surged in latest period
    IMPROVING = "IMPROVING"      # Failure frequency/rate consistently decreasing
    RESOLVED = "RESOLVED"        # Was failing in prior periods, zero failures in latest period
    ISOLATED = "ISOLATED"        # Rare or sporadic failure without systemic recurring pattern


@dataclass
class RuleFailurePattern:
    """
    Deterministic historical finding tracking a statutory rule's failure profile over time.
    """
    pattern_id: str
    rule_id: str
    rule_category: str
    classification: RulePatternClassification

    # Occurrences and Lineage
    total_failures: int
    affected_invoice_count: int
    affected_invoices: List[str] = field(default_factory=list)

    # Temporal Span
    first_seen_period: str = ""
    last_seen_period: str = ""
    periods_observed: List[str] = field(default_factory=list)
    period_counts: Dict[str, int] = field(default_factory=dict)

    # Metrics in latest evaluated period
    latest_period: str = ""
    latest_failure_count: int = 0
    latest_failure_rate: float = 0.0

    # Human and Audit Explanation
    trend_description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    # Aliases for Section 9 compatibility
    @property
    def period(self) -> str:
        return self.latest_period

    @property
    def failure_count(self) -> int:
        return self.total_failures

    @property
    def failure_rate(self) -> float:
        return self.latest_failure_rate

    @property
    def trend(self) -> str:
        return self.trend_description

    @property
    def first_seen(self) -> str:
        return self.first_seen_period

    @property
    def last_seen(self) -> str:
        return self.last_seen_period

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "rule_id": self.rule_id,
            "rule_category": self.rule_category,
            "classification": self.classification.value,
            "total_failures": self.total_failures,
            "affected_invoice_count": self.affected_invoice_count,
            "affected_invoices": self.affected_invoices,
            "first_seen_period": self.first_seen_period,
            "last_seen_period": self.last_seen_period,
            "periods_observed": self.periods_observed,
            "period_counts": self.period_counts,
            "latest_period": self.latest_period,
            "latest_failure_count": self.latest_failure_count,
            "latest_failure_rate": self.latest_failure_rate,
            "trend_description": self.trend_description,
            "evidence": self.evidence,
        }
