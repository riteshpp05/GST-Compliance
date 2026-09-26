"""
tests.unit.test_blast_radius_intelligence
=========================================
Unit test suite for Sprint 9 — Blast Radius Intelligence Engine.
Tests:
  1. Invoice count & ratio
  2. Counterparty count & top counterparty
  3. Rule count & top rule
  4. Period count & monthly distribution
  5. HSN count & top HSN
  6. State count & top state
  7. Financial exposure calculation (reconciled, zero double-counting)
  8. Risk distribution (reconciled from S3 risk truth)
  9. Duplicate overlap (reconciled from S7 duplicate truth)
  10. Anomaly overlap (reconciled from S7 anomaly truth)
  11. Concentration metrics calculation
  12. Temporal trend classification (expanding, contracting, stable, sudden onset)
  13. Systemic classification (isolated, concentrated, systemic, emerging systemic)
  14. Insufficient data handling
"""

import unittest
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models.impact import CalculationStatus, FinancialImpact, FinancialImpactType
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate
from app.intelligence.common.enums import DuplicateMatchType
from app.investigation.blast_radius.calculator import (
    calculate_financial_blast_radius,
    calculate_risk_blast_radius,
    classify_systemic_scope,
    classify_temporal_trend,
)
from app.investigation.blast_radius.engine import BlastRadiusEngine
from app.investigation.enums import SystemicClassification, TrendClassification
from app.investigation.evidence.collector import EvidenceCollector


def _make_inv(
    inv_id: str,
    date_str: str,
    cp_gstin: str,
    cp_name: str,
    hsn: str = "8409",
    pos: str = "Maharashtra",
    taxable_val: float = 50000.0,
) -> Invoice:
    return Invoice.from_record(
        invoice_no=inv_id,
        invoice_date=date_str,
        direction="AP",
        counterparty_gstin=cp_gstin,
        counterparty_name=cp_name,
        place_of_supply=pos,
        hsn_code=hsn,
        item_desc="Auto Components",
        taxable_value_inr=taxable_val,
        cgst_rate=9.0,
        sgst_rate=9.0,
        igst_rate=0.0,
        total_amt=taxable_val * 1.18,
        invoice_id=inv_id,
    )


def _make_decision(
    inv_id: str,
    date_str: str,
    cp_gstin: str,
    cp_name: str,
    failed_rule_ids: list[str],
    gate_nos: list[int],
    risk_level: str = "MEDIUM",
    priority: str = "P3",
    hsn: str = "8409",
    pos: str = "Maharashtra",
) -> ComplianceDecision:
    gates = [
        ValidationResult(
            rule_id=r,
            rule_name=r,
            status="FAIL",
            message=f"Discrepancy under {r}",
            gate_no=g,
        )
        for r, g in zip(failed_rule_ids, gate_nos)
    ]
    d = ComplianceDecision(
        invoice_no=inv_id,
        invoice_date=date_str,
        direction="AP",
        counterparty_gstin=cp_gstin,
        counterparty_name=cp_name,
        place_of_supply=pos,
        hsn_code=hsn,
        item_desc="Auto Components",
        taxable_value_inr=50000.0,
        total_amt=59000.0,
        gates=gates,
        failed_gate_count=len(gates),
        status="NON_COMPLIANT" if len(gates) >= 2 else "NEEDS_REVIEW",
        justification="Gate failure",
        recommended_action="Review invoice",
        sap_action="BLOCK_PAYMENT",
        audit_trail_ref=f"AUD-{inv_id}",
        hard_override=False,
    )
    d.risk_level = risk_level
    d.priority = priority
    return d


