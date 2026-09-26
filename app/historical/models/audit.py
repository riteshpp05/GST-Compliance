"""
UC15 GST Compliance Agent — Historical Audit & Retroactive Simulation Models (Sprint 5)
Provides models for comparing recorded compliance outcomes against retroactive evaluations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class AuditOutcome(str, Enum):
    """Categorization of retroactive historical audit comparison."""
    SAME_RESULT = "SAME_RESULT"                      # Evaluated identically under historical reference
    RESULT_CHANGED = "RESULT_CHANGED"                # Overall compliance status changed
    PREVIOUSLY_UNRESOLVED = "PREVIOUSLY_UNRESOLVED"  # Was NEEDS_REVIEW due to missing data, now resolved
    NEWLY_NON_COMPLIANT = "NEWLY_NON_COMPLIANT"      # Was COMPLIANT, now NON_COMPLIANT
    NEWLY_COMPLIANT = "NEWLY_COMPLIANT"              # Was NON_COMPLIANT, now COMPLIANT
    REFERENCE_CHANGED = "REFERENCE_CHANGED"          # Reference record version changed between runs


@dataclass
class HistoricalAuditComparison:
    """
    Detailed audit result comparing a recorded historical compliance verdict
    against a retroactive evaluation using transaction-date effective reference intelligence.
    """
    invoice_id: str
    invoice_date: date

    # Verdicts
    original_status: str                             # Original recorded status (e.g. COMPLIANT, NON_COMPLIANT)
    retroactive_status: str                          # Retroactive evaluation status
    outcome: AuditOutcome

    # Reference Versions & Differences
    original_reference_versions: Dict[str, str] = field(default_factory=dict)
    retroactive_reference_versions: Dict[str, str] = field(default_factory=dict)
    reference_differences: List[str] = field(default_factory=list)

    # Gate-level discrepancies
    original_failed_rules: List[str] = field(default_factory=list)
    retroactive_failed_rules: List[str] = field(default_factory=list)

    # Explainable Statutory Evidence
    reason: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "invoice_date": self.invoice_date.isoformat(),
            "original_status": self.original_status,
            "retroactive_status": self.retroactive_status,
            "outcome": self.outcome.value,
            "original_reference_versions": self.original_reference_versions,
            "retroactive_reference_versions": self.retroactive_reference_versions,
            "reference_differences": self.reference_differences,
            "original_failed_rules": self.original_failed_rules,
            "retroactive_failed_rules": self.retroactive_failed_rules,
            "reason": self.reason,
            "evidence": self.evidence,
        }
