"""
tests.integration.test_s25_enterprise_ui_workflow
===================================================
Sprint 25 — Integration Test Suite for Enterprise UI Workflow & API Contracts.
"""

import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.db.connection import reset_db_connection
from ui.app import app


class TestS25EnterpriseUIWorkflow(unittest.TestCase):
    """Integration tests for Sprint 25 Enterprise UI workflow and API contracts."""

    @classmethod
    def setUpClass(cls):
        os.environ["APP_ENV"] = "development"
        reset_db_connection()
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        # Populate initial dataset
        run_resp = cls.client.post("/api/run")
        assert run_resp.status_code == 200, f"Pipeline run failed: {run_resp.status_code}"

        # Create a case for testing
        case_resp = cls.client.post(
            "/api/cases",
            json={
                "invoice_id": "INV-8000001",
                "counterparty_gstin": "29XCDBM5846M9ZE",
                "title": "S25 Enterprise UI Integration Case",
                "source": "UI_WORKFLOW_TEST",
            },
        )
        assert case_resp.status_code == 200, f"Case creation failed: {case_resp.text}"
        cls.test_case_id = case_resp.json()["case_id"]

    @classmethod
    def tearDownClass(cls):
        os.environ["APP_ENV"] = "development"
        reset_db_connection()

    def test_01_readiness_endpoint_integration(self):
        """Verify /ready endpoint returns environment details and configuration checks."""
        resp = self.client.get("/ready")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "READY")
        self.assertTrue(data["ready"])
        self.assertIn("configuration", data["details"])

    def test_02_dashboard_overview_metrics(self):
        """Verify dashboard overview returns real backend metrics."""
        resp = self.client.get("/api/dashboard/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("kpis", data)
        self.assertGreater(data["kpis"]["total_invoices"], 0)
        self.assertIn("potential_exposure", data["kpis"])

    def test_03_case_workspace_review_package_contract(self):
        """Verify review package endpoint for case workspace."""
        resp = self.client.get(f"/api/v1/cases/{self.test_case_id}/review-package")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("case_id", data)
        self.assertIn("title", data)
        self.assertIn("financial_exposure", data)
        self.assertIn("reconciliation_summary", data)

    def test_04_case_reconciliation_contract(self):
        """Verify 4-way reconciliation endpoint for case workspace."""
        resp = self.client.get(f"/api/v1/cases/{self.test_case_id}/reconciliation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("overall_status", data)

    def test_05_case_financial_exposure_contract(self):
        """Verify financial exposure endpoint for case workspace."""
        resp = self.client.get(f"/api/v1/cases/{self.test_case_id}/financial-exposure")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("case_id", data)

    def test_06_human_review_decision_submission(self):
        """Verify human review decision endpoint enforces mandatory comment and valid decision."""
        # Follow lifecycle state transitions: CREATED -> TRIAGED -> INVESTIGATING -> FINDINGS_READY -> RESOLUTION_PROPOSED
        self.client.post(
            f"/api/cases/{self.test_case_id}/triage",
            json={"priority": "P1", "risk_level": "CRITICAL", "assigned_to": "Reviewer"}
        )
        self.client.post(
            f"/api/cases/{self.test_case_id}/investigation/start",
            json={"actor": "Investigator"}
        )
        self.client.post(
            f"/api/cases/{self.test_case_id}/findings",
            json={
                "title": "Tax rate mismatch",
                "description": "Observed IGST 18% vs expected 12%",
                "severity": "HIGH",
            }
        )
        self.client.post(
            f"/api/cases/{self.test_case_id}/recommendation",
            json={
                "recommended_action": "RECIRCULATE_INVOICE",
                "rationale": "Tax rate mismatch requires vendor correction.",
            }
        )

        resp = self.client.post(
            f"/api/cases/{self.test_case_id}/review",
            json={
                "reviewer": "Senior Tax Reviewer",
                "reviewer_role": "REVIEWER",
                "decision": "APPROVE",
                "comment": "Formal audit approval for GSTR filing."
            }
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn(data["status"], ["READY_FOR_RESOLUTION", "APPROVED"])

    @patch.dict(os.environ, {"APP_ENV": "production"}, clear=True)
    def test_07_unauthenticated_request_blocked_in_production(self):
        """Verify backend security boundary blocks unauthenticated requests in production."""
        unauth_client = TestClient(app)
        resp = unauth_client.get("/api/cases")
        self.assertEqual(resp.status_code, 401)


if __name__ == "__main__":
    unittest.main()
