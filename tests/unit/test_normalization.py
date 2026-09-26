"""
Unit tests for UC15 Invoice Normalization.
Tests field cleaning, type conversions, date normalization, null representations, and error handling.
"""
import datetime
from decimal import Decimal
import unittest

from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.domain.exceptions import NormalizationError


class TestInvoiceNormalizer(unittest.TestCase):

    def test_clean_str_null_representations(self):
        for null_val in [None, "", "   ", "N/A", "null", "None", "NaN", "-"]:
            self.assertEqual(InvoiceNormalizer.clean_str(null_val, default="DEF"), "DEF")
        self.assertEqual(InvoiceNormalizer.clean_str("  Valid Text  "), "Valid Text")

    def test_clean_decimal(self):
        self.assertEqual(InvoiceNormalizer.clean_decimal("50,000.50"), Decimal("50000.50"))
        self.assertEqual(InvoiceNormalizer.clean_decimal(12500), Decimal("12500"))
        self.assertEqual(InvoiceNormalizer.clean_decimal(None, default="0.00"), Decimal("0.00"))
        self.assertEqual(InvoiceNormalizer.clean_decimal("invalid-num", default="10.00"), Decimal("10.00"))

    def test_clean_date(self):
        today_iso = datetime.date.today().isoformat()
        self.assertEqual(InvoiceNormalizer.clean_date(None), today_iso)
        self.assertEqual(InvoiceNormalizer.clean_date("2026-03-15"), "2026-03-15")
        self.assertEqual(InvoiceNormalizer.clean_date("15-03-2026"), "2026-03-15")
        self.assertEqual(InvoiceNormalizer.clean_date("15/03/2026"), "2026-03-15")
        dt = datetime.datetime(2026, 4, 1, 10, 30)
        self.assertEqual(InvoiceNormalizer.clean_date(dt), "2026-04-01")

    def test_clean_bool(self):
        self.assertTrue(InvoiceNormalizer.clean_bool("YES"))
        self.assertTrue(InvoiceNormalizer.clean_bool("true"))
        self.assertTrue(InvoiceNormalizer.clean_bool(1))
        self.assertFalse(InvoiceNormalizer.clean_bool("NO"))
        self.assertFalse(InvoiceNormalizer.clean_bool("false"))
        self.assertFalse(InvoiceNormalizer.clean_bool(0))

    def test_normalize_valid_dict(self):
        raw = {
            "invoice_no": "  INV-NORM-01  ",
            "invoice_date": "10-02-2026",
            "direction": "ar",
            "counterparty_gstin": "27AAACB1234A1Z5",
            "counterparty_name": " Acme Corp ",
            "place_of_supply": "Maharashtra",
            "hsn_code": "8409",
            "item_desc": "Engines",
            "taxable_value_inr": "25,000.00",
            "cgst_rate": "9.0",
            "sgst_rate": "9.0",
            "igst_rate": "0.0",
            "total_amt": "29,500.00",
            "eway_bill_status": "none",
            "gstr2b_reflected": "yes",
        }
        inv = InvoiceNormalizer.normalize_dict(raw)
        self.assertEqual(inv.invoice_number, "INV-NORM-01")
        self.assertEqual(str(inv.invoice_date), "2026-02-10")
        self.assertEqual(inv.direction, "AR")
        self.assertEqual(inv.taxable_value, Decimal("25000.00"))
        self.assertEqual(inv.total_amount, Decimal("29500.00"))
        self.assertIn(inv.eway_bill, ("", "NOT_REQUIRED"))  # Raw status 'none' normalizes to '' (G5 engine computes requirement)
        self.assertTrue(inv.gstr2b_reflected)

    def test_normalize_tuple_row(self):
        row = (
            "INV-ROW-01", "2026-01-10", "AP", "29AAACM2345D1Z7", "Supplier Bangalore",
            "Karnataka", "8483", "Shafts", 88000.0, 0.0, 0.0, 18.0, 103840.0,
            "GENERATED", "YES"
        )
        inv = InvoiceNormalizer.normalize_row_tuple(row)
        self.assertEqual(inv.invoice_number, "INV-ROW-01")
        self.assertEqual(inv.direction, "AP")
        self.assertEqual(inv.taxable_value, Decimal("88000.0"))
        self.assertEqual(inv.eway_bill_status, "GENERATED")
        self.assertTrue(inv.gstr2b_reflected)

    def test_missing_invoice_id_raises_normalization_error(self):
        with self.assertRaises(NormalizationError):
            InvoiceNormalizer.normalize_dict({"invoice_no": ""})


if __name__ == "__main__":
    unittest.main()
