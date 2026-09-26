"""
UC15 GST Compliance Agent — Evidence Grounding Evaluator (Sprint 23)
Enforces strict traceable grounding of AI assertions against available evidence and findings.
Detects and rejects unsupported or hallucinated factual claims.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from app.investigation.ai.context_builder import ControlledInvestigationContext


class GroundingStatus(str, Enum):
    """Grounding status of an AI assertion against context evidence."""
    GROUNDED = "GROUNDED"
    PARTIALLY_GROUNDED = "PARTIALLY_GROUNDED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"


@dataclass
class AIClaim:
    """
    Individual factual or analytical assertion made in AI investigation output.
    """
    claim_id: str
    claim_text: str
    claim_type: str = "FACTUAL"  # FACTUAL | INFERENCE | RECOMMENDATION | SUMMARY
    source_ids: List[str] = field(default_factory=list)
    source_type: str = "FINDING"
    grounding_status: GroundingStatus = GroundingStatus.UNSUPPORTED
    confidence: float = 0.0
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "claim_text": self.claim_text,
            "claim_type": self.claim_type,
            "source_ids": self.source_ids,
            "source_type": self.source_type,
            "grounding_status": self.grounding_status.value if isinstance(self.grounding_status, Enum) else str(self.grounding_status),
            "confidence": self.confidence,
            "reason": self.reason,
        }


class EvidenceGroundingEvaluator:
    """
    Evaluates AI claims against ControlledInvestigationContext source IDs and facts.
    """

    def evaluate_claim(
        self,
        claim: AIClaim,
        context: ControlledInvestigationContext,
    ) -> AIClaim:
        valid_sources = context.get_valid_source_ids()

        if not claim.source_ids:
            claim.grounding_status = GroundingStatus.UNSUPPORTED
            claim.confidence = 0.0
            claim.reason = "Claim does not cite any context source ID."
            return claim

        cited_valid = [s for s in claim.source_ids if s in valid_sources]
        cited_invalid = [s for s in claim.source_ids if s not in valid_sources]

        if cited_invalid and not cited_valid:
            claim.grounding_status = GroundingStatus.UNSUPPORTED
            claim.confidence = 0.0
            claim.reason = f"Cited source IDs {cited_invalid} do not exist in investigation context."
            return claim

        if cited_invalid and cited_valid:
            claim.grounding_status = GroundingStatus.PARTIALLY_GROUNDED
            claim.confidence = 0.50
            claim.reason = f"Some cited sources exist ({cited_valid}), but unknown sources cited ({cited_invalid})."
            return claim

        # Check for contradictions in context
        if context.contradictions:
            for c in context.contradictions:
                c_id = c.get("contradiction_id")
                if c_id and c_id in claim.source_ids:
                    claim.grounding_status = GroundingStatus.CONTRADICTED
                    claim.confidence = 0.60
                    claim.reason = f"Claim references contradictory signal context '{c_id}'."
                    return claim

        claim.grounding_status = GroundingStatus.GROUNDED
        claim.confidence = 0.95
        claim.reason = f"Claim fully grounded in valid context source IDs {cited_valid}."
        return claim

    def evaluate_response_grounding(
        self,
        claims: List[AIClaim],
        context: ControlledInvestigationContext,
    ) -> Dict[str, Any]:
        evaluated = [self.evaluate_claim(c, context) for c in claims]
        total = len(evaluated)
        if total == 0:
            return {
                "overall_grounding_status": "GROUNDED",
                "grounded_ratio": 1.0,
                "unsupported_claims": [],
                "claims": [],
            }

        grounded_count = sum(1 for c in evaluated if c.grounding_status == GroundingStatus.GROUNDED)
        unsupported = [c.to_dict() for c in evaluated if c.grounding_status in (GroundingStatus.UNSUPPORTED, GroundingStatus.CONTRADICTED)]
        ratio = round(grounded_count / total, 2)

        if ratio >= 0.90:
            overall = "GROUNDED"
        elif ratio >= 0.60:
            overall = "PARTIALLY_GROUNDED"
        else:
            overall = "UNSUPPORTED"

        return {
            "overall_grounding_status": overall,
            "grounded_ratio": ratio,
            "unsupported_claims": unsupported,
            "claims": [c.to_dict() for c in evaluated],
        }
