"""
tests/unit/test_financial_impact.py
===================================
Comprehensive unit test suite for Sprint 6 — Financial Impact & Exposure Intelligence.
Validates:
- Strict Decimal precision and ROUND_HALF_UP rounding
- Exact tax difference and directional consequence (OVERCHARGED_TAX, UNDERCHARGED_TAX, NO_TAX_DIFFERENCE)
- Component-level tax difference calculations (CGST, SGST, IGST)
- ITC at-risk exposure on AP vs NOT_APPLICABLE on AR
- Deterministic UNDETERMINED evaluation for missing EWB and missing data
- Portfolio-wide aggregation and exclusion of UNDETERMINED from monetary exposure totals
- Counterparty, Rule, and Period aggregations & trends
- Deterministic ranking of top exposures
- Recommendation of Credit Notes, Debit Notes, and ITC Reversals
- FinancialService integration and FinancialReport generation
"""

import unittest
from datetime import date
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models import (
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    CalculationStatus,
    round_monetary,
    CounterpartyFinancialExposure,
    RuleFinancialExposure,
    PeriodFinancialExposure,
    PeriodExposureTrend,
    FinancialAdjustment,
    AggregateFinancialExposure,
    FinancialReport,
)
from app.financial.calculators.tax_difference import (
    TaxDifferenceCalculator,
    parse_tax_rate,
    parse_decimal_safe,
)
from app.financial.calculators.exposure_calculator import (
    InvoiceExposureCalculator,
)
from app.financial.calculators.aggregate_calculator import (
    AggregateCalculator,
)
from app.financial.repositories.in_memory import (
    InMemoryFinancialRepository,
)
from app.financial.services.financial_service import (
    FinancialService,
)


