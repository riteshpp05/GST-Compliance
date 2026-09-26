"""
tests/unit/test_financial_hardening.py
======================================
Dedicated unit test suite for Sprint 6.1 — Financial Reporting & Aggregation Hardening.

Validates all 10 core audit and hardening requirements:
1. Status Consistency: Positive exposure always CALCULATED or PARTIALLY_CALCULATED, never NOT_APPLICABLE.
2. Zero Dollar Rule: UNDETERMINED and NOT_APPLICABLE impacts contribute 0.00 INR to totals.
3. Duplicate Protection vs Legitimate Multiple Impacts (Case A vs Case B).
4. Gate 4 Place of Supply evaluates to NOT_APPLICABLE with 0.00 exposure (no phantom double-counting).
5. Gate 6 AR evaluation returns NOT_APPLICABLE with 0.00 exposure.
6. Reconciliation Invariants: Total == Rule Sum == Counterparty Sum == Period Sum.
7. Directional Reconciliation: Overcharged + Undercharged == Tax Difference Exposure.
8. Deterministic Ranking & Tie-Breaking across impacts, counterparties, and rules.
9. Display Semantics: to_text_summary() renders clean, unambiguous statuses.
10. Repository Safety & Edge Cases: get_by_invoice_id handles None safely, Decimal precision.
"""

import unittest
from datetime import date
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models import (
    CalculationStatus,
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    round_monetary,
    AggregateFinancialExposure,
    FinancialReport,
)
from app.financial.calculators.exposure_calculator import InvoiceExposureCalculator
from app.financial.calculators.aggregate_calculator import AggregateCalculator
from app.financial.calculators.tax_difference import TaxDifferenceCalculator
from app.financial.repositories.in_memory import InMemoryFinancialRepository
from app.financial.services.financial_service import FinancialService


class TestStatusConsistencyAndZeroDollarRule(unittest.TestCase):
    """Verify calculation status semantics and zero dollar contribution rules."""

    def setUp(self):
        self.agg_calc = AggregateCalculator()
        self.exp_calc = InvoiceExposureCalculator()

    def test_positive_exposure_requires_calculated_status(self):
        """Positive exposure must only be associated with CALCULATED or PARTIALLY_CALCULATED."""
        imp_calc = FinancialImpact(
            impact_id="IMP-CALC",
            invoice_id="INV-001",
            invoice_date=date(2023, 10, 1),
            counterparty_id="27AAA1111A1Z1",
            rule_id="TAX_001",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("500.00"),
        )
        imp_partial = FinancialImpact(
            impact_id="IMP-PART",
            invoice_id="INV-002",
            invoice_date=date(2023, 10, 1),
            counterparty_id="27AAA1111A1Z1",
            rule_id="TAX_002",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.PARTIALLY_CALCULATED,
            potential_exposure=Decimal("250.00"),
        )
        agg = self.agg_calc.aggregate([imp_calc, imp_partial])
        self.assertEqual(agg.total_potential_exposure, Decimal("750.00"))
        self.assertEqual(agg.calculated_count, 1)
        self.assertEqual(agg.partially_calculated_count, 1)

    def test_not_applicable_and_undetermined_contribute_zero_to_portfolio(self):
        """NOT_APPLICABLE and UNDETERMINED impacts strictly contribute 0.00 INR to totals."""
        imp_na = FinancialImpact(
            impact_id="IMP-NA",
            invoice_id="INV-NA",
            invoice_date=date(2023, 10, 1),
            counterparty_id="27AAA1111A1Z1",
            rule_id="POS_001",
            impact_type=FinancialImpactType.OTHER,
            calculation_status=CalculationStatus.NOT_APPLICABLE,
            potential_exposure=Decimal("0.00"),
        )
        imp_undet = FinancialImpact(
            impact_id="IMP-UNDET",
            invoice_id="INV-UNDET",
            invoice_date=date(2023, 10, 1),
            counterparty_id="27AAA1111A1Z1",
            rule_id="EWB_001",
            impact_type=FinancialImpactType.EWB_RELATED_EXPOSURE,
            calculation_status=CalculationStatus.UNDETERMINED,
            potential_exposure=Decimal("0.00"),
            reason="No penalty policy configured",
        )
        imp_undet_none = FinancialImpact(
            impact_id="IMP-UNDET-NONE",
            invoice_id="INV-UNDET2",
            invoice_date=date(2023, 10, 1),
            counterparty_id="27AAA1111A1Z1",
            rule_id="DATA_001",
            impact_type=FinancialImpactType.DATA_QUALITY_EXPOSURE,
            calculation_status=CalculationStatus.UNDETERMINED,
            potential_exposure=None,
        )

        agg = self.agg_calc.aggregate([imp_na, imp_undet, imp_undet_none])
        self.assertEqual(agg.total_potential_exposure, Decimal("0.00"))
        self.assertEqual(agg.impacted_invoices_count, 0)
        self.assertEqual(agg.total_tax_difference, Decimal("0.00"))
        self.assertEqual(agg.total_itc_exposure, Decimal("0.00"))
        self.assertEqual(agg.undetermined_count, 2)
        self.assertEqual(agg.not_applicable_count, 1)


