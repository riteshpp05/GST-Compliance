"""
UC15 GST Compliance Agent — Dual Confidence Model (Sprint 23)
Maintains strict separation between System Confidence (deterministic statutory certainty)
and AI Confidence (explanation synthesis quality). Prevents combining scores into a single misleading value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.investigation.ai.context_builder import ControlledInvestigationContext


@dataclass
class DualConfidenceResult:
    case_id: str
    system_confidence: float = 1.0
    system_confidence_level: str = "HIGH"
    ai_confidence: float = 0.90
    ai_confidence_level: str = "HIGH"
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "system_confidence": self.system_confidence,
            "system_confidence_level": self.system_confidence_level,
            "ai_confidence": self.ai_confidence,
            "ai_confidence_level": self.ai_confidence_level,
            "explanation": self.explanation,
        }


class DualConfidenceModel:
    """
    Evaluates and preserves separate System Confidence and AI Confidence semantics.
    """

    def evaluate(
        self,
        context: ControlledInvestigationContext,
        grounding_result: Optional[Dict[str, Any]] = None,
    ) -> DualConfidenceResult:
        case_id = context.case_id

        # 1. System Confidence (Deterministic Statutory & Evidence Certainty)
        # 1.0 if clean or deterministic findings present with no evidence gaps, lower if contradictions
        sys_conf = 1.0
        if context.contradictions:
            sys_conf -= 0.25 * len(context.contradictions)
        if context.missing_evidence:
            sys_conf -= 0.10 * len(context.missing_evidence)

        sys_conf = max(0.20, min(1.0, round(sys_conf, 2)))

        if sys_conf >= 0.85:
            sys_lvl = "HIGH"
        elif sys_conf >= 0.55:
            sys_lvl = "MEDIUM"
        else:
            sys_lvl = "LOW"

        # 2. AI Confidence (Synthesized Explanation & Grounding Score)
        ai_conf = 0.95
        if grounding_result:
            ratio = grounding_result.get("grounded_ratio", 1.0)
            ai_conf = round(ratio * 0.95, 2)

        if ai_conf >= 0.85:
            ai_lvl = "HIGH"
        elif ai_conf >= 0.55:
            ai_lvl = "MEDIUM"
        else:
            ai_lvl = "LOW"

        explanation = (
            f"System statutory confidence is {sys_lvl} ({sys_conf}). "
            f"AI explanation synthesis confidence is {ai_lvl} ({ai_conf})."
        )

        return DualConfidenceResult(
            case_id=case_id,
            system_confidence=sys_conf,
            system_confidence_level=sys_lvl,
            ai_confidence=ai_conf,
            ai_confidence_level=ai_lvl,
            explanation=explanation,
        )
