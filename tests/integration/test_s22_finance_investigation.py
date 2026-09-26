"""
UC15 GST Compliance Agent — Sprint 22 Integration Tests
Verifies end-to-end finance investigation workflows, HumanReviewPackage assembly, and 12 synthetic scenarios.
"""
import unittest

from app.case.models import InvestigationCase, CaseStatusEnum
from app.case.service import get_case_service
from app.case.review_package import get_human_review_package, HumanReviewPackage
from app.investigation.evidence.sufficiency_evaluator import EvidenceSufficiencyEvaluator
from app.reconciliation.engine import ReconciliationEngine
from tests.fixtures.synthetic_finance_datasets import SYNTHETIC_FINANCE_SCENARIOS


class TestS22FinanceInvestigationIntegration(unittest.TestCase):

    def setUp(self):
        self.case_svc = get_case_service()

    def test_all_12_synthetic_scenarios_execution(self):
        for scenario in SYNTHETIC_FINANCE_SCENARIOS:
            with self.subTest(scenario=scenario.scenario_id):
                # 1. Create case in case service
                case_id = f"CASE-{scenario.scenario_id}"
                case = self.case_svc.create_case(
                    title=scenario.title,
                    description=scenario.description,
                    source="SYNTHETIC_TEST",
                )

                # 2. Assemble HumanReviewPackage
                pkg = get_human_review_package(case_id=case.case_id)
                self.assertIsInstance(pkg, HumanReviewPackage)
                self.assertEqual(pkg.case_id, case.case_id)

                # 3. Verify Sprint 22 extension structures exist
                self.assertIn("overall_status", pkg.reconciliation_summary)
                self.assertIn("sufficiency_state", pkg.evidence_sufficiency)
                self.assertIn("what_was_detected", pkg.ai_dossier_6part)
                self.assertIn("financial_impact", pkg.ai_dossier_6part)
                self.assertIn("missing_evidence", pkg.ai_dossier_6part)

    def test_evidence_sufficiency_evaluation(self):
        evaluator = EvidenceSufficiencyEvaluator()
        report = evaluator.evaluate(case_id="CASE-SUFF-01")
        self.assertIn(report.sufficiency_state.value, ["INSUFFICIENT", "NOT_AVAILABLE", "PARTIALLY_SUFFICIENT"])
        self.assertTrue(len(report.missing_evidence_items) > 0)

    def test_reconciliation_engine_execution(self):
        rec_engine = ReconciliationEngine()
        result = rec_engine.reconcile(case_id="CASE-REC-01")
        self.assertIsNotNone(result.overall_status)
        self.assertTrue(len(result.pairs) > 0)


if __name__ == "__main__":
    unittest.main()