class TestDuplicateProtectionAndMultipleImpacts(unittest.TestCase):
    """Verify Case A (Legitimate multiple impacts) vs Case B (Duplicate / Phantom exposure)."""

    def setUp(self):
        self.exp_calc = InvoiceExposureCalculator()
        self.agg_calc = AggregateCalculator()

    def test_case_a_legitimate_multiple_impacts_on_single_invoice(self):
        """Case A: Invoice with both Rate Difference (Gate 3) and Blocked ITC (Gate 6). Both are preserved."""
        g3 = ValidationResult(
            gate_no=3,
            rule_id="TAX_001",
            rule_name="GST Rate Check",
            status="FAIL",
            actual_value={"rate": 18.0},
            expected_value={"rate": 12.0},
            message="Rate mismatch: 18% vs 12%",
        )
        g6 = ValidationResult(
            gate_no=6,
            rule_id="ITC_001",
            rule_name="Blocked ITC Check",
            status="FAIL",
            actual_value="MOTOR_VEHICLES",
            expected_value="ELIGIBLE",
            message="ITC blocked under Sec 17(5)(a)",
        )
        decision = ComplianceDecision(
            invoice_no="INV-MULTI-001",
            invoice_date="2023-11-01",
            direction="AP",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Dual Failure Vendor",
            place_of_supply="27",
            hsn_code="8703",
            item_desc="Commercial Van",
            taxable_value_inr=100000.0,
            total_amt=118000.0,  # 18,000 INR tax
            gates=[g3, g6],
            failed_gate_count=2,
            status="NON_COMPLIANT",
            justification="Dual failures",
            recommended_action="Correct rate and reverse ITC",
            sap_action="BLOCK_PAYMENT",
            audit_trail_ref="AUD-M1",
            hard_override=False,
        )

        impacts = self.exp_calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 2)

        # First impact: Rate difference = 6,000 INR (18% - 12% on 100,000)
        imp_tax = next(i for i in impacts if i.impact_type == FinancialImpactType.TAX_RATE_DIFFERENCE)
        self.assertEqual(imp_tax.potential_exposure, Decimal("6000.00"))
        self.assertEqual(imp_tax.direction, ImpactDirection.OVERCHARGED_TAX)
        self.assertEqual(imp_tax.calculation_status, CalculationStatus.CALCULATED)

        # Second impact: Blocked ITC = 18,000 INR (total tax on AP invoice)
        imp_itc = next(i for i in impacts if i.impact_type == FinancialImpactType.ITC_EXPOSURE)
        self.assertEqual(imp_itc.potential_exposure, Decimal("18000.00"))
        self.assertEqual(imp_itc.calculation_status, CalculationStatus.CALCULATED)

        # Aggregate correctly captures both distinct statutory issues
        agg = self.agg_calc.aggregate(impacts)
        self.assertEqual(agg.total_potential_exposure, Decimal("24000.00"))
        self.assertEqual(agg.total_tax_difference, Decimal("6000.00"))
        self.assertEqual(agg.total_itc_exposure, Decimal("18000.00"))
        self.assertEqual(agg.impacted_invoices_count, 1)  # 1 unique invoice

    def test_case_b_gate4_place_of_supply_does_not_double_count_tax(self):
        """Case B: Gate 4 (Place of supply) produces NOT_APPLICABLE (0.00 INR), preventing phantom double-counting."""
        g4 = ValidationResult(
            gate_no=4,
            rule_id="POS_001",
            rule_name="Place of Supply Check",
            status="FAIL",
            message="Intra-state supply charged as IGST",
        )
        g6 = ValidationResult(
            gate_no=6,
            rule_id="ITC_001",
            rule_name="Blocked ITC Check",
            status="FAIL",
            message="ITC blocked under Sec 17(5)",
        )
        decision = ComplianceDecision(
            invoice_no="INV-8000001",
            invoice_date="2023-11-05",
            direction="AP",
            counterparty_gstin="29XCDBM5846M9ZE",
            counterparty_name="Tata Motors",
            place_of_supply="29",
            hsn_code="8703",
            item_desc="Automotive Supplies",
            taxable_value_inr=88000.0,
            total_amt=103840.0,  # 15,840 INR total tax
            gates=[g4, g6],
            failed_gate_count=2,
            status="NON_COMPLIANT",
            justification="POS and ITC failures",
            recommended_action="Review",
            sap_action="HOLD",
            audit_trail_ref="AUD-TM1",
            hard_override=False,
        )

        impacts = self.exp_calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 2)

        imp_pos = next(i for i in impacts if i.rule_id == "POS_001")
        self.assertEqual(imp_pos.calculation_status, CalculationStatus.NOT_APPLICABLE)
        self.assertEqual(imp_pos.potential_exposure, Decimal("0.00"))

        imp_itc = next(i for i in impacts if i.rule_id == "ITC_001")
        self.assertEqual(imp_itc.calculation_status, CalculationStatus.CALCULATED)
        self.assertEqual(imp_itc.potential_exposure, Decimal("15840.00"))

        # Portfolio aggregate has exactly 15,840.00, NOT 31,680.00!
        agg = self.agg_calc.aggregate(impacts)
        self.assertEqual(agg.total_potential_exposure, Decimal("15840.00"))
        self.assertEqual(agg.impacted_invoices_count, 1)

    def test_gate6_on_ar_sales_invoice_evaluates_to_not_applicable(self):
        """Gate 6 on AR (outward) invoice produces NOT_APPLICABLE (0.00 INR)."""
        g6 = ValidationResult(
            gate_no=6,
            rule_id="ITC_001",
            rule_name="ITC Eligibility",
            status="FAIL",
            message="ITC check on AR invoice",
        )
        decision = ComplianceDecision(
            invoice_no="INV-AR-SALES-001",
            invoice_date="2023-11-10",
            direction="AR",
            counterparty_gstin="27ABCDE1234F1Z5",
            counterparty_name="Customer Ltd",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Sales Product",
            taxable_value_inr=50000.0,
            total_amt=59000.0,
            gates=[g6],
            failed_gate_count=1,
            status="NEEDS_REVIEW",
            justification="AR ITC",
            recommended_action="Check",
            sap_action="NONE",
            audit_trail_ref="AUD-AR1",
            hard_override=False,
        )

        impacts = self.exp_calc.calculate_invoice_impact(decision)
        self.assertEqual(len(impacts), 1)
        imp = impacts[0]
        self.assertEqual(imp.calculation_status, CalculationStatus.NOT_APPLICABLE)
        self.assertEqual(imp.potential_exposure, Decimal("0.00"))
        self.assertIn("outward", imp.reason.lower())


