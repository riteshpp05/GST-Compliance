"""
tests.integration.test_case_management_flow
=============================================
Integration Test Suite for Sprint 13 Case Management & Human Approval Subsystem.
Verifies complete flow: Session -> Dossier -> Case -> Assignment -> Review -> Request More Evidence -> Re-investigation -> Approval -> READY_FOR_RESOLUTION.
Also verifies REST API endpoints and Rejection flow.
"""

import unittest
from fastapi.testclient import TestClient

from app.agent.ai.models import InvestigationRequest
from app.agent.ai.orchestrator import AIInvestigationAgent
from app.case.models import CaseDecisionEnum, CaseStatusEnum
from app.case.service import CaseService
from ui.app import app


class TestCaseManagementFlowIntegration(unittest.TestCase):
    """Integration test suite for Sprint 13 Case Management."""

    def setUp(self):
        self.client = TestClient(app)
        self.client.headers.update({"X-API-Key": "key-admin-123"})
        self.agent = AIInvestigationAgent()
        self.case_service = CaseService(agent=self.agent)

    def test_full_case_lifecycle_flow(self):
        # 1. Investigation Session & Query
        session = self.agent.session_manager.create_session()
        session.entity_focus.invoice_id = "INV-2026-CLEAN-AR-01"
        session_id = session.session_id
        req1 = InvestigationRequest(user_query="Why is invoice INV-2026-CLEAN-AR-01 high risk?", invoice_no="INV-2026-CLEAN-AR-01", session_id=session_id)
        resp1 = self.agent.investigate(req1)
        self.assertIsNotNone(resp1)

        # 2. Create Case from Session
        case = self.case_service.create_case_from_session(session_id=session_id)
        case_id = case.case_id
        self.assertEqual(case.status, CaseStatusEnum.REVIEW_REQUIRED)
        self.assertEqual(case.invoice_id, "INV-2026-CLEAN-AR-01")
        self.assertTrue(len(case.evidence_references) > 0)

        # 3. Assign Case
        assigned_case = self.case_service.assign_case(
            case_id=case_id,
            assigned_to="Jane Tax Expert",
            assigned_role="Senior Tax Analyst",
            reason="Assigned for complex Place of Supply & Rule 36(4) verification.",
        )
        self.assertEqual(assigned_case.assigned_to, "Jane Tax Expert")

        # 4. Submit REQUEST_MORE_EVIDENCE Human Decision
        rev_case = self.case_service.request_more_evidence_workflow(
            case_id=case_id,
            reviewer="Jane Tax Expert",
            comment="Please run additional check on Rule 36(4) GSTR-2B reflection.",
            requested_evidence_details="Verify GSTR-2B reflection status for Rule 36(4)",
        )
        # Should complete re-investigation and return to REVIEW_REQUIRED
        self.assertEqual(rev_case.status, CaseStatusEnum.REVIEW_REQUIRED)

        # 5. Submit Human Approval Decision
        app_case = self.case_service.submit_human_review(
            case_id=case_id,
            reviewer="Jane Tax Expert",
            decision=CaseDecisionEnum.APPROVE,
            comment="Verified all gate failures and financial exposure. Approved for resolution queue.",
        )
        self.assertEqual(app_case.status, CaseStatusEnum.READY_FOR_RESOLUTION)

        # 6. Verify Timeline & Events
        events = self.case_service.get_timeline(case_id)
        event_types = [e.event_type for e in events]
        self.assertIn("CASE_CREATED", event_types)
        self.assertIn("ASSIGNED", event_types)
        self.assertIn("MORE_EVIDENCE_REQUESTED", event_types)
        self.assertIn("APPROVED", event_types)
        self.assertIn("STATUS_CHANGED", event_types)

    def test_rejection_flow(self):
        session = self.agent.session_manager.create_session()
        req = InvestigationRequest(user_query="Why is invoice INV-2026-CLEAN-AR-01 high risk?", invoice_no="INV-2026-CLEAN-AR-01", session_id=session.session_id)
        self.agent.investigate(req)

        case = self.case_service.create_case_from_session(session_id=session.session_id)
        rej_case = self.case_service.submit_human_review(
            case_id=case.case_id,
            reviewer="Auditor Bob",
            decision=CaseDecisionEnum.REJECT,
            comment="Rejected due to insufficient vendor response.",
        )
        self.assertEqual(rej_case.status, CaseStatusEnum.REJECTED)

    def test_rest_api_case_endpoints(self):
        # 1. Start Session
        sess_resp = self.client.post("/api/agent/session/start")
        self.assertEqual(sess_resp.status_code, 200)
        session_id = sess_resp.json()["session_id"]

        # Run query
        self.client.post(f"/api/agent/session/{session_id}/query", json={"user_query": "Why is invoice INV-2026-CLEAN-AP-01 high risk?"})

        # 2. POST /api/cases
        create_resp = self.client.post("/api/cases", json={"session_id": session_id, "title": "API Test Case"})
        self.assertEqual(create_resp.status_code, 200)
        case_data = create_resp.json()
        case_id = case_data["case_id"]
        self.assertEqual(case_data["status"], "REVIEW_REQUIRED")

        # 3. GET /api/cases
        list_resp = self.client.get("/api/cases")
        self.assertEqual(list_resp.status_code, 200)
        self.assertTrue(len(list_resp.json()) > 0)

        # 4. GET /api/cases/{case_id}
        get_resp = self.client.get(f"/api/cases/{case_id}")
        self.assertEqual(get_resp.status_code, 200)

        # 5. POST /api/cases/{case_id}/assign
        assign_resp = self.client.post(f"/api/cases/{case_id}/assign", json={"assigned_to": "API Reviewer", "assigned_role": "Analyst"})
        self.assertEqual(assign_resp.status_code, 200)

        # 6. POST /api/cases/{case_id}/review (APPROVE)
        rev_resp = self.client.post(
            f"/api/cases/{case_id}/review",
            json={
                "reviewer": "API Reviewer",
                "decision": "APPROVE",
                "comment": "Approved via REST API test.",
            },
        )
        self.assertEqual(rev_resp.status_code, 200)
        self.assertEqual(rev_resp.json()["status"], "READY_FOR_RESOLUTION")

        # 7. GET /api/cases/{case_id}/timeline
        tm_resp = self.client.get(f"/api/cases/{case_id}/timeline")
        self.assertEqual(tm_resp.status_code, 200)
        self.assertTrue(len(tm_resp.json()) > 0)


if __name__ == "__main__":
    unittest.main()
