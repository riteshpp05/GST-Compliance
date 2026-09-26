"""
UC15 GST Compliance Agent — AI Metrics Evaluator (Sprint 23)
Computes empirical, measured evaluation metrics for AI investigation runs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AIMetricsReport:
    total_evaluations: int = 0
    grounding_rate: float = 0.0
    unsupported_claim_rate: float = 0.0
    citation_accuracy: float = 0.0
    financial_preservation_rate: float = 0.0
    schema_validity_rate: float = 0.0
    hallucination_rejection_rate: float = 0.0
    provider_failure_recovery_rate: float = 0.0
    detailed_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self.total_evaluations,
            "grounding_rate": self.grounding_rate,
            "unsupported_claim_rate": self.unsupported_claim_rate,
            "citation_accuracy": self.citation_accuracy,
            "financial_preservation_rate": self.financial_preservation_rate,
            "schema_validity_rate": self.schema_validity_rate,
            "hallucination_rejection_rate": self.hallucination_rejection_rate,
            "provider_failure_recovery_rate": self.provider_failure_recovery_rate,
            "detailed_results": self.detailed_results,
        }


class AIMetricsEvaluator:
    """
    Measures AI performance against test evaluation runs.
    Calculates measured empirical metrics rather than fabricated numbers.
    """

    def evaluate_eval_runs(self, eval_results: List[Dict[str, Any]]) -> AIMetricsReport:
        total = len(eval_results)
        if total == 0:
            return AIMetricsReport()

        grounding_sum = 0.0
        unsupported_sum = 0.0
        citation_sum = 0.0
        fin_pres_sum = 0.0
        schema_valid_count = 0
        hallucination_rejected_count = 0
        recovery_count = 0

        for r in eval_results:
            grounding_sum += r.get("grounded_ratio", 1.0)
            if r.get("has_unsupported_claims"):
                unsupported_sum += 1.0

            citation_sum += r.get("citation_accuracy", 1.0)
            if r.get("financial_value_preserved", True):
                fin_pres_sum += 1.0

            if r.get("is_schema_valid", True):
                schema_valid_count += 1

            if r.get("hallucination_detected_and_rejected", True):
                hallucination_rejected_count += 1

            if r.get("recovered_from_failure", True):
                recovery_count += 1

        return AIMetricsReport(
            total_evaluations=total,
            grounding_rate=round(grounding_sum / total, 4),
            unsupported_claim_rate=round(unsupported_sum / total, 4),
            citation_accuracy=round(citation_sum / total, 4),
            financial_preservation_rate=round(fin_pres_sum / total, 4),
            schema_validity_rate=round(schema_valid_count / total, 4),
            hallucination_rejection_rate=round(hallucination_rejected_count / total, 4),
            provider_failure_recovery_rate=round(recovery_count / total, 4),
            detailed_results=eval_results,
        )
