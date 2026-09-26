"""
tests.unit.test_root_cause_intelligence
=======================================
Unit test suite for Sprint 8 — Root Cause Intelligence Engine.
Tests:
  1. Single-rule recurring failure
  2. Multi-rule recurring failure
  3. Counterparty concentration
  4. Temporal recurrence
  5. HSN concentration
  6. Data-quality root cause
  7. Duplicate-process root cause
  8. Tax configuration root cause
  9. Multiple root-cause candidates
  10. Insufficient evidence handling
  11. Causality-safe terminology enforcement
  12. Root cause score determinism
"""

import unittest
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.models.impact import CalculationStatus, FinancialImpact, FinancialImpactType
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.intelligence.common.enums import DuplicateMatchType
from app.investigation.enums import (
    EvidenceType,
    RootCauseConfidence,
    RootCauseLikelihood,
    RootCauseStatus,
    RootCauseType,
)
from app.investigation.evidence.collector import EvidenceCollector
from app.investigation.models import RootCauseEvidence, RootCauseFinding, RootCauseScore
from app.investigation.root_cause.candidates import CandidateGenerator
from app.investigation.root_cause.engine import RootCauseEngine
from app.investigation.root_cause.scorer import RootCauseScorer


def _make_inv(
    inv_id: str,
    date_str: str,
    cp_gstin: str,
    cp_name: str,
    hsn: str = "8409",
    pos: str = "Maharashtra",
    item_desc: str = "Engine Components",
) -> Invoice:
    return Invoice.from_record(
        invoice_no=inv_id,
        invoice_date=date_str,
        direction="AP",
        counterparty_gstin=cp_gstin,
        counterparty_name=cp_name,
        place_of_supply=pos,
        hsn_code=hsn,
        item_desc=item_desc,
        taxable_value_inr=50000.0,
        cgst_rate=9.0,
        sgst_rate=9.0,
        igst_rate=0.0,
        total_amt=59000.0,
        invoice_id=inv_id,
    )


def _make_decision(
    inv_id: str,
    date_str: str,
    cp_gstin: str,
    cp_name: str,
    failed_rule_ids: list[str],
    gate_nos: list[int],
    status: str = "NON_COMPLIANT",
    hsn: str = "8409",
    pos: str = "Maharashtra",
) -> ComplianceDecision:
    gates = []
    for r_id, g_no in zip(failed_rule_ids, gate_nos):
        gates.append(
            ValidationResult(
                rule_id=r_id,
                rule_name=r_id,
                status="FAIL",
                message=f"Discrepancy observed under {r_id}",
                gate_no=g_no,
            )
        )
    return ComplianceDecision(
        invoice_no=inv_id,
        invoice_date=date_str,
        direction="AP",
        counterparty_gstin=cp_gstin,
        counterparty_name=cp_name,
        place_of_supply=pos,
        hsn_code=hsn,
        item_desc="Engine Components",
        taxable_value_inr=50000.0,
        total_amt=59000.0,
        gates=gates,
        failed_gate_count=len(gates),
        status=status,
        justification="Rule validation failure",
        recommended_action="Review and adjust invoice",
        sap_action="BLOCK_PAYMENT",
        audit_trail_ref=f"AUD-{inv_id}",
        hard_override=False,
    )


