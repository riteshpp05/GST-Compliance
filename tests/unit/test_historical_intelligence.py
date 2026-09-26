"""
UC15 GST Compliance Agent — Historical Intelligence & Time-Series Audit Test Suite (Sprint 5)
Verifies:
  1. Period Aggregation (daily, weekly, monthly, quarterly)
  2. Compliance Metrics (all compliant, mixed, all non-compliant, all needs-review, empty dataset)
  3. Trend Analysis (improving, stable, deteriorating, insufficient data)
  4. Rule Failure Pattern Classification (persistent, emerging, improving, resolved, isolated)
  5. Counterparty Compliance Intelligence & Consistency (single/multi-vendor, recurring patterns)
  6. Data Quality History (repeated DQ, isolated DQ, clean dataset)
  7. Retroactive Historical Audit (same result, changed result, reference difference, previously unresolved)
  8. Boundary & Edge Cases (0 invoices, 1 invoice, 1 period, missing fields, duplicate invoice IDs)
"""
import unittest
from datetime import date
from decimal import Decimal
from typing import List, Optional

from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.historical.config.historical_config import HistoricalConfig
from app.historical.models.audit import AuditOutcome
from app.historical.models.pattern import RulePatternClassification
from app.historical.models.period import PeriodType
from app.historical.models.record import HistoricalRecord
from app.historical.models.trend import TrendDirection
from app.historical.repositories.in_memory import InMemoryHistoricalRepository
from app.historical.services.historical_service import HistoricalService


