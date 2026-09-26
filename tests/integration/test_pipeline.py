"""
Integration tests for UC15 GST Compliance Agent end-to-end pipeline (v2.0).
Verifies the complete flow across multiple sources:
Excel, CSV, JSON, and Mock data -> Ingestion -> Normalization -> Rules -> Decision -> Results Writer.
"""
import os
import unittest

from app.agent.compliance_agent import GSTComplianceAgent
from app.config.settings import settings
from app.data.loaders.csv_loader import CSVInvoiceLoader
from app.data.loaders.json_loader import JSONInvoiceLoader
from app.data.loaders.mock_loader import MockInvoiceLoader


class TestEndToEndPipeline(unittest.TestCase):

    def setUp(self):
        self.excel_file = settings.excel_file
        self.csv_file = os.path.join("data", "raw", "sample_invoices.csv")
        self.json_file = os.path.join("data", "raw", "sample_invoices.json")

    def test_full_pipeline_run_excel(self):
        if not os.path.exists(self.excel_file):
            self.skipTest(f"Excel dataset not found at {self.excel_file}")

        agent = GSTComplianceAgent(excel_path=self.excel_file)
        decisions = agent.run_all()

        self.assertGreaterEqual(len(decisions), 30)

        # Verify the dataset distribution under hardened statutory policies:
        compliant_count = sum(1 for d in decisions if d.status == "COMPLIANT")
        review_count = sum(1 for d in decisions if d.status == "NEEDS_REVIEW")
        non_compliant_count = sum(1 for d in decisions if d.status in ("NON_COMPLIANT", "BLOCKED"))

        self.assertGreater(compliant_count, 0)
        self.assertGreater(review_count, 0)

        # Check all invoices have audit ref and exactly 6 gates
        for d in decisions:
            self.assertTrue(d.audit_trail_ref.startswith("GST-"))
            self.assertEqual(len(d.gates), 6)
            self.assertTrue(d.invoice_no.startswith("INV"))

    def test_full_pipeline_run_csv(self):
        if not os.path.exists(self.csv_file):
            self.skipTest(f"CSV dataset not found at {self.csv_file}")

        agent = GSTComplianceAgent(source_file=self.csv_file)
        decisions = agent.run_all()

        self.assertGreater(len(decisions), 0)
        for d in decisions:
            self.assertTrue(d.audit_trail_ref.startswith("GST-"))
            self.assertEqual(len(d.gates), 6)

    def test_full_pipeline_run_json(self):
        if not os.path.exists(self.json_file):
            self.skipTest(f"JSON dataset not found at {self.json_file}")

        agent = GSTComplianceAgent(source_file=self.json_file)
        decisions = agent.run_all()

        self.assertEqual(len(decisions), 3)
        for d in decisions:
            self.assertTrue(d.audit_trail_ref.startswith("GST-"))
            self.assertEqual(len(d.gates), 6)

    def test_full_pipeline_run_mock(self):
        agent = GSTComplianceAgent(mock=True)
        decisions = agent.run_all()

        self.assertGreaterEqual(len(decisions), 10)
        # Verify both compliant and non-compliant outcomes exist in mock suite
        statuses = {d.status for d in decisions}
        self.assertIn("COMPLIANT", statuses)
        self.assertIn("NON_COMPLIANT", statuses)

    def test_single_invoice_lookup_and_validation(self):
        if not os.path.exists(self.excel_file):
            self.skipTest(f"Excel dataset not found at {self.excel_file}")

        agent = GSTComplianceAgent(excel_path=self.excel_file)
        decisions = agent.run_all()
        target_id = decisions[0].invoice_no if decisions else "INV-2026-CLEAN-AP-01"
        decision = agent.run_invoice(target_id)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.invoice_no, target_id)
        self.assertEqual(len(decision.gates), 6)

    def test_nonexistent_invoice_returns_none(self):
        if not os.path.exists(self.excel_file):
            self.skipTest(f"Excel dataset not found at {self.excel_file}")

        agent = GSTComplianceAgent(excel_path=self.excel_file)
        decision = agent.run_invoice("INV-DOES-NOT-EXIST")
        self.assertIsNone(decision)


if __name__ == "__main__":
    unittest.main()