class TestBlastRadiusIntelligence(unittest.TestCase):
    """Test suite verifying Blast Radius Engine (Sprint 9)."""

    def setUp(self):
        self.collector = EvidenceCollector()
        self.engine = BlastRadiusEngine()

    def test_01_invoice_count_and_ratio(self):
        """1. Verify affected invoice count and population ratio."""
        invs = [_make_inv(f"INV-{i}", "2026-03-01", "27A", "Vendor A") for i in range(1, 11)]
        decs = [_make_decision(f"INV-{i}", "2026-03-01", "27A", "Vendor A", ["R1_GSTIN_STRUCTURE"], [1]) for i in range(1, 5)]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)

        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3", "INV-4"})
        self.assertEqual(profile.affected_invoice_count, 4)
        self.assertEqual(profile.total_population_count, 10)
        self.assertAlmostEqual(profile.affected_ratio, 0.40, places=2)

    def test_02_counterparty_count_and_top_share(self):
        """2. Verify counterparty count and top counterparty share calculation."""
        invs = [
            _make_inv("INV-1", "2026-03-01", "27A", "Vendor A"),
            _make_inv("INV-2", "2026-03-01", "27A", "Vendor A"),
            _make_inv("INV-3", "2026-03-01", "27A", "Vendor A"),
            _make_inv("INV-4", "2026-03-01", "29B", "Vendor B"),
        ]
        decs = [_make_decision(inv.invoice_id, "2026-03-01", inv.counterparty_gstin, inv.counterparty_name, ["R1_GSTIN_STRUCTURE"], [1]) for inv in invs]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)

        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3", "INV-4"})
        self.assertEqual(profile.affected_counterparty_count, 2)
        self.assertEqual(profile.top_counterparty_id, "27A")
        self.assertAlmostEqual(profile.top_counterparty_share, 0.75, places=2)

    def test_03_rule_count_and_top_rule(self):
        """3. Verify unique rule count and top rule share."""
        invs = [_make_inv(f"INV-{i}", "2026-03-01", "27A", "Vendor A") for i in range(1, 4)]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R6_ITC_ELIGIBILITY"], [6]),
            _make_decision("INV-2", "2026-03-01", "27A", "Vendor A", ["R6_ITC_ELIGIBILITY"], [6]),
            _make_decision("INV-3", "2026-03-01", "27A", "Vendor A", ["R3_TAX_RATE"], [3]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3"})

        self.assertEqual(profile.affected_rule_count, 2)
        self.assertEqual(profile.top_rule_id, "R6_ITC_ELIGIBILITY")
        self.assertAlmostEqual(profile.top_rule_share, 2 / 3, places=2)

    def test_04_period_count_and_monthly_distribution(self):
        """4. Verify period count, start/end dates, and monthly distribution."""
        invs = [
            _make_inv("INV-1", "2026-02-10", "27A", "Vendor A"),
            _make_inv("INV-2", "2026-03-10", "27A", "Vendor A"),
            _make_inv("INV-3", "2026-03-20", "27A", "Vendor A"),
            _make_inv("INV-4", "2026-04-05", "27A", "Vendor A"),
        ]
        decs = [_make_decision(inv.invoice_id, str(inv.invoice_date), "27A", "Vendor A", ["R1"], [1]) for inv in invs]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3", "INV-4"})

        self.assertEqual(profile.affected_period_count, 3)
        self.assertEqual(profile.first_detected_period, "2026-02")
        self.assertEqual(profile.last_detected_period, "2026-04")
        self.assertEqual(profile.period_distribution, {"2026-02": 1, "2026-03": 2, "2026-04": 1})

    def test_05_hsn_count_and_top_hsn(self):
        """5. Verify commodity code distribution."""
        invs = [
            _make_inv("INV-1", "2026-03-01", "27A", "Vendor A", hsn="8409"),
            _make_inv("INV-2", "2026-03-01", "27A", "Vendor A", hsn="8409"),
            _make_inv("INV-3", "2026-03-01", "27A", "Vendor A", hsn="8708"),
        ]
        decs = [_make_decision(inv.invoice_id, "2026-03-01", "27A", "Vendor A", ["R3"], [3], hsn=inv.hsn_sac) for inv in invs]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3"})

        self.assertEqual(profile.affected_hsn_count, 2)
        self.assertEqual(profile.top_hsn, "8409")
        self.assertAlmostEqual(profile.top_hsn_share, 2 / 3, places=2)

    def test_06_state_count_and_top_state(self):
        """6. Verify geographic state / POS distribution."""
        invs = [
            _make_inv("INV-1", "2026-03-01", "27A", "Vendor A", pos="Maharashtra"),
            _make_inv("INV-2", "2026-03-01", "27A", "Vendor A", pos="Maharashtra"),
            _make_inv("INV-3", "2026-03-01", "27A", "Vendor A", pos="Karnataka"),
        ]
        decs = [_make_decision(inv.invoice_id, "2026-03-01", "27A", "Vendor A", ["R4"], [4], pos=inv.place_of_supply) for inv in invs]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3"})

        self.assertEqual(profile.affected_state_count, 2)
        self.assertEqual(profile.top_state, "Maharashtra")
        self.assertAlmostEqual(profile.top_state_share, 2 / 3, places=2)

    def test_07_financial_exposure_reconciliation(self):
        """7. Verify financial exposure sums strictly from S6 truth without double counting."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        fi1 = FinancialImpact(
            impact_id="FI-1",
            invoice_id="INV-1",
            impact_type=FinancialImpactType.ITC_EXPOSURE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("6300.00"),
        )
        fi2 = FinancialImpact(
            impact_id="FI-2",
            invoice_id="INV-2",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("3500.00"),
        )
        ctx = self.collector.collect_context(invoices=invs, financial_impacts=[fi1, fi2])
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2"})

        self.assertEqual(profile.total_potential_exposure, Decimal("9800.00"))
        self.assertEqual(profile.average_exposure, Decimal("4900.00"))
        self.assertEqual(profile.maximum_exposure, Decimal("6300.00"))
        self.assertEqual(profile.exposure_by_type["ITC_EXPOSURE"], Decimal("6300.00"))
        self.assertEqual(profile.exposure_by_type["TAX_RATE_DIFFERENCE"], Decimal("3500.00"))

    def test_08_risk_distribution_reconciliation(self):
        """8. Verify risk severity and priority distributions match S3 inputs."""
        invs = [_make_inv(f"INV-{i}", "2026-03-01", "27A", "Vendor A") for i in range(1, 4)]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R1"], [1], risk_level="CRITICAL", priority="P1"),
            _make_decision("INV-2", "2026-03-01", "27A", "Vendor A", ["R1"], [1], risk_level="HIGH", priority="P2"),
            _make_decision("INV-3", "2026-03-01", "27A", "Vendor A", ["R1"], [1], risk_level="MEDIUM", priority="P3"),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2", "INV-3"})

        self.assertEqual(profile.severity_distribution["CRITICAL"], 1)
        self.assertEqual(profile.severity_distribution["HIGH"], 1)
        self.assertEqual(profile.severity_distribution["MEDIUM"], 1)
        self.assertEqual(profile.priority_distribution["P1"], 1)
        self.assertEqual(profile.priority_distribution["P2"], 1)
        self.assertEqual(profile.priority_distribution["P3"], 1)

    def test_09_duplicate_overlap(self):
        """9. Verify duplicate candidate presence and linkage."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        cand = DuplicateCandidate(
            candidate_id="DUP-CAND-01",
            source_invoice_id="INV-1",
            matched_invoice_id="INV-2",
            match_type=DuplicateMatchType.EXACT_DUPLICATE,
        )
        ctx = self.collector.collect_context(invoices=invs, duplicate_candidates=[cand])
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2"})

        self.assertEqual(profile.duplicate_affected_count, 2)
        self.assertIn("DUP-CAND-01", profile.duplicate_candidate_ids)

    def test_10_anomaly_overlap(self):
        """10. Verify statistical anomaly presence and compound overlap with duplicates."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        cand = DuplicateCandidate(
            candidate_id="DUP-CAND-01",
            source_invoice_id="INV-1",
            matched_invoice_id="INV-2",
            match_type=DuplicateMatchType.EXACT_DUPLICATE,
        )
        anom = AnomalyFinding(
            finding_id="ANOM-01",
            invoice_id="INV-1",
        )
        ctx = self.collector.collect_context(invoices=invs, duplicate_candidates=[cand], anomaly_findings=[anom])
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={"INV-1", "INV-2"})

        self.assertEqual(profile.duplicate_affected_count, 2)
        self.assertEqual(profile.anomaly_affected_count, 1)
        # Compound overlap: INV-1 has BOTH duplicate candidate and anomaly
        self.assertEqual(profile.duplicate_and_anomaly_overlap_count, 1)

    def test_11_concentration_metrics(self):
        """11. Verify concentration metrics when single counterparty dominates."""
        invs = [_make_inv(f"INV-{i}", "2026-03-01", "27A", "Vendor A") for i in range(1, 10)] + [
            _make_inv("INV-10", "2026-03-01", "27B", "Vendor B")
        ]
        decs = [_make_decision(inv.invoice_id, "2026-03-01", inv.counterparty_gstin, inv.counterparty_name, ["R1"], [1]) for inv in invs]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        profile = self.engine.calculate_profile(ctx, target_invoice_ids={inv.invoice_id for inv in invs})

        self.assertEqual(profile.top_counterparty_id, "27A")
        self.assertAlmostEqual(profile.top_counterparty_share, 0.90, places=2)

    def test_12_temporal_trend_classification(self):
        """12. Verify temporal trend classifications: expanding, contracting, stable, sudden onset."""
        # Expanding: 10 -> 25 -> 50
        trend_exp = classify_temporal_trend({"2026-01": 10, "2026-02": 25, "2026-03": 50})
        self.assertEqual(trend_exp, TrendClassification.EXPANDING)

        # Contracting: 50 -> 25 -> 10
        trend_con = classify_temporal_trend({"2026-01": 50, "2026-02": 25, "2026-03": 10})
        self.assertEqual(trend_con, TrendClassification.CONTRACTING)

        # Stable: 20 -> 21 -> 20
        trend_sta = classify_temporal_trend({"2026-01": 20, "2026-02": 21, "2026-03": 20})
        self.assertEqual(trend_sta, TrendClassification.STABLE)

        # Sudden onset: 0 -> 0 -> 40
        trend_sud = classify_temporal_trend({"2026-01": 0, "2026-02": 1, "2026-03": 40})
        self.assertEqual(trend_sud, TrendClassification.SUDDEN_ONSET)

    def test_13_systemic_classification(self):
        """13. Verify systemic boundary classifications: isolated, concentrated, systemic."""
        # Isolated: 1 invoice, 1 vendor
        cls_iso = classify_systemic_scope(
            affected_count=1,
            total_portfolio_count=100,
            counterparty_count=1,
            period_count=1,
            rule_count=1,
            top_counterparty_share=1.0,
            top_rule_share=1.0,
            trend=TrendClassification.STABLE,
        )
        self.assertEqual(cls_iso, SystemicClassification.ISOLATED)

        # Concentrated: 10 invoices, 1 vendor (100% share)
        cls_conc = classify_systemic_scope(
            affected_count=10,
            total_portfolio_count=100,
            counterparty_count=1,
            period_count=2,
            rule_count=1,
            top_counterparty_share=1.0,
            top_rule_share=1.0,
            trend=TrendClassification.STABLE,
        )
        self.assertEqual(cls_conc, SystemicClassification.CONCENTRATED)

        # Systemic: 20 invoices, 4 vendors, 3 periods
        cls_sys = classify_systemic_scope(
            affected_count=20,
            total_portfolio_count=100,
            counterparty_count=4,
            period_count=3,
            rule_count=2,
            top_counterparty_share=0.35,
            top_rule_share=0.40,
            trend=TrendClassification.STABLE,
        )
        self.assertEqual(cls_sys, SystemicClassification.SYSTEMIC)

        # Emerging Systemic: expanding trend across multiple periods
        cls_emg = classify_systemic_scope(
            affected_count=8,
            total_portfolio_count=100,
            counterparty_count=2,
            period_count=2,
            rule_count=1,
            top_counterparty_share=0.50,
            top_rule_share=0.50,
            trend=TrendClassification.EXPANDING,
        )
        self.assertEqual(cls_emg, SystemicClassification.EMERGING_SYSTEMIC)

    def test_14_insufficient_data(self):
        """14. Verify insufficient data handling for empty or 1-period sets."""
        trend_insuf = classify_temporal_trend({"2026-03": 5})
        self.assertEqual(trend_insuf, TrendClassification.INSUFFICIENT_DATA)

        cls_insuf = classify_systemic_scope(
            affected_count=0,
            total_portfolio_count=100,
            counterparty_count=0,
            period_count=0,
            rule_count=0,
            top_counterparty_share=0.0,
            top_rule_share=0.0,
            trend=TrendClassification.INSUFFICIENT_DATA,
        )
        self.assertEqual(cls_insuf, SystemicClassification.INSUFFICIENT_DATA)


if __name__ == "__main__":
    unittest.main()
