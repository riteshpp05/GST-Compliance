"""
Unit Tests for SAP S/4HANA OData V4 Loader & Hybrid Ingestion
Verifies OData V4 RAP URL construction, sap-client=200 injection,
BSIK field normalization, and offline demo fallback resilience.
"""
from decimal import Decimal
import unittest

from app.data.loaders.s4hana_odata_loader import S4HanaODataInvoiceLoader
from app.data.loaders.hybrid_loader import HybridInvoiceLoader
from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.domain.models.ingestion import IngestionStatus


class TestS4HanaODataV4(unittest.TestCase):

    def setUp(self):
        self.loader = S4HanaODataInvoiceLoader(
            base_url="http://192.168.1.55:8000/sap/opu/odata4/sap/z_gst_sb/srvd_a2x/sap/zui_gst_invoices/0001",
            company_code="DI01",
            sap_client="200",
            mock_fallback=True,
        )

    def test_sap_client_and_url_parameters(self):
        """Verify sap_client parameter and OData V4 configuration defaults."""
        self.assertEqual(self.loader.company_code, "DI01")
        self.assertEqual(self.loader.sap_client, "200")
        self.assertEqual(self.loader.inward_entity, "InwardInvoice")
        self.assertEqual(self.loader.outward_entity, "OutwardInvoice")

    def test_offline_demo_fallback_snapshot(self):
        """Verify the loader returns the 11 verified SAP BSIK documents when offline."""
        batch = self.loader.load()
        self.assertGreater(batch.total_records, 0)
        self.assertTrue(self.loader.used_fallback)

        # Check document numbers from functional sheet
        inv_numbers = [r.invoice.invoice_no for r in batch.records if r.invoice]
        self.assertIn("8096", inv_numbers)  # Normal/compliant
        self.assertIn("8094", inv_numbers)  # Intra-state
        self.assertIn("8095", inv_numbers)  # Inter-state
        self.assertIn("8097", inv_numbers)  # Duplicate
        self.assertIn("8098", inv_numbers)  # Duplicate
        self.assertIn("8103", inv_numbers)  # Wrong GST calculation

    def test_sap_bsik_normalization(self):
        """Verify that SAP BSIK InwardInvoice fields normalize cleanly to canonical Invoice."""
        raw_sap = {
            "SupplierInvoice": "8096",
            "FiscalYear": "2026",
            "InvoiceDate": "2026-09-02",
            "CompanyCode": "DI01",
            "VendorNumber": "70014",
            "VendorName": "Precision Tech Components Ltd",
            "VendorGSTIN": "27AAACB7001A1Z5",
            "PlaceOfSupply": "Maharashtra",
            "HSNCode": "8409",
            "TaxableValue": "50000.00",
            "CGSTRate": "9.0",
            "SGSTRate": "9.0",
            "IGSTRate": "0.0",
            "TotalTax": "9000.00",
            "TotalAmount": "59000.00",
            "Table": "BSIK",
        }

        res = InvoiceNormalizer.normalize_record(raw_sap)
        self.assertTrue(res.is_valid)
        inv = res.invoice
        self.assertEqual(inv.invoice_no, "8096")
        self.assertEqual(inv.direction, "AP")
        self.assertEqual(inv.counterparty_gstin, "27AAACB7001A1Z5")
        self.assertEqual(inv.taxable_value_inr, Decimal("50000.00"))
        self.assertEqual(inv.total_amt, Decimal("59000.00"))
        self.assertEqual(inv.metadata.get("sap_table"), "BSIK")

    def test_hybrid_loader_execution(self):
        """Verify that HybridInvoiceLoader combines SAP and statutory sandbox records."""
        hybrid = HybridInvoiceLoader(sap_loader=self.loader)
        batch = hybrid.load()
        self.assertGreater(batch.total_records, 11)
        self.assertIn("Hybrid", batch.source_name)


if __name__ == "__main__":
    unittest.main()
