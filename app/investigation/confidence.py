"""
app.investigation.confidence
============================
Transparent Investigation Confidence Engine for UC15 (Sprint 18).
Calculates deterministic confidence scores based on evidence count, engine consensus,
data quality, and presence of conflicting analysis signals.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Tuple
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ConfidenceLevelEnum(str, Enum):
    """Investigation confidence level classification."""
    VERY_HIGH = "VERY_HIGH"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class InvestigationConfidenceEngine:
    """
    Evaluates empirical evidence signals to compute a transparent, auditable confidence score.
    Does not rely on opaque LLM self-reports.
    """

    def calculate_confidence(
        self,
        validation_result: Optional[Dict[str, Any]] = None,
        risk_assessment: Optional[Dict[str, Any]] = None,
        evidence_count: int = 0,
        data_quality_score: float = 100.0,
        has_contradictions: bool = False,
        failed_step_count: int = 0,
    ) -> Tuple[float, ConfidenceLevelEnum, List[str]]:
        """
        Compute confidence score (0.0 to 1.0), confidence level, and rationale factors.
        """
        score = 0.70  # Baseline neutral score
        reasons: List[str] = []

        # 1. Deterministic Validation Signal
        if validation_result:
            status = str(validation_result.get("status") or validation_result.get("overall_status") or "").upper()
            if status in {"COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW"}:
                score += 0.15
                reasons.append(f"Grounded in deterministic statutory gate check (Status: {status}).")

        # 2. Evidence Volume Signal
        if evidence_count >= 5:
            score += 0.10
            reasons.append(f"Strong evidence volume ({evidence_count} evidence items collected).")
        elif evidence_count >= 2:
            score += 0.05
            reasons.append(f"Adequate evidence volume ({evidence_count} evidence items collected).")
        else:
            score -= 0.10
            reasons.append("Limited evidence items collected.")

        # 3. Engine Consensus Signal
        if validation_result and risk_assessment:
            val_failed = bool(validation_result.get("failed_gate_count", 0) > 0)
            risk_high = str(risk_assessment.get("risk_level", "")).upper() in {"HIGH", "CRITICAL"}
            if val_failed == risk_high:
                score += 0.05
                reasons.append("High consensus between Validation Engine and Risk Engine.")

        # 4. Data Quality Signal
        if data_quality_score >= 85.0:
            score += 0.05
            reasons.append(f"High source data quality ({data_quality_score:.1f}%).")
        elif data_quality_score < 70.0:
            score -= 0.15
            reasons.append(f"Low source data quality ({data_quality_score:.1f}%).")

        # 5. Contradiction Penalty
        if has_contradictions:
            score -= 0.20
            reasons.append("Penalty applied due to conflicting engine analysis signals.")

        # 6. Step Failure Penalty
        if failed_step_count > 0:
            penalty = min(0.20, failed_step_count * 0.05)
            score -= penalty
            reasons.append(f"Penalty applied due to {failed_step_count} step execution failure(s).")

        # Clamp score between 0.0 and 1.0
        final_score = max(0.0, min(1.0, round(score, 2)))

        # Map to level
        if final_score >= 0.90:
            level = ConfidenceLevelEnum.VERY_HIGH
        elif final_score >= 0.75:
            level = ConfidenceLevelEnum.HIGH
        elif final_score >= 0.50:
            level = ConfidenceLevelEnum.MEDIUM
        elif final_score >= 0.30:
            level = ConfidenceLevelEnum.LOW
        else:
            level = ConfidenceLevelEnum.INSUFFICIENT

        return final_score, level, reasons
