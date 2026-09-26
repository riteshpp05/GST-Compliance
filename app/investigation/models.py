"""
app.investigation.models
========================
Canonical data models for Root Cause & Blast Radius Intelligence (Sprint 8 + 9).
Provides strongly typed contracts for scores, evidence, root cause candidates,
blast radius profiles, and unified investigation profiles.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from app.investigation.enums import (
    EvidenceType,
    InvestigationStatus,
    RootCauseConfidence,
    RootCauseLikelihood,
    RootCauseStatus,
    RootCauseType,
    SystemicClassification,
    TrendClassification,
)


def _serialize_val(val: Any) -> Any:
    """Helper to cleanly serialize Decimal, Enums, and nested structures."""
    if isinstance(val, Decimal):
        return float(val)
    if hasattr(val, "value"):
        return val.value
    if isinstance(val, dict):
        return {k: _serialize_val(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_val(v) for v in val]
    return val


@dataclass
class RootCauseScore:
    """
    Deterministic score breakdown for a root cause candidate.
    Weights sum to 100.0 max.
    """
    evidence_strength: float = 0.0          # Max 30.0
    pattern_recurrence: float = 0.0         # Max 20.0
    population_coverage: float = 0.0        # Max 20.0
    temporal_consistency: float = 0.0       # Max 10.0
    counterparty_concentration: float = 0.0 # Max 10.0
    rule_concentration: float = 0.0         # Max 10.0
    total_score: float = 0.0                # Total (0.0 - 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_strength": round(self.evidence_strength, 2),
            "pattern_recurrence": round(self.pattern_recurrence, 2),
            "population_coverage": round(self.population_coverage, 2),
            "temporal_consistency": round(self.temporal_consistency, 2),
            "counterparty_concentration": round(self.counterparty_concentration, 2),
            "rule_concentration": round(self.rule_concentration, 2),
            "total_score": round(self.total_score, 2),
        }


@dataclass
class RootCauseEvidence:
    """
    Individual verifiable evidence item supporting a root cause candidate.
    """
    evidence_id: str
    evidence_type: EvidenceType
    title: str
    description: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    affected_count: int = 0
    source_ids: List[str] = field(default_factory=list)
    weight: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type.value,
            "title": self.title,
            "description": self.description,
            "metrics": _serialize_val(self.metrics),
            "affected_count": self.affected_count,
            "source_ids": self.source_ids,
            "weight": round(self.weight, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class RootCauseFinding:
    """
    Structured hypothesis regarding the underlying driver of compliance findings.
    Adheres strictly to causality-safe phrasing.
    """
    root_cause_id: str
    root_cause_type: RootCauseType
    title: str
    description: str
    status: RootCauseStatus = RootCauseStatus.ACTIVE
    confidence: RootCauseConfidence = RootCauseConfidence.MEDIUM
    likelihood: RootCauseLikelihood = RootCauseLikelihood.MEDIUM
    severity: str = "MEDIUM"
    score: RootCauseScore = field(default_factory=RootCauseScore)
    causality_statement: str = ""
    evidence: List[RootCauseEvidence] = field(default_factory=list)
    affected_invoice_ids: List[str] = field(default_factory=list)
    supporting_finding_ids: List[str] = field(default_factory=list)
    supporting_rule_ids: List[str] = field(default_factory=list)
    supporting_counterparty_ids: List[str] = field(default_factory=list)
    supporting_periods: List[str] = field(default_factory=list)
    financial_exposure: Decimal = field(default=Decimal("0.00"))
    detector_version: str = "1.0"
    lineage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_cause_id": self.root_cause_id,
            "root_cause_type": self.root_cause_type.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "confidence": self.confidence.value,
            "likelihood": self.likelihood.value,
            "severity": self.severity,
            "score": self.score.to_dict(),
            "causality_statement": self.causality_statement,
            "evidence": [e.to_dict() for e in self.evidence],
            "affected_invoice_ids": self.affected_invoice_ids,
            "supporting_finding_ids": self.supporting_finding_ids,
            "supporting_rule_ids": self.supporting_rule_ids,
            "supporting_counterparty_ids": self.supporting_counterparty_ids,
            "supporting_periods": self.supporting_periods,
            "financial_exposure": float(self.financial_exposure),
            "detector_version": self.detector_version,
            "lineage": _serialize_val(self.lineage),
        }


@dataclass
class BlastRadiusProfile:
    """
    Multidimensional quantification of the affected population and impact boundaries.
    Reconciles with S3 (Risk), S5 (History), S6 (Financial Exposure), and S7 (Duplicates/Anomalies).
    """
    blast_radius_id: str
    root_cause_id: str

    # Populations & Coverage
    total_population_count: int = 0
    affected_invoice_count: int = 0
    affected_ratio: float = 0.0
    affected_counterparty_count: int = 0
    affected_rule_count: int = 0
    affected_period_count: int = 0
    affected_hsn_count: int = 0
    affected_state_count: int = 0

    # Concrete Entity Sets
    affected_invoice_ids: List[str] = field(default_factory=list)
    affected_counterparties: List[str] = field(default_factory=list)
    affected_rules: List[str] = field(default_factory=list)
    affected_periods: List[str] = field(default_factory=list)
    affected_hsns: List[str] = field(default_factory=list)
    affected_states: List[str] = field(default_factory=list)

    # Financial Exposure (Reconciled from S6, no double counting)
    total_potential_exposure: Decimal = field(default=Decimal("0.00"))
    average_exposure: Decimal = field(default=Decimal("0.00"))
    maximum_exposure: Decimal = field(default=Decimal("0.00"))
    exposure_by_type: Dict[str, Decimal] = field(default_factory=dict)

    # Temporal Dynamics
    first_detected_period: Optional[str] = None
    last_detected_period: Optional[str] = None
    duration_periods: int = 0
    period_distribution: Dict[str, int] = field(default_factory=dict)
    trend: TrendClassification = TrendClassification.INSUFFICIENT_DATA

    # Risk Distribution (Reconciled from S3)
    severity_distribution: Dict[str, int] = field(default_factory=dict)
    priority_distribution: Dict[str, int] = field(default_factory=dict)

    # Duplicate & Anomaly Signals (Reconciled from S7)
    duplicate_affected_count: int = 0
    anomaly_affected_count: int = 0
    duplicate_and_anomaly_overlap_count: int = 0
    duplicate_candidate_ids: List[str] = field(default_factory=list)
    anomaly_finding_ids: List[str] = field(default_factory=list)

    # Concentration Analysis
    top_counterparty_share: float = 0.0
    top_counterparty_id: Optional[str] = None
    top_rule_share: float = 0.0
    top_rule_id: Optional[str] = None
    top_period_share: float = 0.0
    top_period: Optional[str] = None
    top_hsn_share: float = 0.0
    top_hsn: Optional[str] = None
    top_state_share: float = 0.0
    top_state: Optional[str] = None

    # Systemic Classification
    systemic_classification: SystemicClassification = SystemicClassification.INSUFFICIENT_DATA

    # Provenance & Metadata
    lineage: Dict[str, Any] = field(default_factory=dict)
    detector_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blast_radius_id": self.blast_radius_id,
            "root_cause_id": self.root_cause_id,
            "total_population_count": self.total_population_count,
            "affected_invoice_count": self.affected_invoice_count,
            "affected_ratio": round(self.affected_ratio, 4),
            "affected_counterparty_count": self.affected_counterparty_count,
            "affected_rule_count": self.affected_rule_count,
            "affected_period_count": self.affected_period_count,
            "affected_hsn_count": self.affected_hsn_count,
            "affected_state_count": self.affected_state_count,
            "affected_invoice_ids": self.affected_invoice_ids,
            "affected_counterparties": self.affected_counterparties,
            "affected_rules": self.affected_rules,
            "affected_periods": self.affected_periods,
            "affected_hsns": self.affected_hsns,
            "affected_states": self.affected_states,
            "total_potential_exposure": float(self.total_potential_exposure),
            "average_exposure": float(self.average_exposure),
            "maximum_exposure": float(self.maximum_exposure),
            "exposure_by_type": {k: float(v) for k, v in self.exposure_by_type.items()},
            "first_detected_period": self.first_detected_period,
            "last_detected_period": self.last_detected_period,
            "duration_periods": self.duration_periods,
            "period_distribution": self.period_distribution,
            "trend": self.trend.value,
            "severity_distribution": self.severity_distribution,
            "priority_distribution": self.priority_distribution,
            "duplicate_affected_count": self.duplicate_affected_count,
            "anomaly_affected_count": self.anomaly_affected_count,
            "duplicate_and_anomaly_overlap_count": self.duplicate_and_anomaly_overlap_count,
            "duplicate_candidate_ids": self.duplicate_candidate_ids,
            "anomaly_finding_ids": self.anomaly_finding_ids,
            "top_counterparty_share": round(self.top_counterparty_share, 4),
            "top_counterparty_id": self.top_counterparty_id,
            "top_rule_share": round(self.top_rule_share, 4),
            "top_rule_id": self.top_rule_id,
            "top_period_share": round(self.top_period_share, 4),
            "top_period": self.top_period,
            "top_hsn_share": round(self.top_hsn_share, 4),
            "top_hsn": self.top_hsn,
            "top_state_share": round(self.top_state_share, 4),
            "top_state": self.top_state,
            "systemic_classification": self.systemic_classification.value,
            "lineage": _serialize_val(self.lineage),
            "detector_version": self.detector_version,
        }


@dataclass
class InvestigationProfile:
    """
    Comprehensive investigation case dossier integrating Root Cause, Blast Radius,
    Financial Exposure, Risk, Duplicates, Anomalies, Timeline, and Lineage.
    Serves as the primary contract consumed by future AI Agents (Sprint 11).
    """
    investigation_id: str
    title: str
    status: InvestigationStatus = InvestigationStatus.OPEN
    primary_root_cause: Optional[RootCauseFinding] = None
    root_cause_candidates: List[RootCauseFinding] = field(default_factory=list)
    blast_radius: Optional[BlastRadiusProfile] = None

    # Key Summary Dimensions
    financial_exposure: Decimal = field(default=Decimal("0.00"))
    exposure_summary: Dict[str, Any] = field(default_factory=dict)
    risk_distribution: Dict[str, int] = field(default_factory=dict)
    duplicate_signals_summary: Dict[str, Any] = field(default_factory=dict)
    anomaly_signals_summary: Dict[str, Any] = field(default_factory=dict)
    historical_pattern_summary: Dict[str, Any] = field(default_factory=dict)
    concentration_summary: Dict[str, Any] = field(default_factory=dict)
    trend: str = "INSUFFICIENT_DATA"
    systemic_classification: str = "INSUFFICIENT_DATA"

    # Deterministic Timeline & Evidence Graph
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    evidence_graph: Dict[str, List[str]] = field(default_factory=dict)
    recommended_investigation_areas: List[str] = field(default_factory=list)

    # Lineage and Metadata
    lineage: Dict[str, Any] = field(default_factory=dict)
    detector_version: str = "1.0"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "investigation_id": self.investigation_id,
            "title": self.title,
            "status": self.status.value,
            "primary_root_cause": self.primary_root_cause.to_dict() if self.primary_root_cause else None,
            "root_cause_candidates": [c.to_dict() for c in self.root_cause_candidates],
            "blast_radius": self.blast_radius.to_dict() if self.blast_radius else None,
            "financial_exposure": float(self.financial_exposure),
            "exposure_summary": _serialize_val(self.exposure_summary),
            "risk_distribution": self.risk_distribution,
            "duplicate_signals_summary": _serialize_val(self.duplicate_signals_summary),
            "anomaly_signals_summary": _serialize_val(self.anomaly_signals_summary),
            "historical_pattern_summary": _serialize_val(self.historical_pattern_summary),
            "concentration_summary": _serialize_val(self.concentration_summary),
            "trend": self.trend,
            "systemic_classification": self.systemic_classification,
            "timeline": self.timeline,
            "evidence_graph": self.evidence_graph,
            "recommended_investigation_areas": self.recommended_investigation_areas,
            "lineage": _serialize_val(self.lineage),
            "detector_version": self.detector_version,
            "timestamp": self.timestamp,
        }