class TestReconciliationInvariants(unittest.TestCase):
    """Verify that multi-dimensional totals strictly reconcile to the penny."""

    def setUp(self):
        self.agg_calc = AggregateCalculator()

    def test_multi_dimensional_reconciliation(self):
        """Portfolio total == sum(by_rule) == sum(by_counterparty) == sum(by_period)."""
        impacts = [
            FinancialImpact(
                impact_id="IMP-1",
                invoice_id="INV-1",
                invoice_date=date(2023, 7, 10),
                counterparty_id="CP_A",
                rule_id="TAX_001",
                impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
                direction=ImpactDirection.OVERCHARGED_TAX,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("10500.00"),
            ),
            FinancialImpact(
                impact_id="IMP-2",
                invoice_id="INV-2",
                invoice_date=date(2023, 7, 20),
                counterparty_id="CP_B",
                rule_id="ITC_001",
                impact_type=FinancialImpactType.ITC_EXPOSURE,
                direction=ImpactDirection.NOT_APPLICABLE,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("33780.00"),
            ),
            FinancialImpact(
                impact_id="IMP-3",
                invoice_id="INV-3",
                invoice_date=date(2023, 8, 5),
                counterparty_id="CP_C",
                rule_id="ITC_001",
                impact_type=FinancialImpactType.ITC_EXPOSURE,
                direction=ImpactDirection.NOT_APPLICABLE,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("48480.00"),
            ),
            # Undetermined and Not Applicable entries that must not alter totals
            FinancialImpact(
                impact_id="IMP-4",
                invoice_id="INV-4",
                invoice_date=date(2023, 8, 12),
                counterparty_id="CP_D",
                rule_id="EWB_001",
                impact_type=FinancialImpactType.EWB_RELATED_EXPOSURE,
                direction=ImpactDirection.NOT_APPLICABLE,
                calculation_status=CalculationStatus.UNDETERMINED,
                potential_exposure=Decimal("0.00"),
            ),
            FinancialImpact(
                impact_id="IMP-5",
                invoice_id="INV-5",
                invoice_date=date(2023, 8, 15),
                counterparty_id="CP_E",
                rule_id="POS_001",
                impact_type=FinancialImpactType.OTHER,
                direction=ImpactDirection.NOT_APPLICABLE,
                calculation_status=CalculationStatus.NOT_APPLICABLE,
                potential_exposure=Decimal("0.00"),
            ),
        ]

        agg = self.agg_calc.aggregate(impacts)
        expected_total = Decimal("92760.00")

        # 1. Portfolio Total Exposure
        self.assertEqual(agg.total_potential_exposure, expected_total)

        # 2. Total == Rule breakdown sum
        rule_sum = sum(agg.by_rule.values(), Decimal("0.00"))
        self.assertEqual(rule_sum, expected_total)

        # 3. Total == Counterparty breakdown sum
        cp_sum = sum(agg.by_counterparty.values(), Decimal("0.00"))
        self.assertEqual(cp_sum, expected_total)

        # 4. Total == Period breakdown sum
        period_sum = sum(agg.by_period.values(), Decimal("0.00"))
        self.assertEqual(period_sum, expected_total)

        # 5. Total == Tax Difference + ITC Exposure
        self.assertEqual(agg.total_tax_difference + agg.total_itc_exposure, expected_total)

        # 6. Directional reconciliation: Overcharged + Undercharged == Tax Difference Exposure
        self.assertEqual(agg.overcharged_tax_total + agg.undercharged_tax_total, agg.total_tax_difference)