class TestTaxDifferenceCalculator(unittest.TestCase):
    """Test standalone tax difference and rate parsing calculations."""

    def setUp(self):
        self.calc = TaxDifferenceCalculator()

    def test_overcharged_tax_rate_18_vs_12(self):
        """18% recorded vs 12% statutory on 100,000 INR -> +6% difference, OVERCHARGED_TAX, 6,000.00 INR exposure."""
        res = self.calc.calculate_tax_difference(
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
        )
        self.assertEqual(res["calculation_status"], CalculationStatus.CALCULATED)
        self.assertEqual(res["direction"], ImpactDirection.OVERCHARGED_TAX)
        self.assertEqual(res["potential_exposure"], Decimal("6000.00"))
        self.assertEqual(res["rate_difference_pct"], Decimal("6.00"))
        self.assertEqual(res["recorded_tax_amount"], Decimal("18000.00"))
        self.assertEqual(res["expected_tax_amount"], Decimal("12000.00"))

    def test_undercharged_tax_rate_12_vs_18(self):
        """12% recorded vs 18% statutory on 100,000 INR -> -6% difference, UNDERCHARGED_TAX, 6,000.00 INR exposure."""
        res = self.calc.calculate_tax_difference(
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("12.00"),
            expected_rate=Decimal("18.00"),
        )
        self.assertEqual(res["calculation_status"], CalculationStatus.CALCULATED)
        self.assertEqual(res["direction"], ImpactDirection.UNDERCHARGED_TAX)
        self.assertEqual(res["potential_exposure"], Decimal("6000.00"))
        self.assertEqual(res["rate_difference_pct"], Decimal("-6.00"))
        self.assertEqual(res["recorded_tax_amount"], Decimal("12000.00"))
        self.assertEqual(res["expected_tax_amount"], Decimal("18000.00"))

    def test_exact_match_tax_rate_18_vs_18(self):
        """18% recorded vs 18% statutory on 100,000 INR -> 0% difference, NO_TAX_DIFFERENCE, 0.00 INR exposure."""
        res = self.calc.calculate_tax_difference(
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("18.00"),
        )
        self.assertEqual(res["calculation_status"], CalculationStatus.CALCULATED)
        self.assertEqual(res["direction"], ImpactDirection.NO_TAX_DIFFERENCE)
        self.assertEqual(res["potential_exposure"], Decimal("0.00"))
        self.assertEqual(res["rate_difference_pct"], Decimal("0.00"))

    def test_tax_difference_different_taxable_values(self):
        """Test with 50,000 INR and 10,000 INR taxable amounts."""
        # 50,000 at 18% vs 12% -> 3,000.00
        res1 = self.calc.calculate_tax_difference(
            taxable_value=Decimal("50000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
        )
        self.assertEqual(res1["potential_exposure"], Decimal("3000.00"))

        # 10,000 at 28% vs 18% -> 1,000.00
        res2 = self.calc.calculate_tax_difference(
            taxable_value=Decimal("10000.00"),
            recorded_rate=Decimal("28.00"),
            expected_rate=Decimal("18.00"),
        )
        self.assertEqual(res2["potential_exposure"], Decimal("1000.00"))

    def test_intra_state_component_splits(self):
        """Verify CGST and SGST component differences for intra-state supply."""
        res = self.calc.calculate_tax_difference(
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
            is_interstate=False,
        )
        components = res["components"]
        self.assertEqual(components["cgst_difference"], Decimal("3000.00"))
        self.assertEqual(components["sgst_difference"], Decimal("3000.00"))
        self.assertEqual(components["igst_difference"], Decimal("0.00"))
        self.assertEqual(
            components["cgst_difference"] + components["sgst_difference"],
            res["potential_exposure"],
        )

    def test_inter_state_component_splits(self):
        """Verify IGST component difference for inter-state supply."""
        res = self.calc.calculate_tax_difference(
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
            is_interstate=True,
        )
        components = res["components"]
        self.assertEqual(components["cgst_difference"], Decimal("0.00"))
        self.assertEqual(components["sgst_difference"], Decimal("0.00"))
        self.assertEqual(components["igst_difference"], Decimal("6000.00"))

    def test_missing_or_zero_taxable_value_yields_undetermined(self):
        """Missing or zero taxable value evaluates to UNDETERMINED."""
        res1 = self.calc.calculate_tax_difference(
            taxable_value=Decimal("0.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
        )
        self.assertEqual(res1["calculation_status"], CalculationStatus.UNDETERMINED)
        self.assertIn("taxable_value", res1["required_data"])

        res2 = self.calc.calculate_tax_difference(
            taxable_value=None,
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
        )
        self.assertEqual(res2["calculation_status"], CalculationStatus.UNDETERMINED)

    def test_parse_tax_rate_formats(self):
        """Handles numeric, string percentage, and dictionary formats safely."""
        self.assertEqual(parse_tax_rate(18), Decimal("18.00"))
        self.assertEqual(parse_tax_rate("18%"), Decimal("18.00"))
        self.assertEqual(parse_tax_rate(" 0.18 "), Decimal("18.00"))
        self.assertEqual(parse_tax_rate({"cgst": 9.0, "sgst": 9.0}), Decimal("18.00"))
        self.assertEqual(parse_tax_rate({"igst": 18.0}), Decimal("18.00"))
        self.assertIsNone(parse_tax_rate("invalid"))


class TestInvoiceExposureCalculator(unittest.TestCase):
    """Test invoice-level exposure calculator across various gates."""

    def setUp(self):
        self.calc = InvoiceExposureCalculator()

    def test_gate3_rate_mismatch_exposure(self):
        """Gate 3 rate mismatch produces CALCULATED impact with potential exposure."""
        g3_result = ValidationResult(
            gate_no=3,
            rule_id="RULE-GATE-3-TAX-RATE",
            rule_name="GST Rate Validation",
            status="FAIL",
            severity="HIGH",
            actual_value={"rate": 18.0},
            expected_value={"rate": 12.0},
            message="Rate mismatch: 18.0% recorded vs 12.0% expected",
        )
        decision = ComplianceDecision(
            invoice_no="INV-G3-001",
            invoice_date="2023-11-15",
            direction="AP",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Vendor A",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Laptop Computer",
            taxable_value_inr=100000.0,
            total_amt=118000.0,
            gates=[g3_result],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="Tax rate mismatch",
            recommended_action="Request credit note",
            sap_action="BLOCK_PAYMENT",
            audit_trail_ref="AUD-001",
            hard_override=False,
        )

        impacts = self.calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        imp = impacts[0]
        self.assertEqual(imp.invoice_id, "INV-G3-001")
        self.assertEqual(imp.calculation_status, CalculationStatus.CALCULATED)
        self.assertEqual(imp.impact_type, FinancialImpactType.TAX_RATE_DIFFERENCE)
        self.assertEqual(imp.direction, ImpactDirection.OVERCHARGED_TAX)
        self.assertEqual(imp.potential_exposure, Decimal("6000.00"))
        self.assertEqual(imp.taxable_value, Decimal("100000.00"))
        self.assertEqual(imp.counterparty_id, "27ABCDE1234F1Z5")

    def test_gate6_itc_blocked_category_ap_invoice(self):
        """Gate 6 ITC blocked category on AP invoice produces ITC_EXPOSURE with total tax as exposure."""
        g6_result = ValidationResult(
            gate_no=6,
            rule_id="RULE-GATE-6-ITC",
            rule_name="ITC Eligibility Validation",
            status="FAIL",
            severity="CRITICAL",
            actual_value="FOOD_AND_BEVERAGES",
            expected_value="ELIGIBLE",
            message="ITC blocked under Section 17(5) for food and beverages",
        )
        decision = ComplianceDecision(
            invoice_no="INV-G6-001",
            invoice_date="2023-11-20",
            direction="AP",
            counterparty_gstin="27AABCT1332L1ZV",
            counterparty_name="Catering Services",
            place_of_supply="27",
            hsn_code="996331",
            item_desc="Outdoor Catering",
            taxable_value_inr=50000.0,
            total_amt=52500.0,
            gates=[g6_result],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="ITC blocked",
            recommended_action="Do not claim ITC",
            sap_action="REVERSE_ITC",
            audit_trail_ref="AUD-002",
            hard_override=False,
        )

        impacts = self.calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        imp = impacts[0]
        self.assertEqual(imp.calculation_status, CalculationStatus.CALCULATED)
        self.assertEqual(imp.impact_type, FinancialImpactType.ITC_EXPOSURE)
        self.assertEqual(imp.potential_exposure, Decimal("2500.00"))
        self.assertEqual(imp.rule_id, "RULE-GATE-6-ITC")

    def test_gate6_itc_on_ar_invoice_is_not_applicable(self):
        """ITC is strictly not applicable on AR (sales) invoices."""
        g6_result = ValidationResult(
            gate_no=6,
            rule_id="RULE-GATE-6-ITC",
            rule_name="ITC Eligibility Validation",
            status="NOT_APPLICABLE",
            severity="LOW",
            message="ITC not applicable for outbound AR invoices",
        )
        decision = ComplianceDecision(
            invoice_no="INV-AR-001",
            invoice_date="2023-11-22",
            direction="AR",
            counterparty_gstin="29XYZAB1234M1Z8",
            counterparty_name="Customer Corp",
            place_of_supply="29",
            hsn_code="8471",
            item_desc="Laptops Outbound",
            taxable_value_inr=200000.0,
            total_amt=236000.0,
            gates=[g6_result],
            failed_gate_count=0,
            status="COMPLIANT",
            justification="Compliant AR",
            recommended_action="POST",
            sap_action="POST",
            audit_trail_ref="AUD-003",
            hard_override=False,
        )

        impacts = self.calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        imp = impacts[0]
        self.assertEqual(imp.calculation_status, CalculationStatus.NOT_APPLICABLE)
        self.assertEqual(imp.potential_exposure, Decimal("0.00"))

    def test_gate5_missing_ewb_yields_undetermined(self):
        """Missing E-Way Bill must evaluate to UNDETERMINED with no fabricated penalty."""
        g5_result = ValidationResult(
            gate_no=5,
            rule_id="RULE-GATE-5-EWAY",
            rule_name="E-Way Bill Requirement",
            status="FAIL",
            severity="HIGH",
            actual_value=None,
            expected_value="EWB Required",
            message="E-Way Bill mandatory for goods movement above 50,000 INR but missing",
        )
        decision = ComplianceDecision(
            invoice_no="INV-G5-001",
            invoice_date="2023-11-25",
            direction="AP",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Vendor A",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Server Hardware",
            taxable_value_inr=150000.0,
            total_amt=177000.0,
            gates=[g5_result],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="Missing EWB",
            recommended_action="Obtain EWB",
            sap_action="HOLD",
            audit_trail_ref="AUD-004",
            hard_override=False,
        )

        impacts = self.calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        imp = impacts[0]
        self.assertEqual(imp.calculation_status, CalculationStatus.UNDETERMINED)
        self.assertEqual(imp.potential_exposure, Decimal("0.00"))
        self.assertIn("ewb_penalty_policy", imp.required_data)
        self.assertIn("penalty", imp.undetermined_reason.lower())

    def test_missing_taxable_value_yields_undetermined(self):
        """If taxable value is missing, Gate 3 rate mismatch evaluates to UNDETERMINED."""
        g3_result = ValidationResult(
            gate_no=3,
            rule_id="RULE-GATE-3-TAX-RATE",
            rule_name="GST Rate Validation",
            status="FAIL",
            actual_value={"rate": 18.0},
            expected_value={"rate": 12.0},
            message="Tax rate mismatch",
        )
        decision = ComplianceDecision(
            invoice_no="INV-NOVAL-001",
            invoice_date="2023-11-26",
            direction="AP",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Vendor A",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Hardware",
            taxable_value_inr=0.0,  # missing / zero
            total_amt=0.0,
            gates=[g3_result],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="Zero taxable value",
            recommended_action="Review",
            sap_action="HOLD",
            audit_trail_ref="AUD-005",
            hard_override=False,
        )

        impacts = self.calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        self.assertEqual(impacts[0].calculation_status, CalculationStatus.UNDETERMINED)
        self.assertIn("taxable_value", impacts[0].required_data)


class TestAggregateCalculator(unittest.TestCase):
    """Test portfolio-level aggregation, counterparty grouping, rule grouping, trends, and ranking."""

    def setUp(self):
        self.agg_calc = AggregateCalculator()

    def _make_sample_impacts(self):
        imp1 = FinancialImpact(
            impact_id="IMP-001",
            invoice_id="INV-001",
            invoice_date=date(2023, 10, 15),
            counterparty_id="27ABCDE1234F1Z5",
            counterparty_name="Vendor Alpha",
            rule_id="RULE-GATE-3-TAX-RATE",
            rule_category="TAX",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            direction=ImpactDirection.OVERCHARGED_TAX,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("6000.00"),
            taxable_value=Decimal("100000.00"),
        )
        imp2 = FinancialImpact(
            impact_id="IMP-002",
            invoice_id="INV-002",
            invoice_date=date(2023, 10, 20),
            counterparty_id="27ABCDE1234F1Z5",
            counterparty_name="Vendor Alpha",
            rule_id="RULE-GATE-6-ITC",
            rule_category="ITC",
            impact_type=FinancialImpactType.ITC_EXPOSURE,
            direction=ImpactDirection.NOT_APPLICABLE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("4000.00"),
            taxable_value=Decimal("50000.00"),
        )
        imp3 = FinancialImpact(
            impact_id="IMP-003",
            invoice_id="INV-003",
            invoice_date=date(2023, 11, 10),
            counterparty_id="29BBAAA2222K1Z1",
            counterparty_name="Vendor Beta",
            rule_id="RULE-GATE-5-EWAY",
            rule_category="EWAY_BILL",
            impact_type=FinancialImpactType.EWB_RELATED_EXPOSURE,
            direction=ImpactDirection.NOT_APPLICABLE,
            calculation_status=CalculationStatus.UNDETERMINED,
            potential_exposure=Decimal("0.00"),
            reason="No configured penalty policy",
            required_data=["ewb_penalty_policy"],
        )
        imp4 = FinancialImpact(
            impact_id="IMP-004",
            invoice_id="INV-004",
            invoice_date=date(2023, 11, 15),
            counterparty_id="29BBAAA2222K1Z1",
            counterparty_name="Vendor Beta",
            rule_id="RULE-GATE-3-TAX-RATE",
            rule_category="TAX",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            direction=ImpactDirection.UNDERCHARGED_TAX,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("3000.00"),
            taxable_value=Decimal("50000.00"),
        )
        imp5 = FinancialImpact(
            impact_id="IMP-005",
            invoice_id="INV-005",
            invoice_date=date(2023, 11, 20),
            counterparty_id="27CLEAN1111A1Z9",
            counterparty_name="Clean Supplier",
            rule_id="COMPLIANT",
            rule_category="COMPLIANCE",
            impact_type=FinancialImpactType.OTHER,
            direction=ImpactDirection.NOT_APPLICABLE,
            calculation_status=CalculationStatus.NOT_APPLICABLE,
            potential_exposure=Decimal("0.00"),
        )
        return [imp1, imp2, imp3, imp4, imp5]

    def test_portfolio_aggregation_excludes_undetermined(self):
        """Aggregate total exposure must strictly equal 6000 + 4000 + 3000 = 13,000.00 INR."""
        impacts = self._make_sample_impacts()
        agg = self.agg_calc.aggregate(impacts)

        self.assertEqual(agg.total_invoices_analyzed, 5)
        self.assertEqual(agg.impacted_invoices_count, 3)
        self.assertEqual(agg.total_potential_exposure, Decimal("13000.00"))
        self.assertEqual(agg.total_tax_difference, Decimal("9000.00"))  # 6000 + 3000
        self.assertEqual(agg.total_itc_exposure, Decimal("4000.00"))     # 4000
        self.assertEqual(agg.overcharged_tax_total, Decimal("6000.00"))
        self.assertEqual(agg.undercharged_tax_total, Decimal("3000.00"))

        # Status tracking
        self.assertEqual(agg.calculated_count, 3)
        self.assertEqual(agg.undetermined_count, 1)
        self.assertEqual(agg.not_applicable_count, 1)

    def test_counterparty_aggregation(self):
        """Counterparties must aggregate with Vendor Alpha = 10,000 INR, Vendor Beta = 3,000 INR."""
        impacts = self._make_sample_impacts()
        cp_exposures = self.agg_calc.build_counterparty_exposures(impacts)

        self.assertEqual(len(cp_exposures), 3)
        # Sorted by potential exposure DESC
        alpha = cp_exposures[0]
        self.assertEqual(alpha.counterparty_id, "27ABCDE1234F1Z5")
        self.assertEqual(alpha.total_potential_exposure, Decimal("10000.00"))
        self.assertEqual(alpha.impacted_invoice_count, 2)

        beta = cp_exposures[1]
        self.assertEqual(beta.counterparty_id, "29BBAAA2222K1Z1")
        self.assertEqual(beta.total_potential_exposure, Decimal("3000.00"))
        self.assertEqual(beta.undetermined_count, 1)

    def test_rule_aggregation(self):
        """Rules must aggregate by rule ID."""
        impacts = self._make_sample_impacts()
        rule_exposures = self.agg_calc.build_rule_exposures(impacts)

        rule_map = {r.rule_id: r for r in rule_exposures}
        self.assertIn("RULE-GATE-3-TAX-RATE", rule_map)
        self.assertEqual(rule_map["RULE-GATE-3-TAX-RATE"].total_potential_exposure, Decimal("9000.00"))
        self.assertIn("RULE-GATE-6-ITC", rule_map)
        self.assertEqual(rule_map["RULE-GATE-6-ITC"].total_potential_exposure, Decimal("4000.00"))
        self.assertIn("RULE-GATE-5-EWAY", rule_map)
        self.assertEqual(rule_map["RULE-GATE-5-EWAY"].total_potential_exposure, Decimal("0.00"))
        self.assertEqual(rule_map["RULE-GATE-5-EWAY"].calculation_status_counts.get("UNDETERMINED"), 1)

    def test_period_exposures_and_trends(self):
        """Monthly aggregation: 2023-10 (10,000.00) to 2023-11 (3,000.00) -> DECREASING trend."""
        impacts = self._make_sample_impacts()
        period_exposures = self.agg_calc.build_period_exposures(impacts)

        self.assertEqual(len(period_exposures), 2)
        p_oct = period_exposures[0]
        self.assertEqual(p_oct.period_key, "2023-10")
        self.assertEqual(p_oct.total_potential_exposure, Decimal("10000.00"))

        p_nov = period_exposures[1]
        self.assertEqual(p_nov.period_key, "2023-11")
        self.assertEqual(p_nov.total_potential_exposure, Decimal("3000.00"))

        trends = self.agg_calc.build_period_trends(period_exposures)
        self.assertEqual(len(trends), 2)
        nov_trend = trends[1]
        self.assertEqual(nov_trend.direction, "DECREASING")
        self.assertEqual(nov_trend.absolute_change, Decimal("-7000.00"))
        self.assertEqual(nov_trend.percentage_change, -70.0)

    def test_deterministic_top_exposures_ranking(self):
        """Top exposures must sort by potential_exposure DESC, invoice_date, invoice_id."""
        impacts = self._make_sample_impacts()
        top = self.agg_calc.get_top_exposures(impacts, limit=3)

        self.assertEqual(len(top), 3)
        self.assertEqual(top[0].invoice_id, "INV-001")  # 6000
        self.assertEqual(top[1].invoice_id, "INV-002")  # 4000
        self.assertEqual(top[2].invoice_id, "INV-004")  # 3000


class TestFinancialServiceAndAdjustments(unittest.TestCase):
    """Test FinancialService orchestration and adjustment generation."""

    def setUp(self):
        self.service = FinancialService()

    def test_service_evaluate_batch_and_adjustments(self):
        """FinancialService evaluates batch, stores impacts, and generates adjustments."""
        g3 = ValidationResult(
            gate_no=3,
            rule_id="RULE-GATE-3-TAX-RATE",
            rule_name="GST Rate Validation",
            status="FAIL",
            actual_value={"rate": 18.0},
            expected_value={"rate": 12.0},
            message="Rate mismatch",
        )
        d1 = ComplianceDecision(
            invoice_no="INV-ADJ-001",
            invoice_date="2023-10-10",
            direction="AP",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Vendor Alpha",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Hardware",
            taxable_value_inr=100000.0,
            total_amt=118000.0,
            gates=[g3],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="Rate mismatch",
            recommended_action="Review",
            sap_action="HOLD",
            audit_trail_ref="AUD-101",
            hard_override=False,
        )

        g6 = ValidationResult(
            gate_no=6,
            rule_id="RULE-GATE-6-ITC",
            rule_name="ITC Eligibility Validation",
            status="FAIL",
            actual_value="BLOCKED",
            expected_value="ELIGIBLE",
            message="Blocked ITC under Section 17(5)",
        )
        d2 = ComplianceDecision(
            invoice_no="INV-ADJ-002",
            invoice_date="2023-10-12",
            direction="AP",
            counterparty_gstin="27XYZAB9999K1Z4",
            counterparty_name="Vendor Beta",
            place_of_supply="27",
            hsn_code="996331",
            item_desc="Catering",
            taxable_value_inr=40000.0,
            total_amt=42000.0,
            gates=[g6],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="Blocked ITC",
            recommended_action="Reverse",
            sap_action="HOLD",
            audit_trail_ref="AUD-102",
            hard_override=False,
        )

        impacts = self.service.evaluate_batch([d1, d2])
        self.assertEqual(len(impacts), 2)
        self.assertEqual(self.service.repository.count(), 2)

        # Generate adjustments
        adjustments = self.service.generate_adjustments()
        self.assertEqual(len(adjustments), 2)

        adj_types = {a.adjustment_type for a in adjustments}
        self.assertIn("CREDIT_NOTE_REQUIRED", adj_types)
        self.assertIn("ITC_REVERSAL_REQUIRED", adj_types)

        # Generate full report
        report = self.service.generate_report(top_n=5)
        self.assertEqual(report.aggregate.total_potential_exposure, Decimal("8000.00"))  # 6000 + 2000
        summary_text = report.to_text_summary()
        self.assertIn("Financial Impact & Exposure Intelligence Summary", summary_text)
        self.assertIn("INR 8,000.00", summary_text)


class TestDecimalPrecisionAndRounding(unittest.TestCase):
    """Test strict decimal mathematics and ROUND_HALF_UP rounding rules."""

    def test_round_monetary_boundary_half_up(self):
        """0.005 rounds up to 0.01; 0.004 rounds down to 0.00."""
        self.assertEqual(round_monetary(Decimal("100.005")), Decimal("100.01"))
        self.assertEqual(round_monetary(Decimal("100.004")), Decimal("100.00"))
        self.assertEqual(round_monetary(Decimal("100.0051")), Decimal("100.01"))
        self.assertEqual(round_monetary(Decimal("0.000")), Decimal("0.00"))

    def test_zero_floating_point_drift(self):
        """Repeated fractional calculations must not introduce floating point drift."""
        taxable = Decimal("3333.33")
        rate_diff = Decimal("6.00")
        result = round_monetary(taxable * (rate_diff / Decimal("100.00")))
        # 3333.33 * 0.06 = 199.9998 -> 200.00
        self.assertEqual(result, Decimal("200.00"))


if __name__ == "__main__":
    unittest.main()
