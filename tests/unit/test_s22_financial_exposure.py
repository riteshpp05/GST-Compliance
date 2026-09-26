"""
UC15 GST Compliance Agent — Sprint 22 Financial Exposure Unit Tests
Verifies canonical exposure classifications, step-by-step formula traces, and double-count safe summaries.
"""
import unittest
from decimal import Decimal

from app.engines.financial_engine import (
    FinancialExposureEngine,
    CanonicalExposureType,
    ExposureTrace,
    CaseFinancialSummary,
)
from app.financial.models.impact import FinancialImpact, FinancialImpactType, CalculationStatus, ImpactDirection


class TestS22FinancialExposure(unittest.TestCase):

    def setUp(self):
        self.engine = FinancialExposureEngine()

    def test_tax_difference_trace_generation(self):
        trace = self.engine.create_tax_difference_trace(
            finding_id="RULE-GST-TAX-001",
            taxable_value=Decimal("100000.00"),
            recorded_rate=Decimal("18.00"),
            expected_rate=Decimal("12.00"),
            recorded_tax=Decimal("18000.00"),
            expected_tax=Decimal("12000.00"),
        )
        self.assertEqual(trace.exposure_type, CanonicalExposureType.TAX_OVERCHARGE.value)
        self.assertEqual(trace.amount, Decimal("6000.00"))
        self.assertTrue(trace.is_informational)
        self.assertFalse(trace.is_additive)
        self.assertIn("formula", trace.calculation_trace)
        self.assertEqual(trace.calculation_trace["result"], 6000.0)

    def test_itc_at_risk_trace_generation(self):
        trace = self.engine.create_itc_at_risk_trace(
            finding_id="RULE-GST-ITC-001",
            blocked_tax_amount=Decimal("140000.00"),
            section="17(5)",
            category="Motor Vehicles",
        )
        self.assertEqual(trace.exposure_type, CanonicalExposureType.ITC_AT_RISK.value)
        self.assertEqual(trace.amount, Decimal("140000.00"))
        self.assertTrue(trace.is_overlapping)
        self.assertFalse(trace.is_additive)

    def test_penalty_exposure_trace_generation(self):
        trace = self.engine.create_penalty_exposure_trace(
            finding_id="RULE-GST-PENALTY-001",
            shortfall_tax_amount=Decimal("6000.00"),
        )
        self.assertEqual(trace.exposure_type, CanonicalExposureType.POTENTIAL_PENALTY.value)
        # Minimum penalty is 10,000 when shortfall < 10,000
        self.assertEqual(trace.amount, Decimal("10000.00"))
        self.assertTrue(trace.is_additive)
        self.assertFalse(trace.is_overlapping)

    def test_interest_exposure_trace_generation(self):
        trace = self.engine.create_interest_exposure_trace(
            finding_id="RULE-GST-INTEREST-001",
            base_tax_amount=Decimal("100000.00"),
            delay_days=365,
            annual_rate_pct=Decimal("18.00"),
        )
        self.assertEqual(trace.exposure_type, CanonicalExposureType.POTENTIAL_INTEREST.value)
        self.assertEqual(trace.amount, Decimal("18000.00"))
        self.assertTrue(trace.is_additive)

    def test_double_count_safe_case_summary(self):
        tax_under_trace = ExposureTrace(
            exposure_type=CanonicalExposureType.TAX_UNDERCHARGE.value,
            amount=Decimal("5000.00"),
            is_additive=True,
            is_overlapping=False,
        )
        penalty_trace = ExposureTrace(
            exposure_type=CanonicalExposureType.POTENTIAL_PENALTY.value,
            amount=Decimal("10000.00"),
            is_additive=True,
            is_overlapping=False,
        )
        overlapping_itc_trace = ExposureTrace(
            exposure_type=CanonicalExposureType.ITC_AT_RISK.value,
            amount=Decimal("18000.00"),
            is_additive=False,
            is_overlapping=True,
        )

        summary = self.engine.summarize_case_exposure(
            case_id="CASE-S22-001",
            invoice_id="INV-001",
            traces=[tax_under_trace, penalty_trace, overlapping_itc_trace],
        )

        self.assertEqual(summary.additive_total, Decimal("15000.00"))
        self.assertEqual(summary.overlapping_total, Decimal("18000.00"))
        self.assertEqual(summary.net_financial_exposure, Decimal("15000.00"))
        self.assertIn("CASE-S22-001", summary.case_id)
        self.assertTrue(len(summary.summary_notes) > 0)


if __name__ == "__main__":
    unittest.main()
