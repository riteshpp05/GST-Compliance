"""
tests.integration.test_multi_turn_workspace
=============================================
Integration Test Suite for Sprint 12.4 Multi-Turn Investigation Workspace & Dossier REST API.
Verifies:
  1. POST /api/agent/session/start endpoint contract
  2. POST /api/agent/session/{session_id}/query multi-turn execution
  3. GET /api/agent/session/{session_id} state and focus retrieval
  4. POST /api/agent/session/{session_id}/dossier generation (JSON & Markdown)
  5. GET /api/agent/session/{session_id}/dossier/pdf PDF file export & content header
"""

import unittest
from fastapi.testclient import TestClient

from ui.app import app


class TestMultiTurnWorkspaceIntegration(unittest.TestCase):
    """Integration test suite for Multi-Turn Workspace & Dossier REST API."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        # Populate data pipeline
        r = cls.client.post("/api/run")
        assert r.status_code == 200, f"Pipeline run failed with status {r.status_code}"

    def test_01_start_session(self):
        resp = self.client.post("/api/agent/session/start", json={"invoice_no": "INV-8000001"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("session_id", data)
        self.assertTrue(data["session_id"].startswith("SESS-"))
        self.assertEqual(data["entity_focus"]["invoice_id"], "INV-8000001")

    def test_02_multi_turn_investigation_flow(self):
        # 1. Start Session
        r_start = self.client.post("/api/agent/session/start")
        session_id = r_start.json()["session_id"]

        # 2. Turn 1: Explicit query
        q1 = {"query": "Why is invoice INV-8000001 high risk?"}
        r1 = self.client.post(f"/api/agent/session/{session_id}/query", json=q1)
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        self.assertEqual(d1["session_id"], session_id)
        self.assertEqual(d1["entity_focus"]["invoice_id"], "INV-8000001")

        # 3. Turn 2: Implicit follow-up query without mentioning invoice ID
        q2 = {"query": "Why is it non-compliant?"}
        r2 = self.client.post(f"/api/agent/session/{session_id}/query", json=q2)
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertEqual(d2["session_id"], session_id)
        self.assertIn("INV-8000001", d2["answer"])

        # 4. Get Session details
        r_sess = self.client.get(f"/api/agent/session/{session_id}")
        self.assertEqual(r_sess.status_code, 200)
        s_data = r_sess.json()
        self.assertEqual(len(s_data["turns"]), 2)

        # 5. Generate Dossier
        r_dos = self.client.post(f"/api/agent/session/{session_id}/dossier")
        self.assertEqual(r_dos.status_code, 200)
        dos_data = r_dos.json()
        self.assertIn("dossier", dos_data)
        self.assertIn("markdown", dos_data)
        self.assertIn("UC15 GST COMPLIANCE & INVESTIGATION DOSSIER", dos_data["markdown"])

        # 6. Download PDF Report
        r_pdf = self.client.get(f"/api/agent/session/{session_id}/dossier/pdf")
        self.assertEqual(r_pdf.status_code, 200)
        self.assertEqual(r_pdf.headers["content-type"], "application/pdf")
        self.assertTrue(r_pdf.content.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
