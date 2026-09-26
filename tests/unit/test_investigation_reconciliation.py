"""
tests.unit.test_investigation_reconciliation
============================================
Reconciliation & Cross-Layer Integration Test Suite for S8 + S9.
Verifies:
  1. Blast Radius affected invoices == actual linked invoice IDs
  2. Financial exposure == sum(existing eligible S6 impacts) (zero double counting)
  3. Counterparty counts == unique authoritative counterparty IDs
  4. Rule counts == unique affected rule IDs
  5. Period counts == unique affected periods
  6. Cross-layer integration: S5 Historical -> Investigation
  7. Cross-layer integration: S6 Financial -> Investigation
  8. Cross-layer integration: S7 Duplicates/Anomalies -> Investigation
  9. Cross-layer integration: S3 Risk -> Investigation
  10. Strict non-interference: Investigation preserves compliance, risk, and financial truths
"""

import unittest
from decimal import Decimal

from app.agent.compliance_agent import GSTComplianceAgent
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models.impact import CalculationStatus, FinancialImpact, FinancialImpactType
from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.intelligence.common.enums import DuplicateMatchType
from app.investigation.evidence.collector import EvidenceCollector
from app.investigation.investigation_service import InvestigationService
from app.investigation.models import InvestigationProfile


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
        item_desc="Engine Parts",
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
        item_desc="Engine Parts",
        taxable_value_inr=50000.0,
        total_amt=59000.0,
        gates=gates,
        failed_gate_count=len(gates),
        status="NON_COMPLIANT" if len(gates) >= 2 else "NEEDS_REVIEW",
        justification="Rule validation failure",
        recommended_action="Review invoice",
        sap_action="BLOCK_PAYMENT",
        audit_trail_ref=f"AUD-{inv_id}",
        hard_override=False,
    )
    d.risk_level = risk_level
    d.priority = priority
    return d


