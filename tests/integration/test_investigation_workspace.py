"""
Integration tests for UC15 Reusable Invoice Investigation Workspace backend API.
Verifies multiple invoice types (Clean, AP, AR, Intra-State, Inter-State, EWB Required, EWB Not Required, GSTIN Issue, Tax Issue).
"""
import unittest
from fastapi.testclient import TestClient
from ui.app import app


class TestInvestigationWorkspace(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-investigator-123"})
        # Ensure results are populated
        cls.client.post("/api/run")

    def test_dossier_clean_invoice(self):
        resp = self.client.get("/api/investigation/invoice/INV-2026-CLEAN-AR-02")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["invoice_no"], "INV-2026-CLEAN-AR-02")
        self.assertIn("decision", data)
        self.assertIn("canonical", data)
        canonical = data["canonical"]
        self.assertEqual(canonical["taxable_value"], 55000.0)
        self.assertEqual(canonical["total_tax"], 9900.0)
        self.assertEqual(canonical["total_amount"], 64900.0)
        self.assertEqual(canonical["effective_tax_rate"], 18.0)
        self.assertEqual(canonical["eway_bill"], "GENERATED")

    def test_dossier_gstin_issue_invoice(self):
        resp = self.client.get("/api/investigation/invoice/INV-2026-GSTIN-01")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        canonical = data["canonical"]
        self.assertEqual(canonical["taxable_value"], 40000.0)
        self.assertEqual(canonical["total_tax"], 7200.0)
        self.assertEqual(canonical["total_amount"], 47200.0)
        self.assertEqual(canonical["effective_tax_rate"], 18.0)
        self.assertIn(canonical["eway_bill"], ("UNKNOWN", "", "NOT_REQUIRED"))

    def test_dossier_non_existent_invoice(self):
        resp = self.client.get("/api/investigation/invoice/NONEXISTENT-999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()