class TestDeterministicRankingAndTieBreaking(unittest.TestCase):
    """Verify deterministic ranking with tie-breaking across exposure, date, and IDs."""

    def setUp(self):
        self.agg_calc = AggregateCalculator()

    def test_top_exposures_tie_breaking(self):
        """Top exposures break ties on potential_exposure DESC, date DESC, invoice_id ASC, rule_id ASC."""
        impacts = [
            # Two invoices with identical exposure and date
            FinancialImpact(
                impact_id="IMP-B",
                invoice_id="INV-B",
                invoice_date=date(2023, 10, 15),
                rule_id="ITC_001",
                impact_type=FinancialImpactType.ITC_EXPOSURE,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("15840.00"),
            ),
            FinancialImpact(
                impact_id="IMP-A",
                invoice_id="INV-A",
                invoice_date=date(2023, 10, 15),
                rule_id="ITC_001",
                impact_type=FinancialImpactType.ITC_EXPOSURE,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("15840.00"),
            ),
            # An invoice with identical exposure but newer date (should rank first)
            FinancialImpact(
                impact_id="IMP-C",
                invoice_id="INV-C",
                invoice_date=date(2023, 10, 20),
                rule_id="ITC_001",
                impact_type=FinancialImpactType.ITC_EXPOSURE,
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("15840.00"),
            ),
        ]

        ranked = self.agg_calc.get_top_exposures(impacts, limit=5)
        self.assertEqual(len(ranked), 3)
        self.assertEqual(ranked[0].invoice_id, "INV-C")  # Newer date
        self.assertEqual(ranked[1].invoice_id, "INV-A")  # Alphabetical tie-break A before B
        self.assertEqual(ranked[2].invoice_id, "INV-B")

    def test_counterparty_tie_breaking(self):
        """Counterparty exposures break ties on total_potential_exposure DESC, counterparty_id ASC."""
        impacts = [
            FinancialImpact(
                impact_id="IMP-1",
                invoice_id="INV-1",
                counterparty_id="CP_ZULU",
                counterparty_name="Zulu Corp",
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("5000.00"),
            ),
            FinancialImpact(
                impact_id="IMP-2",
                invoice_id="INV-2",
                counterparty_id="CP_ALPHA",
                counterparty_name="Alpha Corp",
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("5000.00"),
            ),
        ]
        profiles = self.agg_calc.build_counterparty_exposures(impacts)
        self.assertEqual(len(profiles), 2)
        self.assertEqual(profiles[0].counterparty_id, "CP_ALPHA")
        self.assertEqual(profiles[1].counterparty_id, "CP_ZULU")

    def test_rule_tie_breaking(self):
        """Rule exposures break ties on total_potential_exposure DESC, rule_id ASC."""
        impacts = [
            FinancialImpact(
                impact_id="IMP-1",
                invoice_id="INV-1",
                rule_id="RULE_BETA",
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("1000.00"),
            ),
            FinancialImpact(
                impact_id="IMP-2",
                invoice_id="INV-2",
                rule_id="RULE_ALPHA",
                calculation_status=CalculationStatus.CALCULATED,
                potential_exposure=Decimal("1000.00"),
            ),
        ]
        rules = self.agg_calc.build_rule_exposures(impacts)
        self.assertEqual(len(rules), 2)
        self.assertEqual(rules[0].rule_id, "RULE_ALPHA")
        self.assertEqual(rules[1].rule_id, "RULE_BETA")


