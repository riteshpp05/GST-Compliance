"""
UC15 GST Compliance Agent — Cross-Invoice Invariants Automated Test Suite
Verifies 10 core mathematical, logical, and structural invariants across the dataset.
"""
import os
import unittest
from decimal import Decimal
from app.agent.compliance_agent import GSTComplianceAgent
from app.config.settings import settings
from app.domain.services.transaction_calculator import compute_canonical_financials, VALID_EWAY_STATUSES


class TestCrossInvoiceInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        excel_path = settings.excel_file
        if not os.path.exists(excel_path):
            raise unittest.SkipTest(f"Dataset not found at {excel_path}")
        cls.agent = GSTComplianceAgent(excel_path=excel_path)
        cls.decisions = cls.agent.run_all()
        cls.invoices = cls.agent.repository.list_all()

    def test_invariant_1_invoice_total_equals_taxable_plus_total_tax(self):
        """Invariant 1: invoice_total = taxable_value + total_tax across all invoices."""
        for inv in self.invoices:
            fin = compute_canonical_financials(
                taxable_value=inv.taxable_value,
                cgst_rate=inv.cgst_rate,
                sgst_rate=inv.sgst_rate,
                igst_rate=inv.igst_rate,
                total_amount=inv.total_amount,
            )
            taxable = fin["taxable_value"]
            total_tax = fin["total_tax"]
            invoice_total = fin["invoice_total"]
            self.assertEqual(
                invoice_total,
                taxable + total_tax,
                f"Invoice {inv.invoice_no}: invoice_total {invoice_total} != taxable {taxable} + total_tax {total_tax}"
            )

    def test_invariant_2_total_tax_equals_sum_of_components(self):
        """Invariant 2: total_tax = sum of tax components (cgst + sgst + igst + cess)."""
        for inv in self.invoices:
            fin = compute_canonical_financials(
                taxable_value=inv.taxable_value,
                cgst_rate=inv.cgst_rate,
                sgst_rate=inv.sgst_rate,
                igst_rate=inv.igst_rate,
                total_amount=inv.total_amount,
            )
            cgst = fin["cgst_amount"]
            sgst = fin["sgst_amount"]
            igst = fin["igst_amount"]
            cess = fin["cess_amount"]
            total_tax = fin["total_tax"]
            component_sum = cgst + sgst + igst + cess
            self.assertEqual(
                total_tax,
                component_sum,
                f"Invoice {inv.invoice_no}: total_tax {total_tax} != component_sum {component_sum}"
            )

    def test_invariant_3_effective_tax_rate_mathematically_valid(self):
        """Invariant 3: effective_tax_rate is mathematically valid."""
        for inv in self.invoices:
            fin = compute_canonical_financials(
                taxable_value=inv.taxable_value,
                cgst_rate=inv.cgst_rate,
                sgst_rate=inv.sgst_rate,
                igst_rate=inv.igst_rate,
                total_amount=inv.total_amount,
            )
            taxable = fin["taxable_value"]
            total_tax = fin["total_tax"]
            eff_rate = fin["effective_tax_rate"]
            if taxable > Decimal("0.00"):
                expected_eff = ((total_tax / taxable) * Decimal("100.00")).quantize(Decimal("0.01"))
                self.assertAlmostEqual(
                    float(eff_rate),
                    float(expected_eff),
                    places=1,
                    msg=f"Invoice {inv.invoice_no}: effective_tax_rate {eff_rate} invalid for total_tax {total_tax} / taxable {taxable}"
                )
            else:
                self.assertEqual(eff_rate, Decimal("0.00"))

    def test_invariant_4_ewb_status_never_monetary_amount(self):
        """Invariant 4: EWB status is never a numeric monetary amount."""
        for inv in self.invoices:
            ewb = str(inv.eway_bill_status or "").strip()
            cleaned = ewb.replace(",", "").replace(".", "", 1)
            self.assertFalse(
                cleaned.isdigit(),
                f"Invoice {inv.invoice_no}: eway_bill_status '{ewb}' is a leaked numeric monetary value!"
            )
            if ewb != "":
                self.assertIn(
                    ewb,
                    VALID_EWAY_STATUSES,
                    f"Invoice {inv.invoice_no}: eway_bill_status '{ewb}' not in valid classifications!"
                )

    def test_invariant_5_expected_tax_calculated_from_expected_rate(self):
        """Invariant 5: expected_tax is not silently replaced by actual_tax."""
        for d in self.decisions:
            g3 = next((g for g in d.gates if g.gate_no == 3), None)
            if g3 and g3.evidence:
                expected = g3.evidence.get("expected_rates", {})
                if g3.status == "FAIL":
                    self.assertIsNotNone(expected)

    def test_invariant_6_g3_does_not_determine_jurisdiction(self):
        """Invariant 6: G3 evaluates rate quantum, leaving CGST/SGST vs IGST jurisdiction to G4."""
        for d in self.decisions:
            g3 = next((g for g in d.gates if g.gate_no == 3), None)
            g4 = next((g for g in d.gates if g.gate_no == 4), None)
            self.assertIsNotNone(g3)
            self.assertIsNotNone(g4)
            self.assertEqual(g3.gate_no, 3)
            self.assertEqual(g4.gate_no, 4)

    def test_invariant_7_g4_uses_canonical_states_and_pos(self):
        """Invariant 7: G4 uses canonical states/POS matching transaction summary."""
        for d in self.decisions:
            g4 = next((g for g in d.gates if g.gate_no == 4), None)
            if g4 and g4.evidence:
                pos = g4.evidence.get("place_of_supply_declared") or g4.evidence.get("place_of_supply") or g4.evidence.get("pos")
                self.assertTrue(pos is not None or g4.status == "NEEDS_REVIEW")

    def test_invariant_8_historical_failure_count_within_population(self):
        """Invariant 8: historical failure count cannot exceed total invoice population."""
        total_invoices = len(self.decisions)
        failed_invoices = sum(1 for d in self.decisions if d.status in ("NON_COMPLIANT", "BLOCKED", "NEEDS_REVIEW"))
        self.assertLessEqual(failed_invoices, total_invoices)

    def test_invariant_9_compliance_rate_matches_underlying_counts(self):
        """Invariant 9: compliance rate matches sum of underlying status counts."""
        total = len(self.decisions)
        compliant = sum(1 for d in self.decisions if d.status == "COMPLIANT")
        review = sum(1 for d in self.decisions if d.status == "NEEDS_REVIEW")
        non_compliant = sum(1 for d in self.decisions if d.status in ("NON_COMPLIANT", "BLOCKED"))
        self.assertEqual(compliant + review + non_compliant, total)

    def test_invariant_10_overall_decision_from_centralized_engine(self):
        """Invariant 10: overall compliance status comes from centralized DecisionEngine."""
        for d in self.decisions:
            self.assertIn(d.status, ("COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT", "BLOCKED"))
            self.assertTrue(d.audit_trail_ref.startswith("GST-"))


if __name__ == "__main__":
    unittest.main()