class TestHistoricalIntelligence(unittest.TestCase):
    """Exhaustive test suite for Sprint 5 Historical Intelligence."""

    def setUp(self):
        self.repo = InMemoryHistoricalRepository()
        self.config = HistoricalConfig(
            trend_improving_threshold_pp=5.0,
            trend_deteriorating_threshold_pp=-5.0,
            min_pattern_invoices=2,
            min_pattern_periods=2,
            persistent_consecutive_periods=2,
            emerging_growth_factor=1.5,
            emerging_min_latest_failures=2,
            improving_reduction_ratio=0.25,
            counterparty_recurring_min_failures=2,
            dq_min_occurrences=2,
        )
        self.service = HistoricalService(repository=self.repo, config=self.config)

    def _make_record(
        self,
        invoice_id: str,
        invoice_date: date,
        status: str = "COMPLIANT",
        counterparty_gstin: str = "27AAACB1234A1Z5",
        counterparty_name: str = "Vendor Alpha",
        direction: str = "AP",
        hsn_code: str = "8471",
        taxable_value: float = 10000.0,
        total_amount: float = 11800.0,
        failed_rule_ids: Optional[List[str]] = None,
        data_quality_findings: Optional[List[str]] = None,
        reference_versions: Optional[dict] = None,
    ) -> HistoricalRecord:
        failed_rules = failed_rule_ids or []
        gate_results = {}
        for rid in failed_rules:
            gate_results[rid] = {
                "rule_name": f"Rule {rid}",
                "status": "FAIL",
                "message": f"Failure in {rid}",
                "category": "TAX" if "tax" in rid.lower() else "STATUTORY",
                "severity": "HIGH",
                "actual_value": "12.0",
                "expected_value": "18.0",
            }

        return HistoricalRecord(
            invoice_id=invoice_id,
            invoice_date=invoice_date,
            direction=direction,
            counterparty_gstin=counterparty_gstin,
            counterparty_name=counterparty_name,
            place_of_supply="Maharashtra",
            hsn_code=hsn_code,
            item_desc="Computer parts",
            taxable_value=Decimal(str(taxable_value)),
            total_tax=Decimal(str(total_amount - taxable_value)),
            total_amount=Decimal(str(total_amount)),
            compliance_status=status,
            failed_gate_count=len(failed_rules),
            failed_rule_ids=failed_rules,
            failed_gate_numbers=[1] if failed_rules else [],
            gate_results=gate_results,
            data_quality_findings=data_quality_findings or [],
            reference_versions=reference_versions or {"hsn": "1.0", "tax": "1.0"},
            audit_trail_ref="AUDIT-TEST",
        )

    # -------------------------------------------------------------------------
    # 1. Period Aggregation Tests
    # -------------------------------------------------------------------------

    def test_period_aggregation_daily(self):
        """Verify grouping and metric computation at Daily resolution."""
        r1 = self._make_record("INV-D1", date(2026, 6, 1), status="COMPLIANT")
        r2 = self._make_record("INV-D2", date(2026, 6, 1), status="NON_COMPLIANT", failed_rule_ids=["TAX_001"])
        r3 = self._make_record("INV-D3", date(2026, 6, 2), status="COMPLIANT")
        self.repo.add_batch([r1, r2, r3])

        metrics = self.service.get_period_metrics(period_type=PeriodType.DAILY)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0].period_key, "2026-06-01")
        self.assertEqual(metrics[0].total_invoices, 2)
        self.assertEqual(metrics[0].compliant_count, 1)
        self.assertEqual(metrics[0].non_compliant_count, 1)
        self.assertEqual(metrics[0].compliance_rate, 50.0)
        self.assertEqual(metrics[1].period_key, "2026-06-02")
        self.assertEqual(metrics[1].total_invoices, 1)
        self.assertEqual(metrics[1].compliance_rate, 100.0)

    def test_period_aggregation_weekly(self):
        """Verify grouping at ISO calendar Weekly resolution."""
        # 2026-06-01 is Week 23 Monday; 2026-06-08 is Week 24 Monday
        r1 = self._make_record("INV-W1", date(2026, 6, 1), status="COMPLIANT")
        r2 = self._make_record("INV-W2", date(2026, 6, 3), status="COMPLIANT")
        r3 = self._make_record("INV-W3", date(2026, 6, 8), status="NON_COMPLIANT", failed_rule_ids=["HSN_001"])
        self.repo.add_batch([r1, r2, r3])

        metrics = self.service.get_period_metrics(period_type=PeriodType.WEEKLY)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0].period_key, "2026-W23")
        self.assertEqual(metrics[0].total_invoices, 2)
        self.assertEqual(metrics[1].period_key, "2026-W24")
        self.assertEqual(metrics[1].total_invoices, 1)

    def test_period_aggregation_monthly(self):
        """Verify grouping at Monthly resolution (primary statutory filing period)."""
        r1 = self._make_record("INV-M1", date(2026, 5, 15), status="COMPLIANT")
        r2 = self._make_record("INV-M2", date(2026, 6, 10), status="NEEDS_REVIEW")
        r3 = self._make_record("INV-M3", date(2026, 6, 20), status="NON_COMPLIANT")
        self.repo.add_batch([r1, r2, r3])

        metrics = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)
        self.assertEqual(len(metrics), 2)
        self.assertEqual(metrics[0].period_key, "2026-05")
        self.assertEqual(metrics[0].total_invoices, 1)
        self.assertEqual(metrics[0].compliance_rate, 100.0)
        self.assertEqual(metrics[1].period_key, "2026-06")
        self.assertEqual(metrics[1].total_invoices, 2)
        self.assertEqual(metrics[1].needs_review_count, 1)
        self.assertEqual(metrics[1].non_compliant_count, 1)
        self.assertEqual(metrics[1].compliance_rate, 0.0)

    def test_period_aggregation_quarterly(self):
        """Verify grouping at Quarterly resolution."""
        r1 = self._make_record("INV-Q1", date(2026, 1, 10), status="COMPLIANT")  # Q1
        r2 = self._make_record("INV-Q2", date(2026, 4, 10), status="COMPLIANT")  # Q2
        r3 = self._make_record("INV-Q3", date(2026, 7, 10), status="COMPLIANT")  # Q3
        self.repo.add_batch([r1, r2, r3])

        metrics = self.service.get_period_metrics(period_type=PeriodType.QUARTERLY)
        self.assertEqual(len(metrics), 3)
        self.assertEqual(metrics[0].period_key, "2026-Q1")
        self.assertEqual(metrics[1].period_key, "2026-Q2")
        self.assertEqual(metrics[2].period_key, "2026-Q3")

    # -------------------------------------------------------------------------
    # 2. Compliance Metrics Populations
    # -------------------------------------------------------------------------

    def test_compliance_metrics_all_compliant(self):
        """100% compliant population."""
        recs = [self._make_record(f"INV-C{i}", date(2026, 6, i), status="COMPLIANT") for i in range(1, 6)]
        self.repo.add_batch(recs)
        m = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)[0]
        self.assertEqual(m.compliance_rate, 100.0)
        self.assertEqual(m.needs_review_rate, 0.0)
        self.assertEqual(m.non_compliance_rate, 0.0)

    def test_compliance_metrics_all_non_compliant(self):
        """100% non-compliant population."""
        recs = [self._make_record(f"INV-NC{i}", date(2026, 6, i), status="NON_COMPLIANT") for i in range(1, 5)]
        self.repo.add_batch(recs)
        m = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)[0]
        self.assertEqual(m.compliance_rate, 0.0)
        self.assertEqual(m.non_compliance_rate, 100.0)

    def test_compliance_metrics_all_needs_review(self):
        """100% needs_review population."""
        recs = [self._make_record(f"INV-NR{i}", date(2026, 6, i), status="NEEDS_REVIEW") for i in range(1, 4)]
        self.repo.add_batch(recs)
        m = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)[0]
        self.assertEqual(m.compliance_rate, 0.0)
        self.assertEqual(m.needs_review_rate, 100.0)

    def test_compliance_metrics_mixed_population(self):
        """Mixed population: 5 compliant, 3 needs_review, 2 non_compliant = 10 total (50% / 30% / 20%)."""
        recs = (
            [self._make_record(f"INV-MC{i}", date(2026, 6, i), status="COMPLIANT") for i in range(1, 6)] +
            [self._make_record(f"INV-MNR{i}", date(2026, 6, i + 5), status="NEEDS_REVIEW") for i in range(1, 4)] +
            [self._make_record(f"INV-MNC{i}", date(2026, 6, i + 8), status="NON_COMPLIANT", failed_rule_ids=["TAX_001"]) for i in range(1, 3)]
        )
        self.repo.add_batch(recs)
        m = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)[0]
        self.assertEqual(m.total_invoices, 10)
        self.assertEqual(m.compliant_count, 5)
        self.assertEqual(m.needs_review_count, 3)
        self.assertEqual(m.non_compliant_count, 2)
        self.assertEqual(m.compliance_rate, 50.0)
        self.assertEqual(m.needs_review_rate, 30.0)
        self.assertEqual(m.non_compliance_rate, 20.0)
        self.assertGreater(m.total_taxable_value, Decimal("0.00"))
        self.assertEqual(m.failed_gate_count, 2)

    def test_compliance_metrics_empty_dataset(self):
        """Empty repository returns empty metrics list."""
        metrics = self.service.get_period_metrics(period_type=PeriodType.MONTHLY)
        self.assertEqual(metrics, [])

    # -------------------------------------------------------------------------
    # 3. Trend Analysis Tests
    # -------------------------------------------------------------------------

    def test_trend_improving(self):
        """Compliance rate increases >= 5.0 pp -> IMPROVING."""
        # May: 5/10 = 50%
        may_recs = [self._make_record(f"INV-MAY-{i}", date(2026, 5, 10), status="COMPLIANT" if i <= 5 else "NON_COMPLIANT") for i in range(1, 11)]
        # June: 8/10 = 80% (+30 pp)
        june_recs = [self._make_record(f"INV-JUN-{i}", date(2026, 6, 10), status="COMPLIANT" if i <= 8 else "NON_COMPLIANT") for i in range(1, 11)]
        self.repo.add_batch(may_recs + june_recs)

        trends = self.service.get_trends()
        self.assertEqual(len(trends), 2)
        self.assertEqual(trends[0].direction, TrendDirection.INSUFFICIENT_DATA)  # baseline
        self.assertEqual(trends[1].direction, TrendDirection.IMPROVING)
        self.assertEqual(trends[1].absolute_change_pp, 30.0)
        self.assertIn("Compliance improved by +30.0 percentage points", trends[1].description)

    def test_trend_deteriorating(self):
        """Compliance rate decreases <= -5.0 pp -> DETERIORATING."""
        # May: 9/10 = 90%
        may_recs = [self._make_record(f"INV-MAY-{i}", date(2026, 5, 10), status="COMPLIANT" if i <= 9 else "NON_COMPLIANT") for i in range(1, 11)]
        # June: 7/10 = 70% (-20 pp)
        june_recs = [self._make_record(f"INV-JUN-{i}", date(2026, 6, 10), status="COMPLIANT" if i <= 7 else "NON_COMPLIANT") for i in range(1, 11)]
        self.repo.add_batch(may_recs + june_recs)

        trends = self.service.get_trends()
        self.assertEqual(trends[1].direction, TrendDirection.DETERIORATING)
        self.assertEqual(trends[1].absolute_change_pp, -20.0)

    def test_trend_stable(self):
        """Compliance rate within (-5.0, +5.0) pp -> STABLE."""
        # May: 8/10 = 80%
        may_recs = [self._make_record(f"INV-MAY-{i}", date(2026, 5, 10), status="COMPLIANT" if i <= 8 else "NON_COMPLIANT") for i in range(1, 11)]
        # June: 8/10 = 80% (0 pp change)
        june_recs = [self._make_record(f"INV-JUN-{i}", date(2026, 6, 10), status="COMPLIANT" if i <= 8 else "NON_COMPLIANT") for i in range(1, 11)]
        self.repo.add_batch(may_recs + june_recs)

        trends = self.service.get_trends()
        self.assertEqual(trends[1].direction, TrendDirection.STABLE)
        self.assertEqual(trends[1].absolute_change_pp, 0.0)

    def test_trend_insufficient_data(self):
        """Only 1 period yields INSUFFICIENT_DATA."""
        recs = [self._make_record(f"INV-{i}", date(2026, 6, 1), status="COMPLIANT") for i in range(1, 5)]
        self.repo.add_batch(recs)
        trends = self.service.get_trends()
        self.assertEqual(len(trends), 1)
        self.assertEqual(trends[0].direction, TrendDirection.INSUFFICIENT_DATA)

    # -------------------------------------------------------------------------
    # 4. Rule Failure Pattern Classification Tests
    # -------------------------------------------------------------------------

    def test_rule_pattern_persistent(self):
        """Rule failing across >= 2 consecutive periods classified as PERSISTENT."""
        r1 = self._make_record("INV-P1", date(2026, 5, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX_RATE"])
        r2 = self._make_record("INV-P2", date(2026, 6, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX_RATE"])
        r3 = self._make_record("INV-P3", date(2026, 7, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX_RATE"])
        self.repo.add_batch([r1, r2, r3])

        patterns = self.service.get_rule_patterns()
        tax_pat = next((p for p in patterns if p.rule_id == "RULE_TAX_RATE"), None)
        self.assertIsNotNone(tax_pat)
        self.assertEqual(tax_pat.classification, RulePatternClassification.PERSISTENT)
        self.assertEqual(tax_pat.total_failures, 3)
        self.assertEqual(len(tax_pat.periods_observed), 3)

    def test_rule_pattern_emerging(self):
        """Rule absent/low previously but surging in latest period classified as EMERGING."""
        # May: 0 failures, June: 0 failures, July: 4 failures
        r1 = self._make_record("INV-E1", date(2026, 5, 1), status="COMPLIANT")
        r2 = self._make_record("INV-E2", date(2026, 6, 1), status="COMPLIANT")
        r_surges = [
            self._make_record(f"INV-ES{i}", date(2026, 7, i), status="NON_COMPLIANT", failed_rule_ids=["RULE_EWAY_BILL"])
            for i in range(1, 5)
        ]
        self.repo.add_batch([r1, r2] + r_surges)

        patterns = self.service.get_rule_patterns()
        ewb_pat = next((p for p in patterns if p.rule_id == "RULE_EWAY_BILL"), None)
        self.assertIsNotNone(ewb_pat)
        self.assertEqual(ewb_pat.classification, RulePatternClassification.EMERGING)
        self.assertEqual(ewb_pat.latest_failure_count, 4)

    def test_rule_pattern_improving(self):
        """Rule failure count steadily decreasing classified as IMPROVING."""
        # May: 5 failures, June: 2 failures (-60% reduction >= 25% threshold)
        may_fails = [self._make_record(f"INV-IMP-M{i}", date(2026, 5, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_POS"]) for i in range(5)]
        jun_fails = [self._make_record(f"INV-IMP-J{i}", date(2026, 6, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_POS"]) for i in range(2)]
        self.repo.add_batch(may_fails + jun_fails)

        patterns = self.service.get_rule_patterns()
        pos_pat = next((p for p in patterns if p.rule_id == "RULE_POS"), None)
        self.assertIsNotNone(pos_pat)
        self.assertEqual(pos_pat.classification, RulePatternClassification.IMPROVING)

    def test_rule_pattern_resolved(self):
        """Rule failing in previous periods with 0 failures in latest period classified as RESOLVED."""
        # May: 3 failures, June: 0 failures
        may_fails = [self._make_record(f"INV-RES-M{i}", date(2026, 5, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_HSN"]) for i in range(3)]
        jun_clean = [self._make_record(f"INV-RES-J{i}", date(2026, 6, 1), status="COMPLIANT") for i in range(5)]
        self.repo.add_batch(may_fails + jun_clean)

        patterns = self.service.get_rule_patterns()
        hsn_pat = next((p for p in patterns if p.rule_id == "RULE_HSN"), None)
        self.assertIsNotNone(hsn_pat)
        self.assertEqual(hsn_pat.classification, RulePatternClassification.RESOLVED)
        self.assertEqual(hsn_pat.latest_failure_count, 0)

    def test_rule_pattern_isolated(self):
        """Single sporadic failure not meeting recurrence threshold classified as ISOLATED."""
        r1 = self._make_record("INV-ISO-1", date(2026, 5, 1), status="COMPLIANT")
        r2 = self._make_record("INV-ISO-2", date(2026, 6, 1), status="NON_COMPLIANT", failed_rule_ids=["RULE_SPORADIC"])
        self.repo.add_batch([r1, r2])

        patterns = self.service.get_rule_patterns()
        pat = next((p for p in patterns if p.rule_id == "RULE_SPORADIC"), None)
        self.assertIsNotNone(pat)
        self.assertEqual(pat.classification, RulePatternClassification.ISOLATED)

    # -------------------------------------------------------------------------
    # 5. Counterparty Historical Intelligence Tests
    # -------------------------------------------------------------------------

    def test_counterparty_profiling_single_and_multi_vendor(self):
        """Counterparties profiled with compliance counts, rates, and active periods."""
        r1 = self._make_record("INV-V1", date(2026, 5, 1), counterparty_gstin="27ABC1", counterparty_name="Vendor 1", status="COMPLIANT")
        r2 = self._make_record("INV-V2", date(2026, 6, 1), counterparty_gstin="27ABC1", counterparty_name="Vendor 1", status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX"])
        r3 = self._make_record("INV-V3", date(2026, 6, 1), counterparty_gstin="29XYZ2", counterparty_name="Vendor 2", status="COMPLIANT")
        self.repo.add_batch([r1, r2, r3])

        profiles = self.service.get_counterparty_profiles()
        self.assertEqual(len(profiles), 2)
        v1 = next(p for p in profiles if p.counterparty_id == "27ABC1")
        self.assertEqual(v1.total_invoices, 2)
        self.assertEqual(v1.compliance_rate, 50.0)
        self.assertEqual(v1.total_failures, 1)
        self.assertEqual(v1.top_failed_rules[0], ("RULE_TAX", 1))

    def test_counterparty_recurring_consistency_pattern(self):
        """Detect same vendor failing same rule across multiple periods (RECURRING_COUNTERPARTY_PATTERN)."""
        r1 = self._make_record("INV-RC1", date(2026, 5, 1), counterparty_gstin="27VEND1", hsn_code="8471", status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX_RATE"])
        r2 = self._make_record("INV-RC2", date(2026, 6, 1), counterparty_gstin="27VEND1", hsn_code="8471", status="NON_COMPLIANT", failed_rule_ids=["RULE_TAX_RATE"])
        self.repo.add_batch([r1, r2])

        patterns = self.service.get_recurring_counterparty_patterns()
        self.assertTrue(len(patterns) >= 1)
        pat = patterns[0]
        self.assertEqual(pat.counterparty_id, "27VEND1")
        self.assertEqual(pat.hsn_code, "8471")
        self.assertEqual(pat.occurrences, 2)
        self.assertIn("repeated", pat.evidence)

    # -------------------------------------------------------------------------
    # 6. Data Quality History Tests
    # -------------------------------------------------------------------------

    def test_data_quality_recurring_and_isolated(self):
        """Repeated data defects flagged as recurring; isolated defects flagged as non-recurring."""
        # 2 records with missing state info -> recurring
        r1 = self._make_record("INV-DQ1", date(2026, 5, 1), data_quality_findings=["missing counterparty state declaration"])
        r2 = self._make_record("INV-DQ2", date(2026, 6, 1), data_quality_findings=["missing place of supply state"])
        # 1 record with date defect -> isolated
        r3 = self._make_record("INV-DQ3", date(2026, 6, 1), data_quality_findings=["invalid invoice date format"])
        self.repo.add_batch([r1, r2, r3])

        dq_patterns = self.service.get_data_quality_patterns()
        state_pat = next((p for p in dq_patterns if "STATE" in p.issue_type), None)
        date_pat = next((p for p in dq_patterns if "DATE" in p.issue_type), None)

        self.assertIsNotNone(state_pat)
        self.assertTrue(state_pat.is_recurring)
        self.assertEqual(state_pat.occurrence_count, 2)

        self.assertIsNotNone(date_pat)
        self.assertFalse(date_pat.is_recurring)
        self.assertEqual(date_pat.occurrence_count, 1)

    def test_data_quality_clean_dataset(self):
        """Dataset with 0 data quality issues yields empty data quality patterns."""
        r1 = self._make_record("INV-CLEAN", date(2026, 6, 1))
        self.repo.add(r1)
        dq_patterns = self.service.get_data_quality_patterns()
        self.assertEqual(dq_patterns, [])

    # -------------------------------------------------------------------------
    # 7. Historical Audit / Retroactive Simulation Tests
    # -------------------------------------------------------------------------

    def test_historical_audit_same_result(self):
        """Retroactive validation matching recorded status yields SAME_RESULT."""
        r = self._make_record("INV-AUD-1", date(2023, 6, 1), status="COMPLIANT")
        self.repo.add(r)

        # Mock retroactive decision with matching status
        decision = ComplianceDecision(
            invoice_no="INV-AUD-1",
            invoice_date="2023-06-01",
            direction="AP",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Vendor Alpha",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Computer parts",
            taxable_value_inr=10000.0,
            total_amt=11800.0,
            gates=[],
            failed_gate_count=0,
            status="COMPLIANT",
            justification="OK",
            recommended_action="",
            sap_action="",
            audit_trail_ref="AUD-1",
            hard_override=False,
        )

        comp = self.service.audit_analyzer.audit_record(r, retroactive_decision=decision)
        self.assertEqual(comp.outcome, AuditOutcome.SAME_RESULT)

    def test_historical_audit_changed_result(self):
        """Retroactive validation differing from recorded status yields NEWLY_COMPLIANT or RESULT_CHANGED."""
        r = self._make_record("INV-AUD-2", date(2023, 6, 1), status="NON_COMPLIANT")
        self.repo.add(r)

        decision = ComplianceDecision(
            invoice_no="INV-AUD-2",
            invoice_date="2023-06-01",
            direction="AP",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Vendor Alpha",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Computer parts",
            taxable_value_inr=10000.0,
            total_amt=11800.0,
            gates=[],
            failed_gate_count=0,
            status="COMPLIANT",
            justification="Upgraded",
            recommended_action="",
            sap_action="",
            audit_trail_ref="AUD-2",
            hard_override=False,
        )

        comp = self.service.audit_analyzer.audit_record(r, retroactive_decision=decision)
        self.assertEqual(comp.outcome, AuditOutcome.NEWLY_COMPLIANT)
        self.assertIn("upgraded from NON_COMPLIANT to COMPLIANT", comp.reason)

    def test_historical_audit_reference_changed(self):
        """Identical compliance status but reference version bump yields REFERENCE_CHANGED."""
        r = self._make_record("INV-AUD-3", date(2023, 6, 1), status="COMPLIANT", reference_versions={"hsn": "1.0"})
        self.repo.add(r)

        # Snapshot with updated version 2.0
        from unittest.mock import MagicMock
        snap = MagicMock()
        ref_record = MagicMock()
        ref_record.version = "2.0"
        snap.references = {"hsn": ref_record}

        decision = ComplianceDecision(
            invoice_no="INV-AUD-3",
            invoice_date="2023-06-01",
            direction="AP",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Vendor Alpha",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Computer parts",
            taxable_value_inr=10000.0,
            total_amt=11800.0,
            gates=[],
            failed_gate_count=0,
            status="COMPLIANT",
            justification="OK",
            recommended_action="",
            sap_action="",
            audit_trail_ref="AUD-3",
            hard_override=False,
            reference_snapshot=snap,
        )

        comp = self.service.audit_analyzer.audit_record(r, retroactive_decision=decision)
        self.assertEqual(comp.outcome, AuditOutcome.REFERENCE_CHANGED)
        self.assertTrue(len(comp.reference_differences) > 0)

    def test_historical_audit_previously_unresolved(self):
        """Transaction originally NEEDS_REVIEW resolves to COMPLIANT retroactively."""
        r = self._make_record("INV-AUD-UNRES", date(2023, 6, 1), status="NEEDS_REVIEW")
        self.repo.add(r)

        decision = ComplianceDecision(
            invoice_no="INV-AUD-UNRES",
            invoice_date="2023-06-01",
            direction="AP",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Vendor Alpha",
            place_of_supply="Maharashtra",
            hsn_code="8471",
            item_desc="Computer parts",
            taxable_value_inr=10000.0,
            total_amt=11800.0,
            gates=[],
            failed_gate_count=0,
            status="COMPLIANT",
            justification="Resolved via active reference",
            recommended_action="",
            sap_action="",
            audit_trail_ref="AUD-UNRES",
            hard_override=False,
        )

        comp = self.service.audit_analyzer.audit_record(r, retroactive_decision=decision)
        self.assertEqual(comp.outcome, AuditOutcome.PREVIOUSLY_UNRESOLVED)
        self.assertIn("resolved", comp.reason)

    # -------------------------------------------------------------------------
    # 8. Boundary and Edge Cases
    # -------------------------------------------------------------------------

    def test_boundary_zero_invoices(self):
        """Report generation on 0 invoices operates cleanly without errors."""
        report = self.service.generate_report()
        self.assertEqual(report.total_invoices_analyzed, 0)
        self.assertEqual(report.periods, [])
        self.assertEqual(report.trends, [])
        self.assertEqual(report.rule_patterns, [])
        self.assertEqual(report.counterparty_profiles, [])

    def test_boundary_single_invoice(self):
        """Single invoice processed without divide-by-zero or indexing exceptions."""
        r = self._make_record("INV-SINGLE", date(2026, 6, 15), status="COMPLIANT")
        self.repo.add(r)

        report = self.service.generate_report()
        self.assertEqual(report.total_invoices_analyzed, 1)
        self.assertEqual(len(report.periods), 1)
        self.assertEqual(report.periods[0].compliance_rate, 100.0)
        self.assertEqual(report.trends[0].direction, TrendDirection.INSUFFICIENT_DATA)

    def test_boundary_missing_counterparty_and_rules(self):
        """Record with empty counterparty and no failed rules handles gracefully."""
        r = self._make_record("INV-NO-CP", date(2026, 6, 15), counterparty_gstin="", counterparty_name="")
        self.repo.add(r)

        profiles = self.service.get_counterparty_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].counterparty_id, "UNKNOWN_COUNTERPARTY")

    def test_boundary_duplicate_invoice_id_overwrite(self):
        """Duplicate invoice ID gracefully updates rather than corrupting repository index."""
        r1 = self._make_record("INV-DUP", date(2026, 6, 1), status="NON_COMPLIANT")
        r2 = self._make_record("INV-DUP", date(2026, 6, 1), status="COMPLIANT")  # updated run
        self.repo.add(r1)
        self.repo.add(r2)

        self.assertEqual(self.repo.count(), 1)
        retrieved = self.repo.get_by_invoice_id("INV-DUP")
        self.assertEqual(retrieved.compliance_status, "COMPLIANT")

    def test_boundary_two_periods(self):
        """Two periods: verifies boundary between exactly 2 periods calculates sequential trend without error."""
        r1 = self._make_record("INV-2P-1", date(2026, 5, 1), status="COMPLIANT")
        r2 = self._make_record("INV-2P-2", date(2026, 6, 1), status="COMPLIANT")
        self.repo.add_batch([r1, r2])

        trends = self.service.get_trends()
        self.assertEqual(len(trends), 2)
        self.assertEqual(trends[0].direction, TrendDirection.INSUFFICIENT_DATA)
        self.assertEqual(trends[1].direction, TrendDirection.STABLE)
        self.assertEqual(trends[1].current_period, "2026-06")
        self.assertEqual(trends[1].previous_period, "2026-05")

    def test_boundary_missing_dates(self):
        """Record with None invoice_date is handled gracefully by aggregators and repo without raising."""
        r = self._make_record("INV-NO-DATE", date(2023, 1, 1))
        r.invoice_date = None  # Force None
        self.repo.add(r)

        metrics = self.service.get_period_metrics()
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0].total_invoices, 1)

    def test_historical_record_fields_and_aliases(self):
        """Verify all Section 6 normalized historical record fields and properties are populated."""
        r = self._make_record("INV-FULL-FIELDS", date(2026, 6, 1), status="NEEDS_REVIEW", failed_rule_ids=["TAX_001"])
        r.confidence = 0.95
        r.risk_level = "MODERATE"
        r.risk_priority = "P3"

        self.assertEqual(r.invoice_id, "INV-FULL-FIELDS")
        self.assertEqual(r.transaction_type, "AP")
        self.assertEqual(r.direction, "AP")
        self.assertEqual(r.validation_status, "NEEDS_REVIEW")
        self.assertEqual(r.compliance_status, "NEEDS_REVIEW")
        self.assertEqual(r.failed_gates, [1])
        self.assertEqual(r.failed_rule_ids, ["TAX_001"])
        self.assertEqual(r.confidence, 0.95)
        self.assertEqual(r.risk_level, "MODERATE")
        self.assertEqual(r.risk_priority, "P3")

        d = r.to_dict()
        self.assertIn("transaction_type", d)
        self.assertIn("validation_status", d)
        self.assertIn("failed_gates", d)
        self.assertIn("confidence", d)

    def test_comprehensive_report_text_summary(self):
        """Verify to_text_summary() formatting produces required business summary."""
        r1 = self._make_record("INV-REP-1", date(2026, 5, 10), status="NON_COMPLIANT", failed_rule_ids=["TAX_001"])
        r2 = self._make_record("INV-REP-2", date(2026, 6, 10), status="COMPLIANT")
        self.repo.add_batch([r1, r2])

        report = self.service.generate_report()
        summary_text = report.to_text_summary()
        self.assertIn("UC15 GST Historical Intelligence", summary_text)
        self.assertIn("Invoices", summary_text)


if __name__ == "__main__":
    unittest.main()