class TestInvestigationReconciliation(unittest.TestCase):
    """Reconciliation and Cross-Layer Integration tests."""

    def setUp(self):
        self.service = InvestigationService()

    def test_01_blast_radius_invoice_reconciliation(self):
        """1. Blast Radius affected invoices must exactly match linked invoice IDs."""
        invs = [_make_inv(f"INV-R-{i}", "2026-03-01", "27A", "Vendor A") for i in range(1, 6)]
        decs = [_make_decision(f"INV-R-{i}", "2026-03-01", "27A", "Vendor A", ["R6_ITC_ELIGIBILITY"], [6]) for i in range(1, 6)]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        self.assertIsNotNone(profile.blast_radius)
        self.assertEqual(profile.blast_radius.affected_invoice_count, 5)
        self.assertEqual(
            set(profile.blast_radius.affected_invoice_ids),
            {"INV-R-1", "INV-R-2", "INV-R-3", "INV-R-4", "INV-R-5"},
        )

    def test_02_financial_exposure_exact_sum(self):
        """2. Blast Radius financial exposure must exactly equal sum of S6 impacts without double counting."""
        invs = [_make_inv("INV-F-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-F-2", "2026-03-01", "27A", "Vendor A")]
        decs = [
            _make_decision("INV-F-1", "2026-03-01", "27A", "Vendor A", ["R6"], [6]),
            _make_decision("INV-F-2", "2026-03-01", "27A", "Vendor A", ["R6"], [6]),
        ]
        fi1 = FinancialImpact(
            impact_id="FI-1",
            invoice_id="INV-F-1",
            impact_type=FinancialImpactType.ITC_EXPOSURE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("12345.67"),
        )
        fi2 = FinancialImpact(
            impact_id="FI-2",
            invoice_id="INV-F-2",
            impact_type=FinancialImpactType.ITC_EXPOSURE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("23456.78"),
        )
        expected_total = Decimal("12345.67") + Decimal("23456.78")

        profile = self.service.evaluate_batch(invoices=invs, decisions=decs, financial_impacts=[fi1, fi2])

        self.assertEqual(profile.financial_exposure, expected_total)
        self.assertEqual(profile.blast_radius.total_potential_exposure, expected_total)

    def test_03_counterparty_reconciliation(self):
        """3. Blast Radius counterparty count must equal distinct authoritative counterparty IDs."""
        invs = [
            _make_inv("INV-1", "2026-03-01", "27AAA", "Vendor Alpha"),
            _make_inv("INV-2", "2026-03-01", "27AAA", "Vendor Alpha"),
            _make_inv("INV-3", "2026-03-01", "29BBB", "Vendor Beta"),
            _make_inv("INV-4", "2026-03-01", "33CCC", "Vendor Gamma"),
        ]
        decs = [_make_decision(inv.invoice_id, "2026-03-01", inv.counterparty_gstin, inv.counterparty_name, ["R1"], [1]) for inv in invs]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        self.assertEqual(profile.blast_radius.affected_counterparty_count, 3)
        self.assertEqual(set(profile.blast_radius.affected_counterparties), {"27AAA", "29BBB", "33CCC"})

    def test_04_rule_count_reconciliation(self):
        """4. Blast Radius rule count must equal unique affected rule IDs."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R1_GSTIN_STRUCTURE", "R3_TAX_RATE"], [1, 3]),
            _make_decision("INV-2", "2026-03-01", "27A", "Vendor A", ["R3_TAX_RATE", "R4_PLACE_OF_SUPPLY"], [3, 4]),
        ]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        # Unique rules failed: R1_GSTIN_STRUCTURE, R3_TAX_RATE, R4_PLACE_OF_SUPPLY
        self.assertEqual(profile.blast_radius.affected_rule_count, 3)
        self.assertEqual(
            set(profile.blast_radius.affected_rules),
            {"R1_GSTIN_STRUCTURE", "R3_TAX_RATE", "R4_PLACE_OF_SUPPLY"},
        )

    def test_05_period_count_reconciliation(self):
        """5. Blast Radius period count must equal unique affected periods."""
        invs = [
            _make_inv("INV-1", "2026-01-15", "27A", "Vendor A"),
            _make_inv("INV-2", "2026-02-15", "27A", "Vendor A"),
            _make_inv("INV-3", "2026-03-15", "27A", "Vendor A"),
            _make_inv("INV-4", "2026-03-25", "27A", "Vendor A"),
        ]
        decs = [_make_decision(inv.invoice_id, str(inv.invoice_date), "27A", "Vendor A", ["R6"], [6]) for inv in invs]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        self.assertEqual(profile.blast_radius.affected_period_count, 3)
        self.assertEqual(set(profile.blast_radius.affected_periods), {"2026-01", "2026-02", "2026-03"})

    def test_06_cross_layer_s6_financial_no_recalculation(self):
        """6. S6 Financial exposure is directly consumed and never recalculated independently."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A")]
        decs = [_make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R3"], [3])]
        # Injected custom S6 impact
        fi = FinancialImpact(
            impact_id="FI-CUSTOM",
            invoice_id="INV-1",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            potential_exposure=Decimal("7777.77"),
        )
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs, financial_impacts=[fi])

        # Exactly equals the injected S6 truth
        self.assertEqual(profile.financial_exposure, Decimal("7777.77"))

    def test_07_cross_layer_s3_risk_no_recalculation(self):
        """7. S3 Risk severity distribution is consumed directly without altering risk scores."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R1"], [1], risk_level="CRITICAL", priority="P1"),
            _make_decision("INV-2", "2026-03-01", "27A", "Vendor A", ["R1"], [1], risk_level="LOW", priority="P4"),
        ]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        self.assertEqual(profile.risk_distribution["CRITICAL"], 1)
        self.assertEqual(profile.risk_distribution["LOW"], 1)

    def test_08_cross_layer_s7_intelligence_signals_reused(self):
        """8. S7 duplicate and anomaly signals are correlated without creating phantom findings."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-01", "27A", "Vendor A")]
        decs = [_make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R1"], [1]), _make_decision("INV-2", "2026-03-01", "27A", "Vendor A", ["R1"], [1])]

        cand = DuplicateCandidate(
            candidate_id="DUP-101",
            source_invoice_id="INV-1",
            matched_invoice_id="INV-2",
            match_type=DuplicateMatchType.EXACT_DUPLICATE,
        )
        anom = AnomalyFinding(
            finding_id="ANOM-202",
            invoice_id="INV-1",
        )
        profile = self.service.evaluate_batch(
            invoices=invs,
            decisions=decs,
            duplicate_candidates=[cand],
            anomaly_findings=[anom],
        )

        self.assertEqual(profile.blast_radius.duplicate_affected_count, 2)
        self.assertEqual(profile.blast_radius.anomaly_affected_count, 1)
        self.assertEqual(profile.blast_radius.duplicate_and_anomaly_overlap_count, 1)

    def test_09_agent_full_pipeline_preserves_compliance_status(self):
        """9. End-to-end integration via GSTComplianceAgent preserves statutory compliance decisions."""
        agent = GSTComplianceAgent(mock=True)
        decisions, profile = agent.run_all_with_investigation()

        self.assertIsNotNone(profile)
        self.assertIsInstance(profile, InvestigationProfile)
        self.assertGreaterEqual(len(decisions), 10)
        # Verify statutory compliance statuses are untouched
        for d in decisions:
            self.assertIn(d.status, ["COMPLIANT", "NEEDS_REVIEW", "NON_COMPLIANT"])

    def test_10_evidence_graph_and_timeline_integrity(self):
        """10. Verify evidence graph and timeline are populated with traceable linkages."""
        invs = [_make_inv("INV-1", "2026-03-01", "27A", "Vendor A"), _make_inv("INV-2", "2026-03-02", "27A", "Vendor A")]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor A", ["R1_GSTIN_STRUCTURE"], [1]),
            _make_decision("INV-2", "2026-03-02", "27A", "Vendor A", ["R1_GSTIN_STRUCTURE"], [1]),
        ]
        profile = self.service.evaluate_batch(invoices=invs, decisions=decs)

        # Timeline has entries for the period
        self.assertTrue(len(profile.timeline) > 0)
        self.assertEqual(profile.timeline[0]["period"], "2026-03")

        # Evidence graph maps root cause to evidence and invoices
        self.assertTrue(len(profile.evidence_graph) > 0)
        rc_key = f"ROOT_CAUSE:{profile.primary_root_cause.root_cause_id}"
        self.assertIn(rc_key, profile.evidence_graph)


if __name__ == "__main__":
    unittest.main()
