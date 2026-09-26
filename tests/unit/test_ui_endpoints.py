"""
tests.unit.test_ui_endpoints
============================
Unit & Integration tests for Sprint 10 Investigation UI & Enterprise Dashboard.
Verifies:
  1. Root HTML and static asset serving
  2. Execution and run lifecycle
  3. Dashboard overview contract & KPIs
  4. Enriched latest results contract
  5. Detailed invoice investigation dossier contract
  6. Historical, financial, and anomaly intelligence contracts
  7. Error handling & 404s for invalid invoice IDs
"""

import unittest
from fastapi.testclient import TestClient

from ui.app import app


class TestUIEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.client.headers.update({"X-API-Key": "key-admin-123"})
        # Trigger an agent run once for the test suite
        r = cls.client.post("/api/run")
        assert r.status_code == 200, f"Setup run failed: {r.status_code}"

    def test_01_health_and_root_html(self):
        """Test /api/health and / root HTML response."""
        r_health = self.client.get("/api/health")
        self.assertEqual(r_health.status_code, 200)
        self.assertIn(r_health.json()["status"], ["UP", "ok", "healthy", "HEALTHY"])

        r_root = self.client.get("/")
        self.assertEqual(r_root.status_code, 200)
        self.assertIn("UC15 GST Compliance Investigation Platform", r_root.text)
        self.assertIn("Invoice Audit Center", r_root.text)
        self.assertIn("Executive Overview", r_root.text)

    def test_02_static_assets_serving(self):
        """Verify CSS and JS static assets are served properly."""
        r_css = self.client.get("/static/css/investigation_ui.css")
        self.assertEqual(r_css.status_code, 200)
        self.assertIn("--blue-800", r_css.text)

        r_api = self.client.get("/static/js/api.js")
        self.assertEqual(r_api.status_code, 200)
        self.assertIn("class GSTApiClient", r_api.text)

        r_charts = self.client.get("/static/js/charts.js")
        self.assertEqual(r_charts.status_code, 200)
        self.assertIn("class GSTCharts", r_charts.text)

    def test_03_dashboard_overview_kpis(self):
        """Verify /api/dashboard/overview returns all 8 separate KPI dimensions."""
        resp = self.client.get("/api/dashboard/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("kpis", data)
        kpis = data["kpis"]
        self.assertIn("total_invoices", kpis)
        self.assertIn("compliant", kpis)
        self.assertIn("needs_review", kpis)
        self.assertIn("non_compliant", kpis)
        self.assertIn("high_critical_risk", kpis)
        self.assertIn("potential_exposure", kpis)
        self.assertIn("duplicate_findings", kpis)
        self.assertIn("anomaly_findings", kpis)

        self.assertGreater(kpis["total_invoices"], 0)
        self.assertGreater(kpis["potential_exposure"], 0)
        self.assertIn("gate_failures", data)
        self.assertIn("investigation", data)

    def test_04_enriched_latest_results(self):
        """Verify /api/results/latest includes enriched fields without breaking existing fields."""
        resp = self.client.get("/api/results/latest")
        self.assertEqual(resp.status_code, 200)
        invoices = resp.json()
        self.assertGreater(len(invoices), 0)

        first = invoices[0]
        # Core fields
        self.assertIn("invoice_no", first)
        self.assertIn("status", first)
        self.assertIn("gates", first)
        self.assertIn("risk_score", first)

        # Enriched Sprint 10 fields
        self.assertIn("potential_exposure", first)
        self.assertIn("impact_status", first)
        self.assertIn("has_duplicate", first)
        self.assertIn("has_anomaly", first)
        self.assertIn("failed_gate_names", first)

    def test_05_invoice_investigation_dossier(self):
        """Verify /api/investigation/invoice/{id} returns comprehensive 11-part dossier."""
        resp_latest = self.client.get("/api/results/latest")
        invoices = resp_latest.json()
        target_inv = invoices[0]["invoice_no"] if invoices else "INV-2026-POS-06"
        resp = self.client.get(f"/api/investigation/invoice/{target_inv}")
        self.assertEqual(resp.status_code, 200)
        dossier = resp.json()

        self.assertEqual(dossier["invoice_no"], target_inv)
        self.assertIsNotNone(dossier["decision"])
        self.assertIsNotNone(dossier["canonical"])

        # Financial impact
        self.assertIsNotNone(dossier["financial_impact"])

        # Timeline and recommendations
        self.assertIn("timeline", dossier)
        self.assertIn("recommended_actions", dossier)

    def test_06_invoice_dossier_404(self):
        """Verify /api/investigation/invoice/NONEXISTENT returns 404."""
        resp = self.client.get("/api/investigation/invoice/NONEXISTENT-999")
        self.assertEqual(resp.status_code, 404)

    def test_07_intelligence_endpoints(self):
        """Verify intelligence summary, duplicates, and anomalies endpoints."""
        r_sum = self.client.get("/api/intelligence/summary")
        self.assertEqual(r_sum.status_code, 200)

        r_dup = self.client.get("/api/intelligence/duplicates")
        self.assertEqual(r_dup.status_code, 200)
        self.assertIn("candidate_count", r_dup.json())

        r_anom = self.client.get("/api/intelligence/anomalies")
        self.assertEqual(r_anom.status_code, 200)
        anom_data = r_anom.json()
        self.assertIn("finding_count", anom_data)
        self.assertIn("by_dimension", anom_data)
        self.assertIn("by_level", anom_data)

    def test_08_investigation_profile_endpoints(self):
        """Verify investigation summary and candidate endpoints."""
        r_sum = self.client.get("/api/investigation/summary")
        self.assertEqual(r_sum.status_code, 200)
        self.assertIn("primary_root_cause", r_sum.json())

        r_rcs = self.client.get("/api/investigation/root-causes")
        self.assertEqual(r_rcs.status_code, 200)
        self.assertIn("candidates", r_rcs.json())


if __name__ == "__main__":
    unittest.main()
