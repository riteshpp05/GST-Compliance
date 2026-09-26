"""
tests.unit.test_invoice_workspace_endpoints
============================================
Comprehensive test suite for Unified Invoice Workspace endpoints:
  1. POST /api/invoice/{invoice_no}/correct
  2. POST /api/invoice/{invoice_no}/recheck
  3. POST /api/invoice/{invoice_no}/approve
  4. GET  /api/invoice/{invoice_no}/corrections
  5. GET  /api/invoice/{invoice_no}/approval
  6. Invalidation lifecycle on subsequent correction
"""

import unittest
from fastapi.testclient import TestClient
from ui.app import app, _ensure_results_loaded


class TestInvoiceWorkspaceEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        results, agent = _ensure_results_loaded(force_reload=True)
        assert len(results) > 0, "No results loaded from pipeline."
        cls.sample_invoice_no = results[0].invoice_no

    def test_01_correct_invoice_success(self):
        """Test applying a valid field correction to an invoice."""
        payload = {
            "corrections": {
                "hsn_sac": "998313",
                "place_of_supply": "27",
                "cgst_rate": "9.00",
                "sgst_rate": "9.00",
            },
            "reason": "Corrected HSN code and aligned state tax rates",
            "corrected_by": "TAX_AUDITOR",
        }
        res = self.client.post(f"/api/invoice/{self.sample_invoice_no}/correct", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["status"], "CORRECTED")
        self.assertEqual(data["invoice_no"], self.sample_invoice_no)
        self.assertIn("hsn_sac", data["corrections_applied"])
        self.assertEqual(data["corrections_applied"]["hsn_sac"]["new"], "998313")
        self.assertEqual(data["corrected_by"], "TAX_AUDITOR")

    def test_02_correct_invoice_rejects_unallowed_fields(self):
        """Test that attempting to modify unallowed fields fails with 400."""
        payload = {
            "corrections": {
                "internal_id": "malicious_override",
            },
            "reason": "Test unallowed field",
        }
        res = self.client.post(f"/api/invoice/{self.sample_invoice_no}/correct", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("not correctable", res.json()["detail"])

    def test_03_correct_invoice_rejects_invalid_decimal(self):
        """Test that invalid numeric decimal values fail with 400."""
        payload = {
            "corrections": {
                "cgst_rate": "invalid_number_abc",
            },
            "reason": "Test bad decimal",
        }
        res = self.client.post(f"/api/invoice/{self.sample_invoice_no}/correct", json=payload)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid decimal value", res.json()["detail"])

    def test_04_recheck_invoice_success(self):
        """Test re-running compliance validation on an invoice."""
        res = self.client.post(f"/api/invoice/{self.sample_invoice_no}/recheck")
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["invoice_no"], self.sample_invoice_no)
        self.assertIn("current_status", data)
        self.assertIn("gates", data)
        self.assertGreaterEqual(len(data["gates"]), 1)
        self.assertIn("canonical", data)

    def test_05_approve_and_reject_lifecycle(self):
        """Test approving and rejecting an invoice with validation."""
        # 1. Reject without comment should fail (min 5 chars)
        res_fail = self.client.post(
            f"/api/invoice/{self.sample_invoice_no}/approve",
            json={"action": "APPROVE", "comment": "ok"},
        )
        self.assertEqual(res_fail.status_code, 400)

        # 2. Valid Approval
        appr_payload = {
            "action": "APPROVE",
            "comment": "All statutory gates verified and confirmed by tax lead.",
            "approved_by": "SENIOR_TAX_LEAD",
        }
        res_appr = self.client.post(f"/api/invoice/{self.sample_invoice_no}/approve", json=appr_payload)
        self.assertEqual(res_appr.status_code, 200, res_appr.text)
        appr_data = res_appr.json()
        self.assertEqual(appr_data["approval_status"], "APPROVED")
        self.assertEqual(appr_data["approved_by"], "SENIOR_TAX_LEAD")

        # 3. GET /approval
        res_get = self.client.get(f"/api/invoice/{self.sample_invoice_no}/approval")
        self.assertEqual(res_get.status_code, 200)
        app_record = res_get.json()["approval"]
        self.assertIsNotNone(app_record)
        self.assertEqual(app_record["status"], "APPROVED")
        self.assertFalse(app_record["invalidated"])

        # 4. Applying a correction should invalidate the approval
        corr_payload = {
            "corrections": {"hsn_sac": "84713020"},
            "reason": "Subsequent correction after approval",
        }
        res_corr = self.client.post(f"/api/invoice/{self.sample_invoice_no}/correct", json=corr_payload)
        self.assertEqual(res_corr.status_code, 200)

        # 5. Check approval record is now marked invalidated
        res_get_inv = self.client.get(f"/api/invoice/{self.sample_invoice_no}/approval")
        self.assertTrue(res_get_inv.json()["approval"]["invalidated"])

        # 6. Rejection flow
        rej_payload = {
            "action": "REJECT",
            "comment": "Invoice blocked due to unresolved cross-state rate issue.",
            "approved_by": "FINANCE_CONTROLLER",
        }
        res_rej = self.client.post(f"/api/invoice/{self.sample_invoice_no}/approve", json=rej_payload)
        self.assertEqual(res_rej.status_code, 200)
        self.assertEqual(res_rej.json()["approval_status"], "REJECTED")

    def test_06_get_corrections_audit_trail(self):
        """Test retrieving the correction audit history."""
        res = self.client.get(f"/api/invoice/{self.sample_invoice_no}/corrections")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["invoice_no"], self.sample_invoice_no)
        self.assertIsInstance(data["corrections"], list)
        self.assertGreaterEqual(len(data["corrections"]), 1)
        first_entry = data["corrections"][0]
        self.assertIn("timestamp", first_entry)
        self.assertIn("corrected_by", first_entry)
        self.assertIn("changes", first_entry)


if __name__ == "__main__":
    unittest.main()
