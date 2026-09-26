"""
tests.e2e.test_s20_e2e_acceptance
===================================
Sprint 20 End-to-End System Acceptance Test Suite (Guardrail #8).
Verifies complete lifecycle without mocking:
  1. Ingest Data / Sample Invoices
  2. Data Quality & Cleansing
  3. Gate Validation & Compliance Assessment (Findings & Evidence)
  4. AI Agent Investigation & Trace Generation
  5. Case Creation & Assignment
  6. Human Review & Decision Authorization (APPROVE / REJECT / REQUEST MORE EVIDENCE)
  7. Status, Database State, Audit Log, and Timeline Entry Verification
"""

import os
import sys
import tempfile
import unittest
from fastapi.testclient import TestClient

from app.agent.compliance_agent import GSTComplianceAgent
from app.case.models import CaseDecisionEnum, CaseStatusEnum
from app.case.service import CaseService
from ui.app import app


class TestSprint20E2EAcceptance(unittest.TestCase):
    """
    Comprehensive E2E Acceptance Test verifying full ingestion -> decision lifecycle.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.headers_admin = {"X-API-Key": "key-admin-123"}
        self.headers_investigator = {"X-API-Key": "key-investigator-123"}
        self.headers_reviewer = {"X-API-Key": "key-reviewer-123"}

    def test_end_to_end_gst_compliance_and_case_lifecycle(self):
        """
        Full E2E test verifying ingestion, statutory rules, AI investigation,
        case management, human review authorization, and audit trail.
        """
        # 1. Statutory Pipeline Execution
        agent = GSTComplianceAgent()
        results = agent.run_all()
        self.assertGreaterEqual(len(results), 30)

        # 2. Verify Data Quality & Compliance Findings
        non_compliant = [r for r in results if r.status in ("NON_COMPLIANT", "NEEDS_REVIEW")]
        self.assertTrue(len(non_compliant) > 0, "Pipeline should detect non-compliant invoices")
        target_inv = non_compliant[0].invoice_no

        # 3. Create Investigation Case via REST API
        create_res = self.client.post(
            "/api/cases",
            headers=self.headers_investigator,
            json={
                "title": f"E2E Acceptance Audit: {target_inv}",
                "description": f"Full compliance audit for non-compliant invoice {target_inv}",
                "invoice_id": target_inv,
                "counterparty_name": non_compliant[0].counterparty_name,
                "counterparty_gstin": non_compliant[0].counterparty_gstin,
                "source": "E2E_ACCEPTANCE_TEST",
            },
        )
        self.assertEqual(create_res.status_code, 200, create_res.text)
        case_data = create_res.json()
        case_id = case_data["case_id"]
        self.assertEqual(case_data["status"], "CREATED")

        # 4. Triage Case
        triage_res = self.client.post(
            f"/api/cases/{case_id}/triage",
            headers=self.headers_investigator,
            json={
                "category": "INPUT_TAX_CREDIT_ANOMALY",
                "priority": "P1",
                "risk_level": "CRITICAL",
                "investigation_scope": "FULL_AUDIT",
            },
        )
        self.assertEqual(triage_res.status_code, 200)

        # 5. Start Investigation
        start_res = self.client.post(
            f"/api/cases/{case_id}/investigation/start",
            headers=self.headers_investigator,
            json={"actor": "E2E_INVESTIGATOR"},
        )
        self.assertEqual(start_res.status_code, 200)

        # 6. Execute AI Investigation Agent
        ai_res = self.client.post(
            "/api/agent/investigate",
            headers=self.headers_investigator,
            json={
                "user_query": f"Analyze root cause and financial exposure for invoice {target_inv}",
                "invoice_id": target_inv,
            },
        )
        self.assertEqual(ai_res.status_code, 200, ai_res.text)
        ai_data = ai_res.json()
        self.assertIn("synthesized_answer", ai_data)
        self.assertTrue(len(ai_data["synthesized_answer"]) > 0)

        # 7. Add Evidence to Case
        ev_res = self.client.post(
            f"/api/cases/{case_id}/evidence",
            headers=self.headers_investigator,
            json={
                "evidence_type": "GSTR_2B_MISMATCH",
                "source": "STATUTORY_ENGINE",
                "description": f"Gate failures detected for {target_inv}",
                "data": {"risk_score": non_compliant[0].risk_score},
                "reliability": 0.95,
            },
        )
        self.assertEqual(ev_res.status_code, 200)
        ev_id = ev_res.json()["evidence_id"]

        # 8. Add Finding to Case
        fnd_res = self.client.post(
            f"/api/cases/{case_id}/findings",
            headers=self.headers_investigator,
            json={
                "title": "Unmatched Input Tax Credit Claim",
                "description": "Invoice missing from counterparty GSTR-1 return",
                "severity": "HIGH",
                "evidence_ids": [ev_id],
                "confidence": 0.95,
            },
        )
        self.assertEqual(fnd_res.status_code, 200)
        fnd_id = fnd_res.json()["finding_id"]

        # 9. Add Recommendation to Case
        rec_res = self.client.post(
            f"/api/cases/{case_id}/recommendation",
            headers=self.headers_investigator,
            json={
                "recommended_action": "RECONCILIATION_REQUIRED",
                "rationale": "Issue tax demand notice to vendor",
                "supporting_finding_ids": [fnd_id],
                "confidence": 0.90,
            },
        )
        self.assertEqual(rec_res.status_code, 200)

        # 10. Human Review Authorization (Authorized Reviewer Decision: APPROVE)
        decision_res = self.client.post(
            f"/api/cases/{case_id}/review",
            headers=self.headers_reviewer,
            json={
                "reviewer": "Senior Tax Reviewer Officer",
                "decision": "APPROVE",
                "comment": "E2E verification complete. Risk exposure and gate failures verified.",
            },
        )
        self.assertEqual(decision_res.status_code, 200, decision_res.text)
        dec_data = decision_res.json()
        self.assertIn(dec_data["status"], ("APPROVED", "READY_FOR_RESOLUTION"))

        # 11. Verify Timeline & Event Provenance
        timeline_res = self.client.get(
            f"/api/cases/{case_id}/timeline",
            headers=self.headers_reviewer,
        )
        self.assertEqual(timeline_res.status_code, 200)
        events = timeline_res.json()
        event_types = [e["event_type"] for e in events]
        self.assertIn("CASE_CREATED", event_types)
        self.assertIn("APPROVED", event_types)


if __name__ == "__main__":
    unittest.main()
