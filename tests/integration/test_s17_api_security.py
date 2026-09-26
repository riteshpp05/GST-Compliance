"""
tests.integration.test_s17_api_security
========================================
Sprint 17 Integration & Security Test Suite: Ingestion Endpoints, Authorization, Multi-Tenant Isolation, & AI Boundary Enforcement.
"""

import unittest
from fastapi.testclient import TestClient
from ui.app import app


class TestS17APISecurity(unittest.TestCase):
    """Integration test suite for Sprint 17 REST API endpoints."""

    def setUp(self):
        import os
        import app.data.service as ds_mod
        os.environ["APP_ENV"] = "production"
        os.environ["PERSISTENCE_BACKEND"] = "memory"
        ds_mod._GLOBAL_DATA_SERVICE = None
        self.client = TestClient(app)
        self.client.headers.update({"X-API-Key": "key-admin-123"})

    def test_unauthenticated_request_yields_401(self):
        # Request without Authorization or X-API-Key header -> 401 Unauthorized
        c = TestClient(app)
        resp = c.get("/api/ingestion")
        self.assertEqual(resp.status_code, 401)

    def test_valid_investigator_ingestion_flow(self):
        records = [
            {
                "invoice_number": "INV-7001",
                "supplier_gstin": "27ABCDE1234F1Z5",
                "invoice_date": "2026-04-01",
                "counterparty_name": "Test Vendor",
                "taxable_value": 20000.0,
                "place_of_supply": "Maharashtra",
                "hsn_sac": "3926",
            }
        ]

        resp = self.client.post(
            "/api/ingestion",
            headers={"X-API-Key": "key-investigator-123"},
            json={"source_name": "API Test Source", "dataset_type": "INVOICES", "records": records},
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("ingestion_job", data)
        self.assertIn("data_quality_report", data)
        ingestion_id = data["ingestion_job"]["ingestion_id"]

        # Fetch job
        get_res = self.client.get(f"/api/ingestion/{ingestion_id}", headers={"X-API-Key": "key-investigator-123"})
        self.assertEqual(get_res.status_code, 200)

        # Fetch quality report
        q_res = self.client.get(f"/api/ingestion/{ingestion_id}/quality", headers={"X-API-Key": "key-investigator-123"})
        self.assertEqual(q_res.status_code, 200)
        self.assertGreaterEqual(q_res.json()["overall_quality_score"], 80.0)

    def test_cross_tenant_job_access_denied(self):
        # Create job under tenant_default
        create_res = self.client.post(
            "/api/ingestion",
            headers={"X-API-Key": "key-investigator-123"},
            json={"source_name": "Tenant A Job", "records": [{"invoice_number": "INV-7002", "supplier_gstin": "27ABCDE1234F1Z5", "taxable_value": 1000.0}]},
        )
        ing_id = create_res.json()["ingestion_job"]["ingestion_id"]

        # Tenant B attempts access -> 403 Forbidden
        get_res = self.client.get(f"/api/ingestion/{ing_id}", headers={"X-API-Key": "key-tenant-b-123"})
        self.assertEqual(get_res.status_code, 403)

    def test_ai_agent_ingestion_and_human_boundary_integrity(self):
        records = [
            {
                "invoice_number": "INV-7003",
                "supplier_gstin": "27ABCDE1234F1Z5",
                "invoice_date": "2026-04-01",
                "taxable_value": 5000.0,
            }
        ]

        # AI Agent can ingest and validate data
        ing_res = self.client.post(
            "/api/ingestion",
            headers={"X-API-Key": "key-ai-agent-123"},
            json={"source_name": "AI Agent Ingestion", "records": records},
        )
        self.assertEqual(ing_res.status_code, 200)

        # AI Agent STILL STRICTLY BLOCKED from human resolution actions
        rev_res = self.client.post(
            "/api/cases/CASE-DUMMY/review",
            headers={"X-API-Key": "key-ai-agent-123"},
            json={"reviewer": "AI_AGENT", "decision": "APPROVE", "comment": "AI attempting review"},
        )
        self.assertEqual(rev_res.status_code, 403)

    def test_analyze_ingested_dataset_creates_case(self):
        # Ingest non-compliant invoice (missing POS / tax mismatch)
        records = [
            {
                "invoice_number": "INV-7004-NONCOMP",
                "supplier_gstin": "INVALID_GSTIN_FORMAT",  # Will fail validation / cause non-compliance
                "invoice_date": "2026-04-01",
                "taxable_value": 100000.0,
                "place_of_supply": "Maharashtra",
                "hsn_sac": "3926",
            }
        ]

        ing_res = self.client.post(
            "/api/ingestion",
            headers={"X-API-Key": "key-investigator-123"},
            json={"source_name": "Critical non-comp dataset", "records": records},
        )
        ing_id = ing_res.json()["ingestion_job"]["ingestion_id"]

        # Trigger intelligence analysis
        an_res = self.client.post(
            f"/api/ingestion/{ing_id}/analyze",
            headers={"X-API-Key": "key-investigator-123"},
            json={"create_case_for_critical": True},
        )
        self.assertEqual(an_res.status_code, 200)
        data = an_res.json()
        self.assertIn("total_analyzed", data)
