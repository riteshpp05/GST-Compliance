"""
tests.integration.test_s16_api_security
========================================
Sprint 16 Integration Test Suite: REST API Endpoint Protection, Header Authentication, & Error Contracts.
"""

import unittest
from fastapi.testclient import TestClient
from ui.app import app


class TestAPISecurityEndpoints(unittest.TestCase):
    """Integration tests for FastAPI endpoints with mandatory authentication dependencies."""

    def setUp(self):
        import os
        os.environ["APP_ENV"] = "production"
        self.client = TestClient(app)

    def test_unauthenticated_request_yields_401(self):
        # Request without Authorization or X-API-Key header -> 401 Unauthorized
        response = self.client.get("/api/cases")
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["code"], "AUTHENTICATION_ERROR")
        err_detail = data["detail"].lower()
        self.assertTrue("not provided" in err_detail or "invalid" in err_detail)

    def test_invalid_api_key_yields_401(self):
        response = self.client.get("/api/cases", headers={"X-API-Key": "invalid-key-999"})
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["code"], "AUTHENTICATION_ERROR")

    def test_valid_investigator_key_access_granted(self):
        response = self.client.get("/api/cases", headers={"X-API-Key": "key-investigator-123"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)

    def test_ai_agent_key_calling_approval_yields_403(self):
        # Create case first using investigator key
        create_res = self.client.post(
            "/api/cases",
            headers={"X-API-Key": "key-investigator-123"},
            json={"title": "API AI Security Test Case"},
        )
        self.assertEqual(create_res.status_code, 200)
        case_id = create_res.json()["case_id"]

        # AI Agent attempts approval via API -> 403 Forbidden
        review_res = self.client.post(
            f"/api/cases/{case_id}/review",
            headers={"X-API-Key": "key-ai-agent-123"},
            json={
                "reviewer": "AI_AGENT",
                "decision": "APPROVE",
                "comment": "AI attempting REST approval",
            },
        )
        self.assertEqual(review_res.status_code, 403)
        data = review_res.json()
        self.assertTrue("code" in data and ("FORBIDDEN" in data["code"] or "HUMAN" in data.get("detail", "")))

    def test_reviewer_key_calling_approval_access_granted(self):
        # Create case and move to reviewable status
        create_res = self.client.post(
            "/api/cases",
            headers={"X-API-Key": "key-investigator-123"},
            json={"title": "Human Review Case"},
        )
        self.assertEqual(create_res.status_code, 200)
        case_id = create_res.json()["case_id"]

        # Triage, start investigation, add evidence, finding, and recommendation
        self.client.post(f"/api/cases/{case_id}/triage", headers={"X-API-Key": "key-investigator-123"}, json={})
        self.client.post(f"/api/cases/{case_id}/investigation/start", headers={"X-API-Key": "key-investigator-123"})
        res_ev = self.client.post(
            f"/api/cases/{case_id}/evidence",
            headers={"X-API-Key": "key-investigator-123"},
            json={
                "evidence_type": "GST_RETURNS",
                "source": "GSTR-2B",
                "description": "Invoice missing from GSTR-2B",
                "data": {"status": "NOT_FOUND"},
                "reliability": 1.0,
            },
        )
        self.assertEqual(res_ev.status_code, 200)
        ev_id = res_ev.json()["evidence_id"]
        res_fnd = self.client.post(
            f"/api/cases/{case_id}/findings",
            headers={"X-API-Key": "key-investigator-123"},
            json={
                "title": "Unmatched ITC Exposure",
                "description": "ITC claimed without GSTR-2B entry",
                "severity": "HIGH",
                "evidence_ids": [ev_id],
                "confidence": 0.95,
            },
        )
        self.assertEqual(res_fnd.status_code, 200)
        fnd_id = res_fnd.json()["finding_id"]
        res_rec = self.client.post(
            f"/api/cases/{case_id}/recommendation",
            headers={"X-API-Key": "key-investigator-123"},
            json={
                "recommended_action": "RECONCILIATION_REQUIRED",
                "rationale": "Issue vendor notice prior to GSTR-3B filing",
                "supporting_finding_ids": [fnd_id],
                "confidence": 0.9,
            },
        )
        self.assertEqual(res_rec.status_code, 200)

        # Human Reviewer approves -> 200 OK
        review_res = self.client.post(
            f"/api/cases/{case_id}/review",
            headers={"X-API-Key": "key-reviewer-123"},
            json={
                "reviewer": "Senior Tax Reviewer John",
                "decision": "APPROVE",
                "comment": "All compliance criteria verified.",
            },
        )
        self.assertEqual(review_res.status_code, 200)
        data = review_res.json()
        self.assertIn(data["status"], ("APPROVED", "READY_FOR_RESOLUTION"))
