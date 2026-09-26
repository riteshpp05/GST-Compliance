"""
UC15 GST Compliance Agent — Risk Domain Models & Contracts
Contracts for Risk Assessment, Risk Factors, Category Risk, and Batch Risk Reporting.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.domain.enums.confidence_level import ConfidenceLevel
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.risk_priority import RiskPriority


@dataclass
class RiskFactor:
    """
    Individual quantifiable contributor to an invoice's risk score.
    Provides complete auditability and explainability for why a score was assigned.
    """
    factor_id: str
    name: str
    description: str
    contribution: float
    category: str
    severity: Optional[str] = None
    rule_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryRisk:
    """
    Aggregated compliance risk for a specific statutory or operational category.
    """
    category: str
    score: float
    finding_count: int
    max_severity: str
    findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskAssessment:
    """
    Comprehensive risk evaluation for an invoice.
    Maintains clean separation between statutory compliance status, risk score,
    severity, data quality, and financial exposure.
    """
    invoice_id: str
    risk_score: float                                      # 0.0 – 100.0
    risk_level: str                                        # LOW | MODERATE | MEDIUM | HIGH | CRITICAL
    priority: str                                          # P1 | P2 | P3 | P4
    confidence: str                                        # HIGH | MEDIUM | LOW
    confidence_score: float                                # 0.0 – 1.0
    explanation: str

    risk_factors: List[RiskFactor] = field(default_factory=list)
    contributing_findings: List[str] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    severity_contribution: float = 0.0
    data_quality_impact: float = 0.0

    # Extension points for future sprints (Sprint 6-9)
    financial_exposure: Optional[Decimal] = None           # Sprint 6 Financial Impact
    anomaly_score: Optional[float] = None                  # Sprint 7 Anomaly Detection
    historical_risk: Optional[Dict[str, Any]] = None       # Sprint 8 Historical Intelligence
    root_cause_ref: Optional[str] = None                   # Sprint 9 Root Cause / Blast Radius

    # Metadata & Versioning
    risk_model_version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if isinstance(self.risk_level, RiskLevel):
            self.risk_level = self.risk_level.value
        if isinstance(self.priority, RiskPriority):
            self.priority = self.priority.value
        if isinstance(self.confidence, ConfidenceLevel):
            self.confidence = self.confidence.value

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RiskDistribution:
    """Aggregated risk distribution across an entire batch of invoices."""
    total_invoices: int
    by_level: Dict[str, int] = field(default_factory=dict)
    by_priority: Dict[str, int] = field(default_factory=dict)
    by_category: Dict[str, int] = field(default_factory=dict)
    average_risk_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BatchRiskReport:
    """Comprehensive batch evaluation report for risk analytics and dashboards."""
    distribution: RiskDistribution
    top_risky_invoices: List[RiskAssessment] = field(default_factory=list)
    assessments: List[RiskAssessment] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    risk_model_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
