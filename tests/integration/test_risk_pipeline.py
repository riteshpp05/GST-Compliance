"""
Integration tests for Risk Engine end-to-end pipeline execution across Excel, CSV, and Mock sources.
"""
import json
import os
import unittest
import pandas as pd

from app.agent.compliance_agent import GSTComplianceAgent
from app.config.settings import settings
from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.risk_priority import RiskPriority


class TestRiskPipelineIntegration(unittest.TestCase):

    def test_mock_pipeline_with_risk(self):
        agent = GSTComplianceAgent(mock=True)
        decisions = agent.run_all()

        self.assertGreater(len(decisions), 0)
        self.assertIsNotNone(agent.batch_risk_report)
        report = agent.batch_risk_report

        self.assertEqual(report.distribution.total_invoices, len(decisions))
        total_by_level = sum(report.distribution.by_level.values())
        self.assertEqual(total_by_level, len(decisions))

        # Check every decision has risk fields attached
        for d in decisions:
            self.assertIsNotNone(d.risk_score)
            self.assertGreaterEqual(d.risk_score, 0.0)
            self.assertLessEqual(d.risk_score, 100.0)
            self.assertIn(d.risk_level, [lvl.value for lvl in RiskLevel])
            self.assertIn(d.priority, [p.value for p in RiskPriority])
            self.assertIsNotNone(d.risk_assessment)

        # Check deterministic ordering in top risky invoices
        top_risky = report.top_risky_invoices
        for i in range(len(top_risky) - 1):
            self.assertGreaterEqual(top_risky[i].risk_score, top_risky[i + 1].risk_score)

    def test_csv_pipeline_with_risk(self):
        csv_path = "data/raw/sample_invoices.csv"
        if not os.path.exists(csv_path):
            self.skipTest(f"Sample CSV {csv_path} not found")

        agent = GSTComplianceAgent(source_file=csv_path)
        decisions = agent.run_all()
        self.assertEqual(len(decisions), 6)
        self.assertIsNotNone(agent.batch_risk_report)

        # Clean invoice in sample_invoices.csv (INV-CSV-001) should be LOW risk (0.0)
        clean_inv = next((d for d in decisions if d.invoice_no == "INV-CSV-001"), None)
        self.assertIsNotNone(clean_inv)
        self.assertEqual(clean_inv.risk_score, 0.0)
        self.assertEqual(clean_inv.risk_level, RiskLevel.LOW.value)

    def test_excel_pipeline_with_risk_and_persistence(self):
        if not os.path.exists(settings.excel_file):
            self.skipTest("Default Excel dataset not found")

        agent = GSTComplianceAgent(excel_path=settings.excel_file)
        decisions = agent.run_all()
        self.assertGreaterEqual(len(decisions), 30)
        self.assertIsNotNone(agent.batch_risk_report)

        # Find latest results written
        results_dir = settings.results_dir
        json_files = [
            os.path.join(results_dir, f)
            for f in os.listdir(results_dir)
            if f.startswith("uc15_gst_run_") and f.endswith(".json")
        ]
        self.assertTrue(len(json_files) > 0)
        latest_json = sorted(json_files)[-1]

        with open(latest_json, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("results", data)
        self.assertGreaterEqual(len(data["results"]), 30)
        first_item = data["results"][0]
        self.assertIn("risk_score", first_item)
        self.assertIn("risk_level", first_item)
        self.assertIn("priority", first_item)
        self.assertIn("risk_assessment", first_item)

        # Check Excel workbook columns
        xlsx_files = [
            os.path.join(results_dir, f)
            for f in os.listdir(results_dir)
            if f.startswith("uc15_gst_run_") and f.endswith(".xlsx")
        ]
        self.assertTrue(len(xlsx_files) > 0)
        latest_xlsx = sorted(xlsx_files)[-1]

        excel_df = pd.read_excel(latest_xlsx, sheet_name="Detailed Results")
        self.assertIn("Risk Score", excel_df.columns)
        self.assertIn("Risk Level", excel_df.columns)
        self.assertIn("Priority", excel_df.columns)


if __name__ == "__main__":
    unittest.main()
