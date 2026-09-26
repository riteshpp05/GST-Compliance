"""
tests.integration.test_s18_api_security
========================================
Sprint 18 Integration & Security Test Suite: REST APIs, Human Review Packages, Evaluation, & AI Boundary Enforcement.
"""

import os
import unittest
from fastapi.testclient import TestClient
import app.data.service as ds_mod
from ui.app import app


class TestS18APISecurity(unittest.TestCase):

    def setUp(self):
        os.environ["APP_ENV"] = "production"
        os.environ["PERSISTENCE_BACKEND"] = "memory"
        ds_mod._GLOBAL_DATA_SERVICE = None
        self.client = TestClient(app)
        self.client.headers.update({"X-API-Key": "key-admin-123"})

    def test_unauthenticated_request_yields_401(self):
        c = TestClient(app)
        resp = c.post("/api/investigations", json={"case_id": "CASE-DUMMY"})
        self.assertEqual(resp.status_code, 401)

    def test_investigation_execution_api_flow(self):
        # 1. Create case via API
        create_res = self.client.post(
            "/api/cases",
            headers={"X-API-Key": "key-investigator-123"},
            json={"invoice_id": "INV-API-800", "title": "API Test Investigation Case"},
        )
        self.assertEqual(create_res.status_code, 200)
        case_id = create_res.json()["case_id"]

        # 2. Trigger investigation orchestration
        inv_res = self.client.post(
            "/api/investigations",
            headers={"X-API-Key": "key-investigator-123"},
            json={"case_id": case_id, "objective": "Investigate tax rate mismatch", "invoice_id": "INV-API-800"},
        )
        self.assertEqual(inv_res.status_code, 200, inv_res.text)
        data = inv_res.json()
        self.assertEqual(data["case_id"], case_id)
        self.assertIn("confidence_level", data)
        self.assertGreaterEqual(data["evidence_count"], 1)

        # 3. Retrieve operational trace
        inv_id = data["investigation_id"]
        tr_res = self.client.get(f"/api/investigations/{inv_id}/trace", headers={"X-API-Key": "key-investigator-123"})
        self.assertEqual(tr_res.status_code, 200)

        # 4. Retrieve Human Review Package
        rev_res = self.client.get(f"/api/cases/{case_id}/review-package", headers={"X-API-Key": "key-reviewer-123"})
        self.assertEqual(rev_res.status_code, 200)
        pkg = rev_res.json()
        self.assertEqual(pkg["case_id"], case_id)
        self.assertIn("key_findings", pkg)
        self.assertIn("confidence_score", pkg)

    def test_ai_agent_blocked_from_human_resolution(self):
        # AI Agent can run investigation evaluation
        eval_res = self.client.post(
            "/api/evaluations",
            headers={"X-API-Key": "key-ai-agent-123"},
        )
        self.assertEqual(eval_res.status_code, 200)

        # AI Agent STILL STRICTLY BLOCKED from human review/resolution
        rev_res = self.client.post(
            "/api/cases/CASE-DUMMY/review",
            headers={"X-API-Key": "key-ai-agent-123"},
            json={"reviewer": "AI_AGENT", "decision": "APPROVE", "comment": "AI attempting review"},
        )
        self.assertEqual(rev_res.status_code, 403)
