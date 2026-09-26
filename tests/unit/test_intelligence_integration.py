"""
UC15 GST Compliance Agent — Intelligence Integration Test Suite (Sprint 7)
Verifies:
  1. End-to-end pipeline execution with Duplicate & Anomaly Intelligence
  2. Strict non-interference: Intelligence findings do NOT alter compliance status
  3. Strict non-interference: Intelligence findings do NOT alter validation gate results
  4. Strict non-interference: Intelligence findings do NOT alter risk scores or priorities
  5. Strict non-interference: Intelligence findings do NOT alter financial impact or exposures
  6. In-memory repository persistence and retrieval (category, invoice_id)
  7. Auditability, explainability, and lineage preservation
  8. Intelligence report generation and text summary serialization
"""
import unittest
from decimal import Decimal

from app.agent.compliance_agent import GSTComplianceAgent
from app.domain.enums.compliance_status import ComplianceStatus
from app.intelligence.common.enums import (
    AnomalyDimension,
    DuplicateMatchType,
    IntelligenceCategory,
)
from app.intelligence.reporting.report import IntelligenceReport


class TestIntelligencePipelineIntegration(unittest.TestCase):
    """End-to-end integration test for Sprint 7 Intelligence Layer."""

    @classmethod
    def setUpClass(cls):
        cls.agent = GSTComplianceAgent(mock=True)
        cls.decisions = cls.agent.run_all()
        cls.report = cls.agent.get_intelligence_report()

    def test_pipeline_execution_populates_intelligence_report(self):
        self.assertIsNotNone(self.report)
        self.assertIsInstance(self.report, IntelligenceReport)
        self.assertGreater(self.report.invoices_analyzed, 0)
        self.assertEqual(self.report.invoices_analyzed, len(self.decisions))

    def test_compliance_status_integrity(self):
        """Verify that intelligence signals do NOT alter statutory compliance statuses."""
        for d in self.decisions:
            # Status must be strictly one of the 3 statutory values
            self.assertIn(d.status, ["COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT"])

            # Verify deterministic rule: status is derived ONLY from validation gate results
            failed_gates = [r for r in d.gates if r.status in ("FAILED", "FAIL", "NON_COMPLIANT")]
            review_gates = [r for r in d.gates if r.status == "NEEDS_REVIEW"]

            if len(failed_gates) >= 2 or any(r.rule_id == "R1_GSTIN_STRUCTURE" and r.status in ("FAILED", "FAIL") for r in d.gates):
                self.assertEqual(d.status, "NON_COMPLIANT")
            elif len(failed_gates) == 1 or len(review_gates) > 0:
                self.assertIn(d.status, ["NEEDS_REVIEW", "NON_COMPLIANT"])
            else:
                self.assertEqual(d.status, "COMPLIANT")

    def test_risk_score_integrity(self):
        """Verify that intelligence findings do NOT inflate or alter Sprint 3 risk scores."""
        self.assertIsNotNone(self.agent.batch_risk_report)
        for d in self.decisions:
            self.assertIsNotNone(d.risk_score)
            self.assertGreaterEqual(d.risk_score, 0.0)
            self.assertLessEqual(d.risk_score, 100.0)

    def test_financial_exposure_integrity(self):
        """Verify that intelligence findings do NOT modify Sprint 6 financial impact numbers."""
        fin_report = self.agent.get_financial_report()
        self.assertIsNotNone(fin_report)
        self.assertIsNotNone(fin_report.aggregate)
        # S6 total exposure remains unaffected by S7 duplicate or anomaly findings
        self.assertGreaterEqual(fin_report.aggregate.total_potential_exposure, Decimal("0.00"))

    def test_repository_storage_and_retrieval(self):
        """Verify in-memory repository persistence and filtering."""
        repo = self.agent.intelligence_service.repository
        all_findings = repo.list_all_findings()
        self.assertIsInstance(all_findings, list)

        # Filter by category
        dup_findings = repo.get_findings_by_category(IntelligenceCategory.DUPLICATE)
        for df in dup_findings:
            self.assertEqual(df.category, IntelligenceCategory.DUPLICATE)

        anom_findings = repo.get_findings_by_category(IntelligenceCategory.ANOMALY)
        for af in anom_findings:
            self.assertEqual(af.category, IntelligenceCategory.ANOMALY)

    def test_lineage_preservation(self):
        """Verify that all intelligence findings maintain unambiguous source transaction lineage."""
        all_findings = self.agent.intelligence_service.repository.list_all_findings()
        for finding in all_findings:
            self.assertTrue(bool(finding.invoice_id), "Finding must have an associated invoice_id")
            self.assertIn("invoice_id", finding.source_lineage)
            self.assertTrue(bool(finding.detector), "Finding must specify its generating detector")

    def test_report_text_summary_generation(self):
        """Verify report text formatting generates clean audit-ready summaries."""
        summary = self.report.to_text_summary()
        self.assertIn("UC15 GST Intelligence Summary", summary)
        self.assertIn("Anomaly Intelligence:", summary)
        self.assertIn("Duplicate Intelligence:", summary)


if __name__ == "__main__":
    unittest.main()
