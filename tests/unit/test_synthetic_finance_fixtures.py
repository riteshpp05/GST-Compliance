"""
Unit test suite for Synthetic Finance Test Fixtures (Invoices 1 to 20).
Verifies structural validity, model initialization, and scenario parameters.
"""
import unittest

from tests.fixtures.synthetic_finance_fixtures import get_synthetic_finance_fixtures


class TestSyntheticFinanceFixtures(unittest.TestCase):

    def test_fixture_count_and_uniqueness(self):
        fixtures = get_synthetic_finance_fixtures()
        self.assertEqual(len(fixtures), 20)

        inv_ids = [inv.invoice_id for inv in fixtures]
        self.assertEqual(len(inv_ids), 20)

    def test_invoice_1_normal_compliant(self):
        fixtures = get_synthetic_finance_fixtures()
        inv1 = fixtures[0]
        self.assertEqual(inv1.invoice_number, "INV-FIN-001")
        self.assertEqual(inv1.hsn_sac, "84713010")
        self.assertEqual(inv1.total_amount, 118000.00)

    def test_invoice_3_wrong_sap_tax_code(self):
        fixtures = get_synthetic_finance_fixtures()
        inv3 = fixtures[2]
        self.assertEqual(inv3.invoice_number, "INV-FIN-003")
        self.assertEqual(inv3.sap_tax_code, "V1")

    def test_invoice_8_rcm_transaction(self):
        fixtures = get_synthetic_finance_fixtures()
        inv8 = fixtures[7]
        self.assertEqual(inv8.invoice_number, "INV-FIN-008")
        self.assertTrue(inv8.is_rcm)
        self.assertEqual(inv8.hsn_sac, "9965")

    def test_invoice_10_unpaid_180_days(self):
        fixtures = get_synthetic_finance_fixtures()
        inv10 = fixtures[9]
        self.assertEqual(inv10.invoice_number, "INV-FIN-010")
        self.assertEqual(inv10.payment_status, "OVERDUE_180")
        self.assertEqual(inv10.itc_reversal_amount, 18000.00)
        self.assertGreater(inv10.interest_amount, 0)
