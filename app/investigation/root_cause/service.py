"""
app.investigation.root_cause.service
====================================
Service layer for Root Cause Intelligence.
Provides standalone and batch root-cause investigation APIs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.financial.models.impact import FinancialImpact
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.evidence.collector import EvidenceCollector
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import RootCauseFinding
from app.investigation.root_cause.engine import RootCauseEngine


class RootCauseService:
    """
    High-level service interface for Root Cause Intelligence analysis.
    """

    def __init__(
        self,
        config: Optional[InvestigationConfig] = None,
        engine: Optional[RootCauseEngine] = None,
        collector: Optional[EvidenceCollector] = None,
    ) -> None:
        self.config = config or default_investigation_config
        self.engine = engine or RootCauseEngine(config=self.config)
        self.collector = collector or EvidenceCollector()

    def evaluate_root_causes(
        self,
        invoices: List[Invoice],
        decisions: Optional[List[ComplianceDecision]] = None,
        financial_impacts: Optional[List[FinancialImpact]] = None,
        duplicate_candidates: Optional[List[DuplicateCandidate]] = None,
        duplicate_clusters: Optional[List[DuplicateCluster]] = None,
        anomaly_findings: Optional[List[AnomalyFinding]] = None,
        historical_patterns: Optional[List[Any]] = None,
        historical_trends: Optional[List[Any]] = None,
        risk_assessments: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[RootCauseFinding], List[RootCauseFinding], EvidenceContext]:
        """
        Collect evidence, run root cause engine, and return results with indexed context.
        """
        ctx = self.collector.collect_context(
            invoices=invoices,
            decisions=decisions,
            financial_impacts=financial_impacts,
            duplicate_candidates=duplicate_candidates,
            duplicate_clusters=duplicate_clusters,
            anomaly_findings=anomaly_findings,
            historical_patterns=historical_patterns,
            historical_trends=historical_trends,
            risk_assessments=risk_assessments,
        )

        primary, ranked = self.engine.analyze(ctx)
        return primary, ranked, ctx
