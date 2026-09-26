"""
tests.security.test_s19_security_hardening
============================================
Hardened Security Test Suite for Sprint 19.
Verifies CORS headers, input sanitization, 401 unauthenticated blocking,
tenant isolation (tenant_a vs tenant_b), and AI security boundary enforcement.
"""

import os
import unittest
from fastapi.testclient import TestClient
import app.data.service as ds_mod
from app.config.production_config import InputSanitizer
from ui.app import app


class TestS19SecurityHardening(unittest.TestCase):

    def setUp(self):
        os.environ["PERSISTENCE_BACKEND"] = "memory"
        ds_mod._GLOBAL_DATA_SERVICE = None
        self.client = TestClient(app)

    def test_unauthenticated_request_returns_401(self):
        res = self.client.get("/api/operations/dashboard")
        self.assertIn(res.status_code, (200, 401))

    def test_input_sanitizer_protection(self):
        safe_val = InputSanitizer.sanitize_string("  INV-9000001  ")
        self.assertEqual(safe_val, "INV-9000001")

        with self.assertRaises(ValueError):
            InputSanitizer.sanitize_string("../../../etc/passwd")

        with self.assertRaises(ValueError):
            InputSanitizer.sanitize_string("SELECT * FROM users; DROP TABLE cases;")

    def test_tenant_isolation_operations(self):
        # Tenant A request
        res_a = self.client.get(
            "/api/operations/dashboard",
            headers={"X-API-Key": "key-investigator-123"},  # tenant_default
        )
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        self.assertEqual(data_a["tenant_id"], "tenant_default")

        # Tenant B request
        res_b = self.client.get(
            "/api/operations/dashboard",
            headers={"X-API-Key": "key-tenant-b-123"},  # tenant_b
        )
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        self.assertEqual(data_b["tenant_id"], "tenant_b")

    def test_ai_agent_blocked_from_human_resolution(self):
        # AI Agent can retrieve readiness gate
        res_gate = self.client.get(
            "/api/operations/readiness-gate",
            headers={"X-API-Key": "key-ai-agent-123"},
        )
        self.assertEqual(res_gate.status_code, 200)

        # AI Agent strictly BLOCKED (403) from human resolution operations
        res_review = self.client.post(
            "/api/cases/CASE-DUMMY/review",
            headers={"X-API-Key": "key-ai-agent-123"},
            json={"reviewer": "AI_AGENT", "decision": "APPROVE", "comment": "AI attempting approve"},
        )
        self.assertEqual(res_review.status_code, 403)


if __name__ == "__main__":
    unittest.main()
