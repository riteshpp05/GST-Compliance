"""
tests.integration.test_s15_api_endpoints
==========================================
Integration Test Suite for Sprint 15 REST API Endpoints.
Verifies HTTP contracts and status codes for:
  1. POST /api/cases
  2. GET /api/cases
  3. GET /api/cases/{case_id}
  4. POST /api/cases/{case_id}/triage
  5. POST /api/cases/{case_id}/investigation/start
  6. POST /api/cases/{case_id}/plan
  7. GET /api/cases/{case_id}/plan
  8. POST /api/cases/{case_id}/evidence
  9. GET /api/cases/{case_id}/evidence
 10. POST /api/cases/{case_id}/findings
 11. GET /api/cases/{case_id}/findings
 12. POST /api/cases/{case_id}/risk-assessment
 13. GET /api/cases/{case_id}/risk-assessment
 14. POST /api/cases/{case_id}/recommendation
 15. GET /api/cases/{case_id}/recommendation
 16. POST /api/cases/{case_id}/review
 17. POST /api/cases/{case_id}/resolve
 18. POST /api/cases/{case_id}/close
 19. GET /api/cases/{case_id}/timeline
"""

import unittest
from fastapi.testclient import TestClient

from ui.app import app


class TestS15ApiEndpointsIntegration(unittest.TestCase):
    """Integration tests for S15 FastAPI Endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        # Populate pipeline so data exists
        r = cls.client.post("/api/run")
        assert r.status_code == 200, f"Pipeline run failed with status {r.status_code}"

    def test_01_create_and_fetch_case(self):
        """Test POST /api/cases and GET /api/cases/{id}."""
        resp = self.client.post(
            "/api/cases",
            json={
                "invoice_id": "INV-8000001",
                "counterparty_gstin": "29XCDBM5846M9ZE",
                "title": "API Test Case for INV-8000001",
                "source": "MANUAL_TEST",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        case_id = data["case_id"]

        # Fetch case
        get_resp = self.client.get(f"/api/cases/{case_id}")
        self.assertEqual(get_resp.status_code, 200, get_resp.text)
        get_data = get_resp.json()
        self.assertEqual(get_data["case_id"], case_id)
        self.assertEqual(get_data["status"], "CREATED")

    def test_02_full_case_workflow_api_chain(self):
        """Test chained execution of all workflow REST endpoints."""
        # 1. Create Case
        res_create = self.client.post("/api/cases", json={"invoice_id": "INV-8000001", "title": "Full API Chain Case"})
        self.assertEqual(res_create.status_code, 200)
        case_id = res_create.json()["case_id"]

        # 2. Triage Case
        res_triage = self.client.post(
            f"/api/cases/{case_id}/triage",
            json={"priority": "P1", "risk_level": "CRITICAL", "category": "TAX_MISMATCH", "actor": "TAX_OFFICER_JOHN"},
        )
        self.assertEqual(res_triage.status_code, 200)
        self.assertEqual(res_triage.json()["priority"], "P1")

        # 3. Create Investigation Plan
        res_plan = self.client.post(
            f"/api/cases/{case_id}/plan",
            json={
                "objective": "Verify Place of Supply tax liability",
                "questions": ["Is counterparty registered in POS state?"],
                "required_data": ["GSTR-1", "GSTR-2B"],
                "expected_evidence": ["EVIDENCE_POS"],
                "analysis_tasks": ["Cross-check GSTIN state prefix"],
                "risk_areas": ["POS_MISMATCH"],
            },
        )
        self.assertEqual(res_plan.status_code, 200)
        self.assertEqual(res_plan.json()["objective"], "Verify Place of Supply tax liability")

        # Fetch Plan
        res_get_plan = self.client.get(f"/api/cases/{case_id}/plan")
        self.assertEqual(res_get_plan.status_code, 200)
        self.assertEqual(res_get_plan.json()["objective"], "Verify Place of Supply tax liability")

        # 4. Start Investigation
        res_start = self.client.post(f"/api/cases/{case_id}/investigation/start", json={"actor": "INVESTIGATOR_ALICE"})
        self.assertEqual(res_start.status_code, 200)
        self.assertEqual(res_start.json()["status"], "INVESTIGATING")

        # 5. Add Evidence
        res_ev = self.client.post(
            f"/api/cases/{case_id}/evidence",
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

        # Get Evidence Records
        res_get_ev = self.client.get(f"/api/cases/{case_id}/evidence")
        self.assertEqual(res_get_ev.status_code, 200)
        self.assertEqual(len(res_get_ev.json()["evidence_records"]), 1)

        # 6. Add Finding
        res_fnd = self.client.post(
            f"/api/cases/{case_id}/findings",
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

        # Get Findings
        res_get_fnd = self.client.get(f"/api/cases/{case_id}/findings")
        self.assertEqual(res_get_fnd.status_code, 200)
        self.assertEqual(len(res_get_fnd.json()), 1)

        # 7. Post Risk Assessment
        res_risk = self.client.post(
            f"/api/cases/{case_id}/risk-assessment",
            json={
                "risk_score": 88.0,
                "risk_level": "HIGH",
                "contributing_factors": ["Unmatched ITC"],
                "explanation": "High financial exposure.",
            },
        )
        self.assertEqual(res_risk.status_code, 200)

        # Get Risk Assessment
        res_get_risk = self.client.get(f"/api/cases/{case_id}/risk-assessment")
        self.assertEqual(res_get_risk.status_code, 200)
        self.assertEqual(res_get_risk.json()["risk_score"], 88.0)

        # 8. Post Recommendation
        res_rec = self.client.post(
            f"/api/cases/{case_id}/recommendation",
            json={
                "recommended_action": "RECONCILIATION_REQUIRED",
                "rationale": "Issue vendor notice prior to GSTR-3B filing",
                "supporting_finding_ids": [fnd_id],
                "confidence": 0.9,
            },
        )
        self.assertEqual(res_rec.status_code, 200)

        # Get Recommendation
        res_get_rec = self.client.get(f"/api/cases/{case_id}/recommendation")
        self.assertEqual(res_get_rec.status_code, 200)
        self.assertEqual(res_get_rec.json()["recommended_action"], "RECONCILIATION_REQUIRED")

        # 9. Submit Review (APPROVE)
        res_rev = self.client.post(
            f"/api/cases/{case_id}/review",
            json={
                "reviewer": "TAX_DIRECTOR",
                "reviewer_role": "Tax Director",
                "decision": "APPROVE",
                "comment": "Approved reconciliation action.",
            },
        )
        self.assertEqual(res_rev.status_code, 200)
        self.assertEqual(res_rev.json()["status"], "READY_FOR_RESOLUTION")

        # 10. Resolve Case
        res_res = self.client.post(
            f"/api/cases/{case_id}/resolve",
            json={"actor": "TAX_DIRECTOR", "resolution_summary": "Reconciliation notice issued."},
        )
        self.assertEqual(res_res.status_code, 200)
        self.assertEqual(res_res.json()["status"], "RESOLVED")

        # 11. Close Case
        res_cls = self.client.post(
            f"/api/cases/{case_id}/close",
            json={"actor": "TAX_DIRECTOR", "closure_notes": "All steps completed."},
        )
        self.assertEqual(res_cls.status_code, 200)
        self.assertEqual(res_cls.json()["status"], "CLOSED")

        # 12. Fetch Timeline
        res_tl = self.client.get(f"/api/cases/{case_id}/timeline")
        self.assertEqual(res_tl.status_code, 200)
        events = res_tl.json()
        self.assertGreater(len(events), 5)

    def test_03_list_cases_filter(self):
        """Test GET /api/cases filtering."""
        resp = self.client.get("/api/cases")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(isinstance(resp.json(), list))


if __name__ == "__main__":
    unittest.main()
