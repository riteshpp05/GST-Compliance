"""
app.investigation.evidence.models
=================================
Container and indexed context models for investigation evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.domain.models.invoice import Invoice
from app.domain.models.risk import RiskAssessment
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models.impact import FinancialImpact
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.investigation.models import RootCauseEvidence


@dataclass
class EvidenceContext:
    """
    Indexed evidence context enabling high-performance, deterministic pattern matching.
    Prevents repetitive O(N^2) scans across dimensions.
    """
    total_invoices: int = 0
    invoices: List[Invoice] = field(default_factory=list)
    decisions: List[ComplianceDecision] = field(default_factory=list)

    # Core indices by invoice_id
    invoice_map: Dict[str, Invoice] = field(default_factory=dict)
    decision_map: Dict[str, ComplianceDecision] = field(default_factory=dict)
    financial_impacts_map: Dict[str, FinancialImpact] = field(default_factory=dict)
    duplicates_map: Dict[str, List[DuplicateCandidate]] = field(default_factory=dict)
    anomalies_map: Dict[str, List[AnomalyFinding]] = field(default_factory=dict)

    # Dimensional indices (mapping -> set of invoice_ids)
    invoices_by_counterparty: Dict[str, Set[str]] = field(default_factory=dict)
    counterparty_names: Dict[str, str] = field(default_factory=dict)
    invoices_by_period: Dict[str, Set[str]] = field(default_factory=dict)
    invoices_by_hsn: Dict[str, Set[str]] = field(default_factory=dict)
    invoices_by_state: Dict[str, Set[str]] = field(default_factory=dict)

    # Discrepancy / Failure indices
    failed_invoices: Set[str] = field(default_factory=set)
    failed_invoices_by_rule: Dict[str, Set[str]] = field(default_factory=dict)
    failed_invoices_by_gate_no: Dict[int, Set[str]] = field(default_factory=dict)
    rule_failure_details: Dict[str, List[ValidationResult]] = field(default_factory=dict)
    failed_invoices_by_counterparty: Dict[str, Set[str]] = field(default_factory=dict)
    failed_invoices_by_period: Dict[str, Set[str]] = field(default_factory=dict)
    failed_invoices_by_hsn: Dict[str, Set[str]] = field(default_factory=dict)
    failed_invoices_by_state: Dict[str, Set[str]] = field(default_factory=dict)

    # S7 Intelligence Collections
    duplicate_clusters: List[DuplicateCluster] = field(default_factory=list)
    all_duplicate_candidates: List[DuplicateCandidate] = field(default_factory=list)
    all_anomaly_findings: List[AnomalyFinding] = field(default_factory=list)

    # S5 Historical Intelligence References
    historical_patterns: List[Any] = field(default_factory=list)
    historical_trends: List[Any] = field(default_factory=list)

    # S3 Risk Information
    risk_assessments: Dict[str, Any] = field(default_factory=dict)


class EvidenceSufficiencyState(str, Enum):
    """Evaluation state of evidence completeness for finance investigation."""
    SUFFICIENT = "SUFFICIENT"
    PARTIALLY_SUFFICIENT = "PARTIALLY_SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class MissingEvidenceUrgency(str, Enum):
    """Urgency level of missing evidence items."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class MissingEvidenceItem:
    """Explicit itemization of missing evidence required for conclusive resolution."""
    evidence_type: str
    description: str
    urgency: MissingEvidenceUrgency = MissingEvidenceUrgency.MEDIUM
    impact_on_investigation: str = ""
    recommended_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type,
            "description": self.description,
            "urgency": self.urgency.value if isinstance(self.urgency, Enum) else str(self.urgency),
            "impact_on_investigation": self.impact_on_investigation,
            "recommended_action": self.recommended_action,
        }


@dataclass
class EvidenceSufficiencyReport:
    """Overall evidence evaluation report for a case or invoice."""
    case_id: str
    invoice_id: str
    sufficiency_state: EvidenceSufficiencyState = EvidenceSufficiencyState.NOT_AVAILABLE
    score: float = 0.0
    present_evidence_types: List[str] = field(default_factory=list)
    missing_evidence_items: List[MissingEvidenceItem] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "invoice_id": self.invoice_id,
            "sufficiency_state": self.sufficiency_state.value if isinstance(self.sufficiency_state, Enum) else str(self.sufficiency_state),
            "score": self.score,
            "present_evidence_types": self.present_evidence_types,
            "missing_evidence_items": [m.to_dict() for m in self.missing_evidence_items],
            "notes": self.notes,
        }

