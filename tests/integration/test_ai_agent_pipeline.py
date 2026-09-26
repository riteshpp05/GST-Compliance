"""
tests.integration.test_ai_agent_pipeline
========================================
Integration tests for Sprint 12.1 Controlled AI Investigation Agent API Endpoint.
Verifies:
  1. POST /api/agent/investigate endpoint contract & Pydantic response schema
  2. Single invoice risk query processing via API
  3. Financial exposure query processing via API
  4. Force fallback flag parameter override
  5. Input validation (400 Bad Request for empty/whitespace query)
"""

import unittest
from fastapi.testclient import TestClient

from ui.app import app


class TestAIAgentPipelineIntegration(unittest.TestCase):
    """Integration test suite for AI Investigation Agent REST API."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        # Run pipeline once so deterministic engines have data populated
        r = cls.client.post("/api/run")
        assert r.status_code == 200, f"Setup run failed with status {r.status_code}"

    def test_01_investigate_risk_query(self):
        """Test POST /api/agent/investigate with single invoice risk query."""
        payload = {
            "query": "Why is invoice INV-8000001 high risk?",
            "invoice_id": "INV-8000001"
        }
        resp = self.client.post("/api/agent/investigate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["query"], payload["query"])
        self.assertIn("intent", data)
        self.assertIn("plan", data)
        self.assertIn("tool_results", data)
        self.assertIn("synthesized_answer", data)
        self.assertIn("provider_status", data)
        self.assertTrue(data["guardrails_passed"])
        self.assertGreater(data["confidence_score"], 0.0)

        # Sprint 12.2 Agentic Loop Response Fields Verification
        self.assertIn("investigation_id", data)
        self.assertIsNotNone(data["investigation_id"])
        self.assertTrue(data["investigation_id"].startswith("INVEST-"))
        self.assertIn("investigation_status", data)
        self.assertIn("termination_reason", data)
        self.assertIn("investigation_steps", data)
        self.assertTrue(len(data["investigation_steps"]) >= 2)
        self.assertIn("evidence_sufficiency", data)
        self.assertIn("contradictions", data)

    def test_02_investigate_financial_query(self):
        """Test POST /api/agent/investigate with financial exposure query."""
        payload = {
            "query": "What is our total tax exposure across non-compliant invoices?"
        }
        resp = self.client.post("/api/agent/investigate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["intent"]["intent"], "FINANCIAL_EXPOSURE")
        self.assertGreaterEqual(len(data["tool_results"]), 0)
        self.assertIn("Deterministic GST Engine Determination", data["synthesized_answer"])

    def test_03_investigate_force_fallback(self):
        """Test force_fallback flag forcing deterministic synthesis."""
        payload = {
            "query": "Are there duplicate invoices?",
            "force_fallback": True
        }
        resp = self.client.post("/api/agent/investigate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertFalse(data["provider_status"]["available"])

    def test_04_investigate_empty_query_validation(self):
        """Test that empty or whitespace query returns 400 Bad Request."""
        resp1 = self.client.post("/api/agent/investigate", json={"query": ""})
        self.assertEqual(resp1.status_code, 400)

        resp2 = self.client.post("/api/agent/investigate", json={"query": "   "})
        self.assertEqual(resp2.status_code, 400)


if __name__ == "__main__":
    unittest.main()