class TestDisplaySemantics(unittest.TestCase):
    """Verify that to_text_summary() renders audit-safe, unambiguous statuses."""

    def test_text_summary_renders_clean_status(self):
        """Verify that NOT_APPLICABLE direction is never displayed next to positive exposure."""
        report = FinancialReport(
            aggregate=AggregateFinancialExposure(
                total_invoices_analyzed=2,
                impacted_invoices_count=2,
                total_potential_exposure=Decimal("21840.00"),
                total_tax_difference=Decimal("6000.00"),
                total_itc_exposure=Decimal("15840.00"),
                overcharged_tax_total=Decimal("6000.00"),
            ),
            top_exposures=[
                FinancialImpact(
                    impact_id="IMP-1",
                    invoice_id="INV-TAX-001",
                    counterparty_name="Tax Vendor",
                    impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
                    direction=ImpactDirection.OVERCHARGED_TAX,
                    calculation_status=CalculationStatus.CALCULATED,
                    potential_exposure=Decimal("6000.00"),
                ),
                FinancialImpact(
                    impact_id="IMP-2",
                    invoice_id="INV-ITC-001",
                    counterparty_name="ITC Vendor",
                    impact_type=FinancialImpactType.ITC_EXPOSURE,
                    direction=ImpactDirection.NOT_APPLICABLE,
                    calculation_status=CalculationStatus.CALCULATED,
                    potential_exposure=Decimal("15840.00"),
                ),
            ],
        )

        summary_text = report.to_text_summary()

        # TAX_RATE_DIFFERENCE displays both direction and status
        self.assertIn("[TAX_RATE_DIFFERENCE | OVERCHARGED_TAX | CALCULATED]", summary_text)

        # ITC_EXPOSURE displays type and status, strictly omitting NOT_APPLICABLE direction
        self.assertIn("[ITC_EXPOSURE | CALCULATED]", summary_text)
        self.assertNotIn("[ITC_EXPOSURE | NOT_APPLICABLE]", summary_text)


class TestRepositorySafetyAndPrecision(unittest.TestCase):
    """Verify repository edge cases and Decimal rounding precision."""

    def test_repository_get_by_invoice_id_with_none_exposure(self):
        """Repository get_by_invoice_id handles records with None exposure without raising TypeError."""
        repo = InMemoryFinancialRepository()
        imp_none = FinancialImpact(
            impact_id="IMP-NONE",
            invoice_id="INV-MIXED",
            calculation_status=CalculationStatus.UNDETERMINED,
            potential_exposure=None,
        )
        imp_calc = FinancialImpact(
            impact_id="IMP-CALC",
            invoice_id="INV-MIXED",
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("1000.00"),
        )
        repo.add(imp_none)
        repo.add(imp_calc)

        primary = repo.get_by_invoice_id("INV-MIXED")
        self.assertIsNotNone(primary)
        self.assertEqual(primary.impact_id, "IMP-CALC")

    def test_decimal_rounding_half_up(self):
        """Monetary rounding adheres strictly to ROUND_HALF_UP."""
        self.assertEqual(round_monetary(Decimal("100.005")), Decimal("100.01"))
        self.assertEqual(round_monetary(Decimal("100.004")), Decimal("100.00"))
        self.assertEqual(round_monetary(Decimal("100.015")), Decimal("100.02"))


if __name__ == "__main__":
    unittest.main()
