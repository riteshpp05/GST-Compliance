"""
Unit tests for UC15 Compliance Rules and Rule Registry.
Covers positive and negative test cases for each of the six migrated rules.
"""
import unittest

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.rules.existing.gstin import GSTINFormatRule
from app.rules.existing.hsn import HSNValidityRule
from app.rules.existing.tax import TaxRateCorrectnessRule
from app.rules.existing.pos import PlaceOfSupplyRule
from app.rules.existing.eway import EWayBillComplianceRule
from app.rules.existing.itc import ITCEligibilityRule
from app.rules.registry import RuleRegistry, create_default_registry
from tests.fixtures.sample_invoices import make_test_context, make_test_invoice


class TestComplianceRulesAndRegistry(unittest.TestCase):

    def setUp(self):
        self.context = make_test_context()

    # -- Registry Tests --------------------------------------------------------

    def test_registry_registration_and_retrieval(self):
        reg = RuleRegistry()
        rule = GSTINFormatRule()
        reg.register(rule)

        self.assertEqual(len(reg), 1)
        self.assertEqual(reg.get("GSTIN_001"), rule)
        self.assertIsNone(reg.get("NON_EXISTENT"))

    def test_default_registry_contains_all_six_rules(self):
        reg = create_default_registry()
        self.assertEqual(len(reg.all()), 6)
        self.assertEqual(len(reg.enabled()), 6)

        expected_ids = {"GSTIN_001", "HSN_001", "TAX_001", "POS_001", "EWB_001", "ITC_001"}
        registered_ids = {r.rule_id for r in reg.all()}
        self.assertEqual(expected_ids, registered_ids)

    def test_registry_filter_by_category(self):
        reg = create_default_registry()
        master_data_rules = reg.by_category(RuleCategory.MASTER_DATA)
        self.assertEqual(len(master_data_rules), 1)
        self.assertEqual(master_data_rules[0].rule_id, "GSTIN_001")

    # -- Gate 1: GSTIN Format Rule ---------------------------------------------

    def test_gate1_gstin_valid(self):
        rule = GSTINFormatRule()
        inv = make_test_invoice(gstin="27AAACB1234A1Z5")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)
        self.assertEqual(result.gate_no, 1)

    def test_gate1_gstin_invalid(self):
        rule = GSTINFormatRule()
        inv = make_test_invoice(gstin="27INVALID123")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)
        self.assertEqual(result.severity, Severity.CRITICAL.value)

    # -- Gate 2: HSN Validity Rule ---------------------------------------------

    def test_gate2_hsn_valid(self):
        rule = HSNValidityRule()
        inv = make_test_invoice(hsn_code="8409")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)
        self.assertEqual(result.gate_no, 2)
        self.assertIn("Parts for Internal Combustion Engines", result.message)

    def test_gate2_hsn_invalid(self):
        rule = HSNValidityRule()
        inv = make_test_invoice(hsn_code="0000")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertEqual(result.severity, Severity.HIGH.value)

    # -- Gate 3: Tax Rate Correctness Rule -------------------------------------

    def test_gate3_tax_rate_valid_intra_state(self):
        rule = TaxRateCorrectnessRule()
        inv = make_test_invoice(hsn_code="8409", cgst_rate=9.0, sgst_rate=9.0, igst_rate=0.0)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate3_tax_rate_valid_inter_state(self):
        rule = TaxRateCorrectnessRule()
        inv = make_test_invoice(hsn_code="8409", cgst_rate=0.0, sgst_rate=0.0, igst_rate=18.0)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate3_tax_rate_mismatch_fails(self):
        rule = TaxRateCorrectnessRule()
        inv = make_test_invoice(hsn_code="8409", cgst_rate=12.0, sgst_rate=12.0, igst_rate=0.0)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)

    def test_gate3_missing_hsn_fails(self):
        rule = TaxRateCorrectnessRule()
        inv = make_test_invoice(hsn_code="9999")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.NEEDS_REVIEW.value)
        self.assertIn("Cannot verify rate", result.message)

    # -- Gate 4: Place of Supply Rule ------------------------------------------

    def test_gate4_intra_state_correct(self):
        rule = PlaceOfSupplyRule()
        # 27 = Maharashtra, POS = Maharashtra -> intra-state -> CGST+SGST
        inv = make_test_invoice(gstin="27AAACB1234A1Z5", place_of_supply="Maharashtra", cgst_rate=9, sgst_rate=9, igst_rate=0)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate4_intra_state_charged_as_igst_fails(self):
        rule = PlaceOfSupplyRule()
        inv = make_test_invoice(gstin="27AAACB1234A1Z5", place_of_supply="Maharashtra", cgst_rate=0, sgst_rate=0, igst_rate=18)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)

    def test_gate4_inter_state_correct(self):
        rule = PlaceOfSupplyRule()
        # 27 = Maharashtra, POS = Delhi -> inter-state -> IGST
        inv = make_test_invoice(gstin="27AAACB1234A1Z5", place_of_supply="Delhi", cgst_rate=0, sgst_rate=0, igst_rate=18)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate4_inter_state_charged_as_cgst_sgst_fails(self):
        rule = PlaceOfSupplyRule()
        inv = make_test_invoice(gstin="27AAACB1234A1Z5", place_of_supply="Delhi", cgst_rate=9, sgst_rate=9, igst_rate=0)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)

    # -- Gate 5: E-Way Bill Rule -----------------------------------------------

    def test_gate5_below_threshold_not_applicable(self):
        rule = EWayBillComplianceRule()
        inv = make_test_invoice(taxable_value=35000.0, eway_bill="")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.NOT_APPLICABLE.value)

    def test_gate5_above_threshold_generated_passes(self):
        rule = EWayBillComplianceRule()
        inv = make_test_invoice(taxable_value=75000.0, eway_bill="GENERATED")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate5_above_threshold_missing_fails(self):
        rule = EWayBillComplianceRule()
        inv = make_test_invoice(taxable_value=75000.0, eway_bill="PENDING")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)

    # -- Gate 6: ITC Eligibility Rule ------------------------------------------

    def test_gate6_ar_invoice_not_applicable(self):
        rule = ITCEligibilityRule()
        inv = make_test_invoice(direction="AR")
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.NOT_APPLICABLE.value)

    def test_gate6_ap_clean_passes(self):
        rule = ITCEligibilityRule()
        inv = make_test_invoice(direction="AP", item_desc="Industrial pump", gstr2b_reflected=True)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.PASS.value)

    def test_gate6_ap_blocked_category_fails(self):
        rule = ITCEligibilityRule()
        inv = make_test_invoice(direction="AP", item_desc="Employee welfare lunch catering", gstr2b_reflected=True)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)
        self.assertIn("Section 17(5)", result.message)

    def test_gate6_ap_not_reflected_in_gstr2b_fails(self):
        rule = ITCEligibilityRule()
        inv = make_test_invoice(direction="AP", item_desc="Raw steel bolts", gstr2b_reflected=False)
        result = rule.validate(inv, self.context)
        self.assertEqual(result.status, ValidationStatus.FAIL.value)
        self.assertIn("not reflected in GSTR-2B", result.message)


if __name__ == "__main__":
    unittest.main()
