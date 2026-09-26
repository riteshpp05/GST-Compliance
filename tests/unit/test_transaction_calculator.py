import unittest
from decimal import Decimal

from app.domain.services.transaction_calculator import (
    compute_canonical_financials,
    sanitize_eway_bill_status,
)


class TestTransactionCalculator(unittest.TestCase):
    def test_compute_canonical_financials_intra_state(self):
        # Taxable Value = 40,000, CGST = 9%, SGST = 9% (3600 + 3600 = 7200 tax)
        fin = compute_canonical_financials(
            taxable_value=40000,
            cgst_rate=9,
            sgst_rate=9,
            igst_rate=0,
        )
        self.assertEqual(fin["taxable_value"], Decimal("40000.00"))
        self.assertEqual(fin["cgst_amount"], Decimal("3600.00"))
        self.assertEqual(fin["sgst_amount"], Decimal("3600.00"))
        self.assertEqual(fin["total_tax"], Decimal("7200.00"))
        self.assertEqual(fin["invoice_total"], Decimal("47200.00"))
        self.assertEqual(fin["effective_tax_rate"], Decimal("18.00"))

    def test_compute_canonical_financials_inter_state(self):
        # Taxable Value = 55,000, IGST = 18% (9900 tax)
        fin = compute_canonical_financials(
            taxable_value=55000,
            cgst_rate=0,
            sgst_rate=0,
            igst_rate=18,
        )
        self.assertEqual(fin["taxable_value"], Decimal("55000.00"))
        self.assertEqual(fin["igst_amount"], Decimal("9900.00"))
        self.assertEqual(fin["total_tax"], Decimal("9900.00"))
        self.assertEqual(fin["invoice_total"], Decimal("64900.00"))
        self.assertEqual(fin["effective_tax_rate"], Decimal("18.00"))

    def test_compute_canonical_financials_prevents_negative_tax_when_passed_tax_in_place_of_total(self):
        # Taxable Value = 55,000, but total_amount passed was 9,900 (tax amount)
        fin = compute_canonical_financials(
            taxable_value=55000,
            igst_rate=18,
            total_amount=9900,
        )
        self.assertEqual(fin["total_tax"], Decimal("9900.00"))
        self.assertEqual(fin["invoice_total"], Decimal("64900.00"))
        self.assertEqual(fin["effective_tax_rate"], Decimal("18.00"))

    def test_sanitize_eway_bill_status_numeric_leaks(self):
        # Numeric leaked totals like "64900" or "47200" must be sanitized
        status1 = sanitize_eway_bill_status("64900", taxable_value=Decimal("55000.00"))
        self.assertEqual(status1, "UNKNOWN")

        status2 = sanitize_eway_bill_status("47200", taxable_value=Decimal("40000.00"))
        self.assertEqual(status2, "UNKNOWN")

        status3 = sanitize_eway_bill_status("GENERATED", taxable_value=Decimal("55000.00"))
        self.assertEqual(status3, "GENERATED")


if __name__ == "__main__":
    unittest.main()

