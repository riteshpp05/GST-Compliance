"""
app.operations.models
=====================
Pydantic domain models for UC15 Enterprise Operations Center, Observability,
Performance Benchmarks, Review Queue, and Operational Alerts (Sprint 19).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AlertSeverityEnum(str, Enum):
    """Severity classification for operational alerts."""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertCategoryEnum(str, Enum):
    """Category classification for operational alerts."""
    HIGH_RISK_CASE = "HIGH_RISK_CASE"
    HIGH_FINANCIAL_EXPOSURE = "HIGH_FINANCIAL_EXPOSURE"
    FAILED_INGESTION = "FAILED_INGESTION"
    POOR_DATA_QUALITY = "POOR_DATA_QUALITY"
    INVESTIGATION_FAILURE = "INVESTIGATION_FAILURE"
    INVESTIGATION_TIMEOUT = "INVESTIGATION_TIMEOUT"
    EVALUATION_REGRESSION = "EVALUATION_REGRESSION"
    SYSTEM_HEALTH_DEGRADATION = "SYSTEM_HEALTH_DEGRADATION"


class OperationalAlert(BaseModel):
    """Structured actionable operational alert."""
    alert_id: str = Field(..., description="Unique alert ID.")
    title: str = Field(..., description="Alert title.")
    description: str = Field(..., description="Detailed explanation.")
    category: AlertCategoryEnum = Field(..., description="Alert category.")
    severity: AlertSeverityEnum = Field(..., description="Alert severity level.")
    tenant_id: str = Field("tenant_default", description="Associated tenant ID.")
    resource_id: Optional[str] = Field(None, description="Associated case, ingestion, or run ID.")
    action_required: str = Field("", description="Recommended operational response.")
    acknowledged: bool = Field(False, description="Whether alert was acknowledged.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp.",
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class CaseMetricsSummary(BaseModel):
    """Summary metrics for enterprise compliance cases."""
    total_cases: int = Field(0, description="Total case count.")
    active_cases: int = Field(0, description="Active (non-closed) case count.")
    created_count: int = Field(0, description="Cases in CREATED status.")
    investigating_count: int = Field(0, description="Cases in INVESTIGATING status.")
    evidence_collected_count: int = Field(0, description="Cases in EVIDENCE_COLLECTED status.")
    findings_ready_count: int = Field(0, description="Cases in FINDINGS_READY status.")
    resolution_proposed_count: int = Field(0, description="Cases in RESOLUTION_PROPOSED status.")
    pending_review_count: int = Field(0, description="Cases in PENDING_REVIEW status.")
    approved_count: int = Field(0, description="Approved cases count.")
    rejected_count: int = Field(0, description="Rejected cases count.")
    resolved_count: int = Field(0, description="Resolved cases count.")
    closed_count: int = Field(0, description="Closed cases count.")
    overdue_count: int = Field(0, description="Overdue cases count (>7 days).")
    aging_distribution: Dict[str, int] = Field(
        default_factory=lambda: {"<24h": 0, "1-3d": 0, "4-7d": 0, ">7d": 0},
        description="Case age distribution.",
    )


class RiskMetricsSummary(BaseModel):
    """Summary metrics for risk distribution."""
    critical_count: int = Field(0, description="Critical risk cases count.")
    high_count: int = Field(0, description="High risk cases count.")
    medium_count: int = Field(0, description="Medium risk cases count.")
    low_count: int = Field(0, description="Low risk cases count.")
    average_risk_score: float = Field(0.0, description="Average risk score (0-100).")
    top_risk_categories: Dict[str, int] = Field(default_factory=dict, description="Risk count by category.")
    risk_by_period: Dict[str, int] = Field(default_factory=dict, description="Risk count by month/period.")


class FinancialExposureSummary(BaseModel):
    """Summary metrics for quantified financial exposure."""
    total_exposure_inr: float = Field(0.0, description="Total quantified exposure in INR.")
    high_exposure_case_count: int = Field(0, description="Count of cases with exposure > INR 50,000.")
    exposure_by_severity: Dict[str, float] = Field(default_factory=dict, description="Exposure sum by case severity.")
    exposure_by_period: Dict[str, float] = Field(default_factory=dict, description="Exposure sum by period.")


class DataQualityMetricsSummary(BaseModel):
    """Summary metrics for Sprint 17 data connectivity and quality."""
    total_ingestion_jobs: int = Field(0, description="Total ingestion jobs.")
    total_records_ingested: int = Field(0, description="Total records ingested.")
    accepted_records_count: int = Field(0, description="Accepted records count.")
    rejected_records_count: int = Field(0, description="Rejected records count.")
    exact_duplicate_count: int = Field(0, description="Exact duplicate count.")
    potential_duplicate_count: int = Field(0, description="Potential duplicate count.")
    average_quality_score: float = Field(100.0, description="Average dataset quality score.")
    failed_ingestions_count: int = Field(0, description="Failed ingestion job count.")


class InvestigationMetricsSummary(BaseModel):
    """Summary metrics for Sprint 18 bounded investigation execution."""
    investigations_started: int = Field(0, description="Total investigations started.")
    investigations_completed: int = Field(0, description="Completed investigations count.")
    investigations_failed: int = Field(0, description="Failed investigations count.")
    average_duration_seconds: float = Field(0.0, description="Average investigation duration.")
    average_tool_calls_per_investigation: float = Field(0.0, description="Average tool calls per run.")
    average_steps_per_investigation: float = Field(0.0, description="Average step count per run.")
    total_findings_generated: int = Field(0, description="Total findings generated.")
    total_evidence_collected: int = Field(0, description="Total evidence items collected.")
    contradiction_frequency: float = Field(0.0, description="Percentage of runs with contradictions.")


class AIQualityMetricsSummary(BaseModel):
    """Summary metrics for Sprint 18 AI evaluation runs."""
    latest_run_id: Optional[str] = Field(None, description="Latest evaluation run ID.")
    overall_accuracy: float = Field(100.0, description="Latest overall accuracy score.")
    finding_relevance: float = Field(100.0, description="Latest finding relevance score.")
    evidence_grounding: float = Field(100.0, description="Latest evidence grounding score.")
    confidence_calibration: float = Field(100.0, description="Latest confidence calibration score.")
    recommendation_quality: float = Field(100.0, description="Latest recommendation quality score.")
    tool_selection_efficiency: float = Field(100.0, description="Latest tool selection efficiency score.")
    security_compliance: float = Field(100.0, description="Latest security compliance score.")
    root_cause_accuracy: float = Field(100.0, description="Latest root cause accuracy score.")
    conflict_detection_accuracy: float = Field(100.0, description="Latest conflict detection score.")
    passed_golden_cases: int = Field(10, description="Golden test cases passed in latest run.")
    total_golden_cases: int = Field(10, description="Total golden test cases.")
    has_regression: bool = Field(False, description="Flag indicating detected evaluation regression.")


class ReviewQueueItem(BaseModel):
    """Item DTO in the operational Human Review Queue."""
    case_id: str = Field(..., description="Case ID.")
    title: str = Field(..., description="Case title.")
    status: str = Field(..., description="Status.")
    priority: str = Field("P3", description="Case priority.")
    risk_level: str = Field("LOW", description="Risk level.")
    financial_exposure: float = Field(0.0, description="Financial exposure (INR).")
    confidence_score: float = Field(1.0, description="Investigation confidence.")
    confidence_level: str = Field("HIGH", description="Confidence level.")
    has_contradictions: bool = Field(False, description="Contradictions flag.")
    finding_count: int = Field(0, description="Consolidated findings count.")
    evidence_count: int = Field(0, description="Collected evidence count.")
    age_hours: float = Field(0.0, description="Case age in hours.")
    assigned_reviewer: str = Field("UNASSIGNED", description="Assigned reviewer.")
    recommendation: str = Field("", description="AI resolution recommendation.")


class OperationsDashboardOverview(BaseModel):
    """Unified Operations Center Dashboard Overview DTO."""
    tenant_id: str = Field("tenant_default", description="Tenant scope.")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )
    cases: CaseMetricsSummary = Field(default_factory=CaseMetricsSummary)
    risk: RiskMetricsSummary = Field(default_factory=RiskMetricsSummary)
    financial: FinancialExposureSummary = Field(default_factory=FinancialExposureSummary)
    data_quality: DataQualityMetricsSummary = Field(default_factory=DataQualityMetricsSummary)
    investigation: InvestigationMetricsSummary = Field(default_factory=InvestigationMetricsSummary)
    ai_quality: AIQualityMetricsSummary = Field(default_factory=AIQualityMetricsSummary)
    active_alerts: List[OperationalAlert] = Field(default_factory=list)
    review_queue_count: int = Field(0, description="Number of items pending human review.")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
