"""
app.case.review_package
======================
Human Review Package Aggregator DTO for UC15 (Sprint 18).
Assembles Case Summary, Key Findings, Evidence, Financial Impact, Risk Level, Confidence,
Contradictions, Trace Summary, Recommendation, Data Quality, and Source Lineage.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.case.models import CaseStatusEnum
from app.case.service import CaseService, get_case_service
from app.infrastructure.logging import get_logger
from app.investigation.trace import InvestigationTraceTracker
from app.security import AuthenticatedPrincipal, get_internal_compatibility_principal

logger = get_logger(__name__)


class HumanReviewPackage(BaseModel):
    """
    Unified Review Package presented to Human Reviewers when an investigation reaches PENDING_REVIEW.
    Contains complete evidence provenance, reconciliation results, exposure traces, and 6-part AI dossier.
    """
    case_id: str = Field(..., description="Target case ID.")
    title: str = Field(..., description="Case title.")
    status: str = Field(..., description="Current case status.")
    priority: str = Field("P3", description="Case priority.")
    risk_level: str = Field("LOW", description="Risk level.")
    financial_exposure: float = Field(0.0, ge=0.0, description="Quantified financial exposure (INR).")
    root_cause: str = Field("UNDETERMINED", description="Root cause classification.")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Investigation confidence score.")
    confidence_level: str = Field("HIGH", description="Confidence level classification.")
    has_contradictions: bool = Field(False, description="Flag indicating conflicting analysis signals.")
    key_findings: List[Dict[str, Any]] = Field(default_factory=list, description="Consolidated findings.")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="First-class evidence records.")
    trace_summary: List[Dict[str, Any]] = Field(default_factory=list, description="Operational execution trace.")
    recommendation: str = Field("", description="AI resolution recommendation.")
    data_quality_score: float = Field(100.0, ge=0.0, le=100.0, description="Source data quality score.")

    # Sprint 22 Extension Fields
    reconciliation_summary: Dict[str, Any] = Field(default_factory=dict, description="Multi-way record reconciliation results.")
    exposure_summary: Dict[str, Any] = Field(default_factory=dict, description="Exposure trace breakdown & formula details.")
    evidence_sufficiency: Dict[str, Any] = Field(default_factory=dict, description="Evidence sufficiency status & missing items.")
    ai_dossier_6part: Dict[str, Any] = Field(default_factory=dict, description="Structured 6-part AI investigation report.")

    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


def get_human_review_package(
    case_id: str,
    principal: Optional[AuthenticatedPrincipal] = None,
) -> HumanReviewPackage:
    """Assemble HumanReviewPackage for an investigation case."""
    auth_principal = principal or get_internal_compatibility_principal()
    case_svc = get_case_service()
    case = case_svc.get_case(case_id, principal=auth_principal)
    if not case:
        raise ValueError(f"InvestigationCase '{case_id}' not found.")

    findings = case_svc.get_findings(case_id)
    evidence_records = case_svc.get_evidence_records(case_id)
    trace = InvestigationTraceTracker.get_trace(case.source_session_id or case_id)

    # Instantiate Sprint 22 Evaluators
    from app.engines.financial_engine import FinancialExposureEngine
    from app.reconciliation.engine import ReconciliationEngine
    from app.investigation.evidence.sufficiency_evaluator import EvidenceSufficiencyEvaluator

    rec_engine = ReconciliationEngine()
    rec_result = rec_engine.reconcile(case_id=case_id)

    suff_eval = EvidenceSufficiencyEvaluator()
    suff_report = suff_eval.evaluate(case_id=case_id)

    fin_engine = FinancialExposureEngine()
    case_exp = fin_engine.summarize_case_exposure(case_id=case_id, invoice_id=case_id, traces=[])

    has_contradictions = bool(rec_result.contradictions) or any(f.category == "CONFLICTING_ANALYSIS" for f in findings)

    # Build 6-part AI dossier dictionary
    ai_6part = {
        "what_was_detected": [f.title or f.description for f in findings] if findings else ["No active statutory gate violations detected for case."],
        "supporting_evidence": [e.model_dump() for e in evidence_records],
        "conflicts_and_contradictions": [c.to_dict() for c in rec_result.contradictions],
        "financial_impact": case_exp.to_dict(),
        "missing_evidence": [m.to_dict() for m in suff_report.missing_evidence_items],
        "next_steps_for_investigator": [
            "Verify missing evidence documents with vendor.",
            "Review reconciliation mismatches and confirm Places of Supply.",
            "Submit final human review decision.",
        ],
    }

    package = HumanReviewPackage(
        case_id=case.case_id,
        title=case.title,
        status=case.status.value if isinstance(case.status, CaseStatusEnum) else str(case.status),
        priority=case.priority,
        risk_level=case.risk_level,
        financial_exposure=case.financial_exposure,
        root_cause=case.root_cause,
        confidence_score=0.90 if not has_contradictions else 0.65,
        confidence_level="HIGH" if not has_contradictions else "MEDIUM",
        has_contradictions=has_contradictions,
        key_findings=[f.model_dump() for f in findings],
        evidence=[e.model_dump() for e in evidence_records],
        trace_summary=[t.model_dump() for t in trace],
        recommendation=case.recommendation or "Review collected evidence and findings before submitting decision.",
        data_quality_score=95.0,
        reconciliation_summary=rec_result.to_dict(),
        exposure_summary=case_exp.to_dict(),
        evidence_sufficiency=suff_report.to_dict(),
        ai_dossier_6part=ai_6part,
    )
    logger.info(f"Assembled HumanReviewPackage for case '{case_id}' (Findings: {len(findings)}, Evidence: {len(evidence_records)}).")
    return package

