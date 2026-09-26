"""
app.investigation.explainability
================================
Structured Explanation & Unsupported Claim Detection Engine for UC15 (Sprint 18).
Generates structured explanations clearly separating FACT, INFERENCE, and RECOMMENDATION.
Detects claims lacking supporting evidence references and enforces objective safety language.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.case.models import CaseEvidenceRecord, CaseFinding
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class StructuredExplanation(BaseModel):
    """
    Auditable explanation output separating observable facts, inferences, and recommendations.
    """
    finding_id: str = Field(..., description="Target finding ID.")
    case_id: str = Field(..., description="Target case ID.")
    facts: List[str] = Field(default_factory=list, description="Observable facts grounded in empirical evidence.")
    inferences: List[str] = Field(default_factory=list, description="System inferences derived from rules and models.")
    recommendation: str = Field("", description="Recommended action.")
    supporting_evidence_ids: List[str] = Field(default_factory=list, description="Linked evidence record IDs.")
    confidence_level: str = Field("HIGH", description="Confidence level.")
    contradictions: Optional[str] = Field(None, description="Contradictory analysis signals if present.")
    is_grounded: bool = Field(True, description="True if all primary claims map to supporting evidence.")
    unsupported_claims: List[str] = Field(default_factory=list, description="Claims lacking empirical evidence linkage.")


class UnsupportedClaimDetector:
    """
    Scans generated statements to ensure claims are grounded in collected evidence items.
    """

    UNGROUNDED_TRIGGER_TERMS = ["FRAUD", "TAX EVASION", "CRIMINAL", "ILLEGAL INTENT", "GUARANTEED VIOLATION"]

    @classmethod
    def detect_unsupported_claims(
        cls,
        statement: str,
        evidence_records: List[CaseEvidenceRecord],
    ) -> List[str]:
        """Check for unsupported claims or prohibited subjective accusations."""
        unsupported: List[str] = []
        upper_text = statement.upper()

        # Check for ungrounded trigger terms
        for term in cls.UNGROUNDED_TRIGGER_TERMS:
            if term in upper_text:
                unsupported.append(
                    f"Statement contains unsupported subjective assertion '{term}'. "
                    f"UC15 safety policy requires objective compliance wording (e.g. 'Potential compliance anomaly')."
                )

        # If statement makes claims but evidence list is empty
        if statement.strip() and not evidence_records:
            unsupported.append("Claim generated without any linked supporting evidence records.")

        return unsupported


class InvestigationExplainer:
    """
    Engine generating auditable, structured explanations for case findings.
    """

    def explain_finding(
        self,
        finding: CaseFinding,
        evidence_records: List[CaseEvidenceRecord],
        confidence_level: str = "HIGH",
        contradictions: Optional[str] = None,
    ) -> StructuredExplanation:
        """
        Generate structured explanation with fact/inference separation and grounding validation.
        """
        facts: List[str] = []
        inferences: List[str] = []

        # Extract facts directly from evidence records
        for ev in evidence_records:
            facts.append(f"[{ev.evidence_type}] {ev.description}")

        if not facts:
            facts.append(f"Recorded defect category '{finding.category}' with severity '{finding.severity}'.")

        # Formulate inference
        inferences.append(f"Finding Title: {finding.title}")
        inferences.append(f"Analysis: {finding.description}")

        # Formulate recommendation based on severity
        if finding.severity == "CRITICAL":
            rec = "Hold invoice from GSTR filing cycle; require urgent tax team reconciliation."
        elif finding.severity == "HIGH":
            rec = "Flag for compliance review; request supporting invoice/challan documentation."
        else:
            rec = "Log for routine periodic audit review."

        # Detect unsupported claims
        full_text = f"{finding.title} {finding.description}"
        unsupported = UnsupportedClaimDetector.detect_unsupported_claims(full_text, evidence_records)
        is_grounded = len(unsupported) == 0

        ev_ids = [ev.evidence_id for ev in evidence_records] if evidence_records else finding.evidence_ids

        return StructuredExplanation(
            finding_id=finding.finding_id,
            case_id=finding.case_id,
            facts=facts,
            inferences=inferences,
            recommendation=rec,
            supporting_evidence_ids=ev_ids,
            confidence_level=confidence_level,
            contradictions=contradictions,
            is_grounded=is_grounded,
            unsupported_claims=unsupported,
        )
