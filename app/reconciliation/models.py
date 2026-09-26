"""
UC15 GST Compliance Agent — Reconciliation Models (Sprint 22)
Defines data structures for multi-way financial record reconciliation and contradiction detection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class ReconciliationStatus(str, Enum):
    """Status of cross-record comparison."""
    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    CONFLICTING = "CONFLICTING"


class ContradictionSeverity(str, Enum):
    """Severity of cross-signal contradiction."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ReconciliationPair:
    """
    Comparison result between invoice attribute and external reference/source.
    """
    dimension: str  # e.g., INVOICE_VS_TAX_CALC, INVOICE_VS_GSTR2B, INVOICE_VS_SUPPLIER_ERP, INVOICE_VS_TAX_PERIOD
    status: ReconciliationStatus = ReconciliationStatus.NOT_AVAILABLE
    invoice_value: Any = None
    counterpart_value: Any = None
    delta: Any = None
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "invoice_value": self.invoice_value,
            "counterpart_value": self.counterpart_value,
            "delta": self.delta,
            "explanation": self.explanation,
        }


@dataclass
class ContradictionFinding:
    """
    Direct contradiction detected across available evidence signals.
    """
    contradiction_id: str
    contradiction_type: str
    severity: ContradictionSeverity = ContradictionSeverity.MEDIUM
    description: str = ""
    conflicting_signals: List[Dict[str, Any]] = field(default_factory=list)
    impact_on_validity: str = ""
    recommended_investigation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "contradiction_type": self.contradiction_type,
            "severity": self.severity.value if isinstance(self.severity, Enum) else str(self.severity),
            "description": self.description,
            "conflicting_signals": self.conflicting_signals,
            "impact_on_validity": self.impact_on_validity,
            "recommended_investigation": self.recommended_investigation,
        }


@dataclass
class ReconciliationResult:
    """
    Aggregated multi-way reconciliation output for a case.
    """
    case_id: str
    invoice_id: str
    overall_status: ReconciliationStatus = ReconciliationStatus.NOT_AVAILABLE
    pairs: List[ReconciliationPair] = field(default_factory=list)
    contradictions: List[ContradictionFinding] = field(default_factory=list)
    reconciled_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "invoice_id": self.invoice_id,
            "overall_status": self.overall_status.value if isinstance(self.overall_status, Enum) else str(self.overall_status),
            "pairs": [p.to_dict() for p in self.pairs],
            "contradictions": [c.to_dict() for c in self.contradictions],
            "reconciled_at": self.reconciled_at,
        }
