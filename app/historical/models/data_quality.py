"""
UC15 GST Compliance Agent — Data Quality History Models (Sprint 5)
Tracks recurring data ingestion and structural data quality defects over time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DataQualityPattern:
    """
    Historical pattern tracking recurring data defects (e.g. missing state, invalid GSTIN format).
    Distinguishes operational data cleanliness from legal/statutory tax violations.
    """
    pattern_id: str
    issue_type: str                        # e.g. "MISSING_STATE", "INVALID_GSTIN_FORMAT", "MISSING_INVOICE_ID"
    description: str

    # Scope & Lineage
    counterparty_id: Optional[str] = None
    occurrence_count: int = 0
    total_invoices_evaluated: int = 0
    occurrence_rate: float = 0.0           # Percentage of evaluated invoices affected

    affected_invoices: List[str] = field(default_factory=list)
    periods_observed: List[str] = field(default_factory=list)
    is_recurring: bool = False

    # Traceable Evidence
    evidence: str = ""

    def calculate_rate(self) -> None:
        if self.total_invoices_evaluated > 0:
            self.occurrence_rate = round((self.occurrence_count / self.total_invoices_evaluated) * 100.0, 2)
        else:
            self.occurrence_rate = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "issue_type": self.issue_type,
            "description": self.description,
            "counterparty_id": self.counterparty_id,
            "occurrence_count": self.occurrence_count,
            "total_invoices_evaluated": self.total_invoices_evaluated,
            "occurrence_rate": self.occurrence_rate,
            "affected_invoices": self.affected_invoices,
            "periods_observed": self.periods_observed,
            "is_recurring": self.is_recurring,
            "evidence": self.evidence,
        }
