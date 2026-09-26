"""
UC15 GST Compliance Agent — Sprint 22 Reconciliation Unit Tests
Verifies 4-way record reconciliation and contradiction detection across evidence signals.
"""
import unittest

from app.domain.models.invoice import Invoice
from app.reconciliation.contradiction_detector import ContradictionDetector
from app.reconciliation.engine import ReconciliationEngine
from app.reconciliation.models import ReconciliationStatus, ContradictionSeverity


class TestS22Reconciliation(unittest.TestCase):

    def setUp(self):
        self.detector = ContradictionDetector()
        self.engine = ReconciliationEngine(contradiction_detector=self.detector)

    def test_pos_tax_head_contradiction_detection(self):
        inv = Invoice.from_record(
            invoice_no="INV-POS-TEST",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="MH Vendor Ltd",
            place_of_supply="29",
            hsn_code="8471",
            item_desc="Laptops",
            taxable_value_inr=10000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=11800.0,
        )
        inv.seller_gstin = "27AAACB1234C1Z1"
        inv.buyer_gstin = "29BBBCB5678D1Z2"

        contradictions = self.detector.detect_contradictions(invoice=inv)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0].contradiction_type, "POS_TAX_HEAD_CONTRADICTION")
        self.assertEqual(contradictions[0].severity, ContradictionSeverity.CRITICAL)

    def test_cancelled_supplier_contradiction_detection(self):
        inv = Invoice.from_record(
            invoice_no="INV-CANCELLED-TEST",
            invoice_date="2026-03-15",
            direction="AP",
            counterparty_gstin="27DEFGB9999C1Z9",
            counterparty_name="Defunct Traders",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Services",
            taxable_value_inr=50000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=59000.0,
            irn="1234567890abcdef",
        )
        supplier_master = {"status": "CANCELLED", "cancellation_date": "2024-01-15"}

        contradictions = self.detector.detect_contradictions(invoice=inv, supplier_master=supplier_master)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0].contradiction_type, "CANCELLED_SUPPLIER_ACTIVE_IRN_CONTRADICTION")

    def test_erp_paid_gstr2b_missing_contradiction_detection(self):
        inv = Invoice.from_record(
            invoice_no="INV-ERP-TEST",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Unresponsive Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Parts",
            taxable_value_inr=20000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=23600.0,
            gstr2b_reflected=False,
        )
        inv.metadata["is_paid"] = True
        inv.gstr2b_reflected = False

        contradictions = self.detector.detect_contradictions(invoice=inv, gstr2b_record=None)
        self.assertEqual(len(contradictions), 1)
        self.assertEqual(contradictions[0].contradiction_type, "ERP_PAID_GSTR2B_MISSING_CONTRADICTION")

    def test_reconciliation_engine_match(self):
        inv = Invoice.from_record(
            invoice_no="INV-MATCH-TEST",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Compliant Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Goods",
            taxable_value_inr=100000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=118000.0,
            gstr2b_reflected=True,
        )
        inv.gstr2b_reflected = True
        supplier_master = {"status": "ACTIVE"}

        result = self.engine.reconcile(
            case_id="CASE-MATCH",
            invoice=inv,
            supplier_master=supplier_master,
        )

        self.assertEqual(result.overall_status, ReconciliationStatus.MATCH)
        self.assertEqual(len(result.contradictions), 0)
        self.assertTrue(len(result.pairs) >= 3)


if __name__ == "__main__":
    unittest.main()