class TestRootCauseIntelligence(unittest.TestCase):
    """Test suite verifying deterministic behavior of Root Cause Engine (Sprint 8)."""

    def setUp(self):
        self.collector = EvidenceCollector()
        self.scorer = RootCauseScorer()
        self.candidate_gen = CandidateGenerator(scorer=self.scorer)
        self.engine = RootCauseEngine(candidate_generator=self.candidate_gen, scorer=self.scorer)

    def test_01_single_rule_recurring_failure(self):
        """1. Single-rule recurring failure should generate a focused candidate with rule evidence."""
        invs = [
            _make_inv(f"INV-ITC-{i}", "2026-03-10", "27AAACB1234A1Z5", "Vendor Alfa")
            for i in range(1, 5)
        ]
        decs = [
            _make_decision(f"INV-ITC-{i}", "2026-03-10", "27AAACB1234A1Z5", "Vendor Alfa", ["R6_ITC_ELIGIBILITY"], [6])
            for i in range(1, 5)
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, candidates = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.ITC_PROCESS)
        self.assertEqual(len(primary.affected_invoice_ids), 4)
        rule_evid = [e for e in primary.evidence if e.evidence_type == EvidenceType.RULE_FAILURE_PATTERN]
        self.assertTrue(len(rule_evid) > 0)
        self.assertIn("R6_ITC_ELIGIBILITY", rule_evid[0].title)

    def test_02_multi_rule_recurring_failure(self):
        """2. Multi-rule recurring failure generates distinct candidates with primary and contributing separation."""
        invs = [
            _make_inv("INV-M-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor A"),
            _make_inv("INV-M-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor A"),
            _make_inv("INV-M-3", "2026-03-03", "27AAACB1234A1Z5", "Vendor A"),
            _make_inv("INV-M-4", "2026-03-04", "27AAACB1234A1Z5", "Vendor A"),
        ]
        # Invoices fail both Gate 3 (Tax Rate) and Gate 4 (Place of Supply)
        decs = [
            _make_decision("INV-M-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor A", ["R3_TAX_RATE"], [3]),
            _make_decision("INV-M-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor A", ["R3_TAX_RATE"], [3]),
            _make_decision("INV-M-3", "2026-03-03", "27AAACB1234A1Z5", "Vendor A", ["R4_PLACE_OF_SUPPLY"], [4]),
            _make_decision("INV-M-4", "2026-03-04", "27AAACB1234A1Z5", "Vendor A", ["R4_PLACE_OF_SUPPLY"], [4]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, candidates = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertGreaterEqual(len(candidates), 2)
        cause_types = {c.root_cause_type for c in candidates}
        self.assertIn(RootCauseType.TAX_RATE_CONFIGURATION, cause_types)
        self.assertIn(RootCauseType.PLACE_OF_SUPPLY, cause_types)

    def test_03_counterparty_concentration(self):
        """3. Counterparty concentration identifies high vendor share and builds counterparty evidence."""
        # 10 invoices: 8 from Vendor Concentrated, 2 from Vendor Other
        invs = [
            _make_inv(f"INV-CC-{i}", "2026-03-01", "27AAACB1234A1Z5", "Concentrated Corp")
            for i in range(1, 9)
        ] + [
            _make_inv("INV-CC-9", "2026-03-01", "27BBBCB5678B1Z2", "Other Corp"),
            _make_inv("INV-CC-10", "2026-03-01", "27BBBCB5678B1Z2", "Other Corp"),
        ]
        decs = [
            _make_decision(f"INV-CC-{i}", "2026-03-01", "27AAACB1234A1Z5", "Concentrated Corp", ["R1_GSTIN_STRUCTURE"], [1])
            for i in range(1, 9)
        ] + [
            _make_decision("INV-CC-9", "2026-03-01", "27BBBCB5678B1Z2", "Other Corp", ["R1_GSTIN_STRUCTURE"], [1]),
            _make_decision("INV-CC-10", "2026-03-01", "27BBBCB5678B1Z2", "Other Corp", ["R1_GSTIN_STRUCTURE"], [1]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, _ = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.MASTER_DATA)
        # Top counterparty share should be 8/10 = 80%
        cp_evids = [e for e in primary.evidence if e.evidence_type == EvidenceType.COUNTERPARTY_PATTERN]
        self.assertTrue(len(cp_evids) > 0)
        self.assertAlmostEqual(cp_evids[0].metrics["concentration_share"], 0.80, places=2)

    def test_04_temporal_recurrence(self):
        """4. Discrepancies across multiple months create temporal evidence."""
        invs = [
            _make_inv("INV-T-1", "2026-03-15", "27AAACB1234A1Z5", "Vendor Alpha"),
            _make_inv("INV-T-2", "2026-04-15", "27AAACB1234A1Z5", "Vendor Alpha"),
            _make_inv("INV-T-3", "2026-05-15", "27AAACB1234A1Z5", "Vendor Alpha"),
        ]
        decs = [
            _make_decision("INV-T-1", "2026-03-15", "27AAACB1234A1Z5", "Vendor Alpha", ["R6_ITC_ELIGIBILITY"], [6]),
            _make_decision("INV-T-2", "2026-04-15", "27AAACB1234A1Z5", "Vendor Alpha", ["R6_ITC_ELIGIBILITY"], [6]),
            _make_decision("INV-T-3", "2026-05-15", "27AAACB1234A1Z5", "Vendor Alpha", ["R6_ITC_ELIGIBILITY"], [6]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, _ = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        temp_evids = [e for e in primary.evidence if e.evidence_type == EvidenceType.TEMPORAL_PATTERN]
        self.assertTrue(len(temp_evids) > 0)
        self.assertEqual(temp_evids[0].metrics["duration_months"], 3)
        self.assertEqual(temp_evids[0].metrics["first_period"], "2026-03")
        self.assertEqual(temp_evids[0].metrics["last_period"], "2026-05")

    def test_05_hsn_concentration(self):
        """5. Tax rate mismatches concentrated in an HSN code."""
        invs = [
            _make_inv("INV-H-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha", hsn="8409"),
            _make_inv("INV-H-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Alpha", hsn="8409"),
            _make_inv("INV-H-3", "2026-03-03", "27AAACB1234A1Z5", "Vendor Alpha", hsn="8409"),
        ]
        decs = [
            _make_decision("INV-H-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha", ["R3_TAX_RATE"], [3], hsn="8409"),
            _make_decision("INV-H-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Alpha", ["R3_TAX_RATE"], [3], hsn="8409"),
            _make_decision("INV-H-3", "2026-03-03", "27AAACB1234A1Z5", "Vendor Alpha", ["R3_TAX_RATE"], [3], hsn="8409"),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, _ = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.TAX_RATE_CONFIGURATION)
        self.assertEqual(len(primary.affected_invoice_ids), 3)

    def test_06_data_quality_root_cause(self):
        """6. Unclassified failures without dominant statutory rule fall back gracefully with safe classification."""
        invs = [_make_inv("INV-DQ-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor X")]
        decs = [_make_decision("INV-DQ-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor X", ["CUSTOM_DATA_ERROR"], [99])]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, candidates = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.UNKNOWN)
        self.assertEqual(primary.status, RootCauseStatus.INSUFFICIENT_EVIDENCE)

    def test_07_duplicate_process_root_cause(self):
        """7. S7 duplicate clusters generate DUPLICATE_PROCESS candidate."""
        invs = [
            _make_inv("INV-DUP-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Dup"),
            _make_inv("INV-DUP-2", "2026-03-01", "27AAACB1234A1Z5", "Vendor Dup"),
        ]
        decs = [
            _make_decision("INV-DUP-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Dup", [], []),
            _make_decision("INV-DUP-2", "2026-03-01", "27AAACB1234A1Z5", "Vendor Dup", [], []),
        ]
        cand = DuplicateCandidate(
            source_invoice_id="INV-DUP-1",
            matched_invoice_id="INV-DUP-2",
            match_type=DuplicateMatchType.EXACT_DUPLICATE,
            similarity_score=100.0,
        )
        clust = DuplicateCluster(cluster_id="CLUST-01", invoice_ids=["INV-DUP-1", "INV-DUP-2"])

        ctx = self.collector.collect_context(
            invoices=invs,
            decisions=decs,
            duplicate_candidates=[cand],
            duplicate_clusters=[clust],
        )
        primary, candidates = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.DUPLICATE_PROCESS)
        self.assertIn("INV-DUP-1", primary.affected_invoice_ids)
        self.assertIn("INV-DUP-2", primary.affected_invoice_ids)

    def test_08_tax_configuration_root_cause(self):
        """8. Statutory tax rate differences trigger TAX_RATE_CONFIGURATION with financial exposure."""
        invs = [
            _make_inv("INV-TAX-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Rate"),
            _make_inv("INV-TAX-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Rate"),
        ]
        decs = [
            _make_decision("INV-TAX-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Rate", ["R3_TAX_RATE"], [3]),
            _make_decision("INV-TAX-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Rate", ["R3_TAX_RATE"], [3]),
        ]
        fi1 = FinancialImpact(
            impact_id="FI-TAX-1",
            invoice_id="INV-TAX-1",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("4500.00"),
        )
        fi2 = FinancialImpact(
            impact_id="FI-TAX-2",
            invoice_id="INV-TAX-2",
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.CALCULATED,
            potential_exposure=Decimal("4500.00"),
        )
        ctx = self.collector.collect_context(invoices=invs, decisions=decs, financial_impacts=[fi1, fi2])
        primary, _ = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.root_cause_type, RootCauseType.TAX_RATE_CONFIGURATION)
        self.assertEqual(primary.financial_exposure, Decimal("9000.00"))

    def test_09_multiple_root_cause_candidates(self):
        """9. Multi-issue population correctly produces ranked candidates without forcing one cause."""
        invs = [
            _make_inv("INV-1", "2026-03-01", "27A", "Vendor 1"),
            _make_inv("INV-2", "2026-03-02", "27A", "Vendor 1"),
            _make_inv("INV-3", "2026-03-03", "27B", "Vendor 2"),
            _make_inv("INV-4", "2026-03-04", "27B", "Vendor 2"),
        ]
        decs = [
            _make_decision("INV-1", "2026-03-01", "27A", "Vendor 1", ["R1_GSTIN_STRUCTURE"], [1]),
            _make_decision("INV-2", "2026-03-02", "27A", "Vendor 1", ["R1_GSTIN_STRUCTURE"], [1]),
            _make_decision("INV-3", "2026-03-03", "27B", "Vendor 2", ["R5_EWAY_BILL"], [5]),
            _make_decision("INV-4", "2026-03-04", "27B", "Vendor 2", ["R5_EWAY_BILL"], [5]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, candidates = self.engine.analyze(ctx)

        self.assertEqual(len(candidates), 2)
        # Scores should be sorted descending
        self.assertGreaterEqual(candidates[0].score.total_score, candidates[1].score.total_score)

    def test_10_insufficient_evidence(self):
        """10. Population below minimum sample size results in INSUFFICIENT_EVIDENCE confidence."""
        invs = [_make_inv("INV-SOLO-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Solo")]
        decs = [_make_decision("INV-SOLO-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Solo", ["R1_GSTIN_STRUCTURE"], [1])]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, candidates = self.engine.analyze(ctx)

        self.assertIsNotNone(primary)
        self.assertEqual(primary.confidence, RootCauseConfidence.INSUFFICIENT_EVIDENCE)
        self.assertEqual(primary.status, RootCauseStatus.INSUFFICIENT_EVIDENCE)

    def test_11_causality_safety(self):
        """11. Causality-safe phrasing: verify statements do not accuse vendors or assert absolute blame."""
        invs = [
            _make_inv("INV-C-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha"),
            _make_inv("INV-C-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Alpha"),
        ]
        decs = [
            _make_decision("INV-C-1", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha", ["R1_GSTIN_STRUCTURE"], [1]),
            _make_decision("INV-C-2", "2026-03-02", "27AAACB1234A1Z5", "Vendor Alpha", ["R1_GSTIN_STRUCTURE"], [1]),
        ]
        ctx = self.collector.collect_context(invoices=invs, decisions=decs)
        primary, _ = self.engine.analyze(ctx)

        stmt = primary.causality_statement.lower()
        # Must NOT contain accusatory claims
        self.assertNotIn("caused the issue", stmt)
        self.assertNotIn("vendor is at fault", stmt)
        self.assertNotIn("fraud", stmt)
        # Must contain safe language
        self.assertIn("consistent with", stmt)

    def test_12_root_cause_score_determinism(self):
        """12. Root Cause scoring is deterministic, bounded [0, 100], and reproducible across executions."""
        invs = [
            _make_inv(f"INV-D-{i}", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha")
            for i in range(1, 6)
        ]
        decs = [
            _make_decision(f"INV-D-{i}", "2026-03-01", "27AAACB1234A1Z5", "Vendor Alpha", ["R4_PLACE_OF_SUPPLY"], [4])
            for i in range(1, 6)
        ]
        ctx1 = self.collector.collect_context(invoices=invs, decisions=decs)
        primary1, _ = self.engine.analyze(ctx1)

        ctx2 = self.collector.collect_context(invoices=invs, decisions=decs)
        primary2, _ = self.engine.analyze(ctx2)

        self.assertEqual(primary1.score.total_score, primary2.score.total_score)
        self.assertGreaterEqual(primary1.score.total_score, 0.0)
        self.assertLessEqual(primary1.score.total_score, 100.0)


if __name__ == "__main__":
    unittest.main()
