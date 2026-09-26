"""
Unit tests for Rule Engine 2.0 capabilities:
Dynamic rule toggling, rule versions, structured evidence, and DATA_001-DATA_005 rules.
"""
from decimal import Decimal
import unittest

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.validation_status import ValidationStatus
from app.rules.data_quality import (
    CounterpartyInfoRule,
    MandatoryInvoiceIdRule,
    NonNegativeTaxableValueRule,
    NumericTaxRateRule,
    ValidInvoiceDateRule,
)
from app.rules.existing.gstin import GSTINFormatRule
from app.rules.existing.hsn import HSNValidityRule
from app.rules.existing.tax import TaxRateCorrectnessRule
from app.rules.existing.pos import PlaceOfSupplyRule
from app.rules.existing.eway import EWayBillComplianceRule
from app.rules.existing.itc import ITCEligibilityRule
from app.rules.registry import RuleRegistry, create_default_registry
from tests.fixtures.sample_invoices import make_test_context, make_test_invoice


class TestRuleEngineV2(unittest.TestCase):

    def setUp(self):
        self.context = make_test_context()

    def test_all_rules_have_version_2_0(self):
        reg = create_default_registry()
        for rule in reg.all():
            self.assertEqual(rule.version, "2.0", f"Rule {rule.rule_id} missing version 2.0")

    def test_dynamic_enable_disable_in_registry(self):
        reg = create_default_registry()
        initial_enabled = len(reg.enabled())

        # Disable Gate 5
        self.assertTrue(reg.disable("EWB_001"))
        self.assertEqual(len(reg.enabled()), initial_enabled - 1)
        self.assertNotIn("EWB_001", [r.rule_id for r in reg.enabled()])

        # Re-enable Gate 5
        self.assertTrue(reg.enable("EWB_001"))
        self.assertEqual(len(reg.enabled()), initial_enabled)
        self.assertIn("EWB_001", [r.rule_id for r in reg.enabled()])

    def test_all_six_gates_produce_structured_evidence(self):
        inv = make_test_invoice(
            taxable_value=85000.0,
            eway_bill="GENERATED",
            direction="AP",
            gstr2b_reflected=True,
        )

        r1 = GSTINFormatRule().validate(inv, self.context)
        r2 = HSNValidityRule().validate(inv, self.context)
        r3 = TaxRateCorrectnessRule().validate(inv, self.context)
        r4 = PlaceOfSupplyRule().validate(inv, self.context)
        r5 = EWayBillComplianceRule().validate(inv, self.context)
        r6 = ITCEligibilityRule().validate(inv, self.context)

        for r in [r1, r2, r3, r4, r5, r6]:
            self.assertIsNotNone(r.evidence, f"Rule {r.rule_id} missing evidence")
            self.assertIsInstance(r.evidence, dict)
            self.assertEqual(r.rule_version, "2.0")

    # -- Data Quality Rules Tests (DATA_001 to DATA_005) -----------------------

    def test_data_001_mandatory_invoice_id(self):
        rule = MandatoryInvoiceIdRule()
        inv_good = make_test_invoice(invoice_no="INV-100")
        inv_bad = make_test_invoice(invoice_no="   ")

        self.assertEqual(rule.validate(inv_good).status, ValidationStatus.PASS.value)
        self.assertEqual(rule.validate(inv_bad).status, ValidationStatus.FAIL.value)

    def test_data_002_valid_invoice_date(self):
        rule = ValidInvoiceDateRule()
        inv_good = make_test_invoice(invoice_date="2026-03-01")
        inv_bad_fmt = make_test_invoice(invoice_date="unparseable-date")
        inv_out_of_bounds = make_test_invoice(invoice_date="1980-01-01")

        self.assertEqual(rule.validate(inv_good).status, ValidationStatus.PASS.value)
        self.assertEqual(rule.validate(inv_bad_fmt).status, ValidationStatus.FAIL.value)
        self.assertEqual(rule.validate(inv_out_of_bounds).status, ValidationStatus.FAIL.value)

    def test_data_003_non_negative_taxable_value(self):
        rule = NonNegativeTaxableValueRule()
        inv_good = make_test_invoice(taxable_value=1000.0)
        inv_neg = make_test_invoice()
        inv_neg.taxable_value = Decimal("-500.00")

        self.assertEqual(rule.validate(inv_good).status, ValidationStatus.PASS.value)
        self.assertEqual(rule.validate(inv_neg).status, ValidationStatus.FAIL.value)

    def test_data_004_numeric_tax_rate_bounds(self):
        rule = NumericTaxRateRule()
        inv_good = make_test_invoice(cgst_rate=9, sgst_rate=9, igst_rate=0)
        inv_bad = make_test_invoice(cgst_rate=75.0)  # Exceeds 50%

        self.assertEqual(rule.validate(inv_good).status, ValidationStatus.PASS.value)
        self.assertEqual(rule.validate(inv_bad).status, ValidationStatus.FAIL.value)

    def test_data_005_counterparty_info(self):
        rule = CounterpartyInfoRule()
        inv_good = make_test_invoice(counterparty_name="Bosch India", place_of_supply="Maharashtra")
        inv_bad = make_test_invoice(counterparty_name="", place_of_supply="")

        self.assertEqual(rule.validate(inv_good).status, ValidationStatus.PASS.value)
        self.assertEqual(rule.validate(inv_bad).status, ValidationStatus.WARNING.value)


if __name__ == "__main__":
    unittest.main()
