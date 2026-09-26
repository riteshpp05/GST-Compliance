"""
app.intelligence.services.intelligence_service
==============================================
Central orchestration service for Duplicate & Anomaly Intelligence (Sprint 7).
Provides high-level interfaces for batch analysis, pairwise comparisons, persistence, and reporting.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.intelligence.anomaly.engine import AnomalyIntelligenceEngine
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.common.enums import IntelligenceCategory
from app.intelligence.common.models import IntelligenceFinding
from app.intelligence.config.intelligence_config import (
    IntelligenceConfig,
    default_intelligence_config,
)
from app.intelligence.duplicate.engine import DuplicateIntelligenceEngine
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.intelligence.reporting.report import IntelligenceReport
from app.intelligence.repositories.base import BaseIntelligenceRepository
from app.intelligence.repositories.in_memory import InMemoryIntelligenceRepository


class IntelligenceService:
    """
    Primary interface for Duplicate & Anomaly Intelligence (Sprint 7).
    Orchestrates duplicate matching, clustering, statistical anomaly evaluation,
    and unified reporting.
    """

    def __init__(
        self,
        repository: Optional[BaseIntelligenceRepository] = None,
        config: Optional[IntelligenceConfig] = None,
        duplicate_engine: Optional[DuplicateIntelligenceEngine] = None,
        anomaly_engine: Optional[AnomalyIntelligenceEngine] = None,
    ) -> None:
        self.repository = repository or InMemoryIntelligenceRepository()
        self.config = config or default_intelligence_config
        self.duplicate_engine = duplicate_engine or DuplicateIntelligenceEngine(config=self.config.duplicate)
        self.anomaly_engine = anomaly_engine or AnomalyIntelligenceEngine(config=self.config.anomaly)

    def evaluate_batch(
        self,
        invoices: List[Invoice],
        decisions: Optional[List[ComplianceDecision]] = None,
        historical_invoices: Optional[List[Invoice]] = None,
    ) -> IntelligenceReport:
        """
        Execute full duplicate and anomaly intelligence evaluation over a batch of invoices.
        Persists all findings and returns a consolidated IntelligenceReport.
        """
        if not invoices:
            return IntelligenceReport(invoices_analyzed=0)

        # 1. Duplicate Intelligence Evaluation
        clusters, candidates, dup_findings = self.duplicate_engine.analyze(invoices)

        # 2. Anomaly Intelligence Evaluation
        anom_findings, anom_int_findings = self.anomaly_engine.analyze(
            invoices=invoices,
            historical_invoices=historical_invoices,
        )

        # 3. Persist to repository
        self.repository.add_duplicate_candidates(candidates)
        self.repository.add_duplicate_clusters(clusters)
        self.repository.add_anomaly_findings(anom_findings)

        all_findings = dup_findings + anom_int_findings
        self.repository.add_findings(all_findings)

        # 4. Generate report
        report = IntelligenceReport(
            invoices_analyzed=len(invoices),
            duplicate_clusters=clusters,
            duplicate_candidates=candidates,
            anomaly_findings=anom_findings,
            all_findings=all_findings,
        )

        return report

    def compare_invoices(self, inv1: Invoice, inv2: Invoice) -> DuplicateCandidate:
        """Evaluate two invoices directly for duplicate candidate relationship."""
        cand = self.duplicate_engine.compare_invoices(inv1, inv2)
        if cand.match_type != cand.match_type.NO_DUPLICATE:
            self.repository.add_duplicate_candidates([cand])
        return cand

    def get_report(self) -> IntelligenceReport:
        """Compile an IntelligenceReport from all records stored in the repository."""
        findings = self.repository.list_all_findings()
        candidates = self.repository.list_duplicate_candidates()
        clusters = self.repository.list_duplicate_clusters()
        anomalies = self.repository.list_anomaly_findings()

        # Count unique invoices represented
        seen_invoices = set()
        for f in findings:
            if f.invoice_id:
                seen_invoices.add(f.invoice_id)
        for c in candidates:
            if c.source_invoice_id:
                seen_invoices.add(c.source_invoice_id)
            if c.matched_invoice_id:
                seen_invoices.add(c.matched_invoice_id)
        for a in anomalies:
            if a.invoice_id:
                seen_invoices.add(a.invoice_id)

        return IntelligenceReport(
            invoices_analyzed=len(seen_invoices),
            duplicate_clusters=clusters,
            duplicate_candidates=candidates,
            anomaly_findings=anomalies,
            all_findings=findings,
        )

    def get_findings_by_invoice(self, invoice_id: str) -> List[IntelligenceFinding]:
        """Retrieve all intelligence findings associated with an invoice ID."""
        return self.repository.get_findings_by_invoice(invoice_id)

    def get_duplicates(self) -> List[DuplicateCandidate]:
        """Retrieve all detected duplicate candidate pairs."""
        return self.repository.list_duplicate_candidates()

    def get_duplicate_clusters(self) -> List[DuplicateCluster]:
        """Retrieve all consolidated duplicate clusters."""
        return self.repository.list_duplicate_clusters()

    def get_anomalies(self, invoice_id: Optional[str] = None) -> List[AnomalyFinding]:
        """Retrieve dimensional anomaly evaluation records."""
        all_anoms = self.repository.list_anomaly_findings()
        if invoice_id:
            return [a for a in all_anoms if a.invoice_id == invoice_id]
        return all_anoms

    def clear(self) -> None:
        """Clear all stored intelligence records."""
        self.repository.clear()
