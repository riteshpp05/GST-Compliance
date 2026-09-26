"""
app.evaluation.models
=====================
Domain Models, Metric Definitions, and Evaluation Results for UC15 AI Evaluation Framework (Sprint 18).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvaluationMetricEnum(str, Enum):
    """Supported evaluation metrics with associated weighting."""
    INVESTIGATION_CORRECTNESS = "INVESTIGATION_CORRECTNESS"  # Weight: 20%
    EVIDENCE_GROUNDING = "EVIDENCE_GROUNDING"                # Weight: 20%
    INVESTIGATION_COMPLETENESS = "INVESTIGATION_COMPLETENESS"# Weight: 15%
    TOOL_SELECTION = "TOOL_SELECTION"                        # Weight: 10%
    TOOL_EFFICIENCY = "TOOL_EFFICIENCY"                      # Weight: 10%
    FINDING_QUALITY = "FINDING_QUALITY"                      # Weight: 10%
    RECOMMENDATION_QUALITY = "RECOMMENDATION_QUALITY"        # Weight: 5%
    SECURITY_COMPLIANCE = "SECURITY_COMPLIANCE"              # Weight: 5%
    UNSUPPORTED_CLAIM_RATE = "UNSUPPORTED_CLAIM_RATE"        # Weight: 5%


METRIC_WEIGHTS: Dict[EvaluationMetricEnum, float] = {
    EvaluationMetricEnum.INVESTIGATION_CORRECTNESS: 0.20,
    EvaluationMetricEnum.EVIDENCE_GROUNDING: 0.20,
    EvaluationMetricEnum.INVESTIGATION_COMPLETENESS: 0.15,
    EvaluationMetricEnum.TOOL_SELECTION: 0.10,
    EvaluationMetricEnum.TOOL_EFFICIENCY: 0.10,
    EvaluationMetricEnum.FINDING_QUALITY: 0.10,
    EvaluationMetricEnum.RECOMMENDATION_QUALITY: 0.05,
    EvaluationMetricEnum.SECURITY_COMPLIANCE: 0.05,
    EvaluationMetricEnum.UNSUPPORTED_CLAIM_RATE: 0.05,
}


class GoldenTestCase(BaseModel):
    """Deterministic golden test case specification."""
    golden_id: str = Field(..., description="Unique golden case identifier.")
    name: str = Field(..., description="Golden case title.")
    description: str = Field(..., description="Case scenario description.")
    input_invoice: Dict[str, Any] = Field(..., description="Raw invoice record.")
    expected_status: str = Field(..., description="Expected compliance status (COMPLIANT, NON_COMPLIANT, NEEDS_REVIEW).")
    expected_defect_category: Optional[str] = Field(None, description="Expected defect category if non-compliant.")
    expected_tools: List[str] = Field(default_factory=list, description="Tools expected to be executed.")
    forbidden_tools: List[str] = Field(default_factory=list, description="Forbidden tools (e.g. human resolution tools).")
    min_evidence_count: int = Field(2, ge=1, description="Minimum expected evidence count.")


class MetricScore(BaseModel):
    """Individual metric evaluation score."""
    metric: EvaluationMetricEnum = Field(..., description="Evaluated metric.")
    weight: float = Field(..., description="Metric weight ratio.")
    score: float = Field(..., ge=0.0, le=100.0, description="Score percentage (0.0 to 100.0).")
    rationale: str = Field("", description="Reasoning or evaluation breakdown.")


class EvaluationResult(BaseModel):
    """Result of evaluating a single golden test case."""
    test_case_id: str = Field(..., description="Target golden case ID.")
    test_case_name: str = Field(..., description="Golden case name.")
    passed: bool = Field(True, description="True if test case criteria met.")
    overall_score: float = Field(0.0, ge=0.0, le=100.0, description="Weighted overall score (0.0 - 100.0).")
    metric_scores: List[MetricScore] = Field(default_factory=list, description="Breakdown per metric.")
    detected_issue: Optional[str] = Field(None, description="Primary issue detected during run.")
    tools_called: List[str] = Field(default_factory=list, description="Actual tools called.")
    evidence_count: int = Field(0, ge=0, description="Evidence items collected.")
    unsupported_claim_count: int = Field(0, ge=0, description="Unsupported claims flagged.")
    security_violation_count: int = Field(0, ge=0, description="Security violations detected.")


class EvaluationRun(BaseModel):
    """Complete evaluation run over the golden dataset."""
    run_id: str = Field(
        default_factory=lambda: f"EVAL-{uuid.uuid4().hex[:8].upper()}",
        description="Unique evaluation run ID.",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )
    total_cases: int = Field(0, ge=0)
    passed_cases: int = Field(0, ge=0)
    overall_score: float = Field(0.0, ge=0.0, le=100.0)
    metric_averages: Dict[str, float] = Field(default_factory=dict)
    case_results: List[EvaluationResult] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class RegressionComparison(BaseModel):
    """Comparison between a candidate evaluation run and a baseline run."""
    run_id: str = Field(..., description="Candidate run ID.")
    baseline_run_id: str = Field(..., description="Baseline run ID.")
    baseline_score: float = Field(..., ge=0.0, le=100.0)
    candidate_score: float = Field(..., ge=0.0, le=100.0)
    score_difference: float = Field(...)
    status: str = Field("UNCHANGED", description="Status: IMPROVED, REGRESSION, UNCHANGED.")
    details: List[str] = Field(default_factory=list)
