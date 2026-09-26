"""
UC15 GST Compliance Agent — Unit Test Suite for Exhaustive Decision Matrix & Control Engine
Tests GSTIN, POS, Tax Rate Symmetry, RCM, Section 17(5) Blocked Credit, 180-Day Payment Interest, EWB Distance, and SAP Tax Code Drift.
"""
import unittest
from decimal import Decimal

from app.decision.context import ComplianceContext
from app.decision.orchestrator import ExhaustiveDecisionOrchestrator
from app.decision.result import DecisionStatus
from tests.fixtures.synthetic_finance_fixtures import get_synthetic_finance_fixtures


class TestExhaustiveDecisionMatrix(unittest.TestCase):

    def setUp(self):
        self.fixtures = get_synthetic_finance_fixtures()

    def test_invoice_1_normal_compliant_pass(self):
        inv1 = self.fixtures[0]
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv1)
        self.assertEqual(package.overall_status, DecisionStatus.PASS)
        self.assertEqual(package.failing_rules_count, 0)
        self.assertEqual(package.total_financial_exposure, 0.0)

    def test_invoice_2_wrong_rate_fail(self):
        inv2 = self.fixtures[1] # Charged 12% instead of 18% for HSN 8471
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv2)
        self.assertIn(package.overall_status, (DecisionStatus.FAIL, DecisionStatus.REVIEW_REQUIRED))
        self.assertGreater(len(package.decision_paths), 5)

    def test_invoice_3_wrong_sap_tax_code(self):
        inv3 = self.fixtures[2] # V1 (IGST) configured on intra-state transaction
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv3)
        sap_paths = [p for p in package.decision_paths if p.rule_id == "SAP_TAX_003"]
        self.assertEqual(len(sap_paths), 1)
        self.assertEqual(sap_paths[0].status, DecisionStatus.FAIL)
        self.assertGreater(sap_paths[0].financial_exposure, 0)

    def test_invoice_4_wrong_pos_symmetry_fail(self):
        inv4 = self.fixtures[3] # POS Delhi for MH transaction charged CGST+SGST
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv4)
        sym_paths = [p for p in package.decision_paths if p.rule_id == "TAX_002"]
        self.assertEqual(len(sym_paths), 1)
        self.assertEqual(sym_paths[0].status, DecisionStatus.FAIL)

    def test_invoice_8_rcm_transaction_pass(self):
        inv8 = self.fixtures[7] # GTA HSN 9965 correctly classified as RCM
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv8)
        rcm_paths = [p for p in package.decision_paths if p.rule_id == "RCM_001"]
        self.assertEqual(len(rcm_paths), 1)
        self.assertEqual(rcm_paths[0].status, DecisionStatus.PASS)

    def test_invoice_10_unpaid_180_days_interest_exposure(self):
        inv10 = self.fixtures[9] # Overdue 180 days
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv10)
        itc_paths = [p for p in package.decision_paths if p.rule_id == "ITC_180_001"]
        self.assertEqual(len(itc_paths), 1)
        self.assertEqual(itc_paths[0].status, DecisionStatus.FAIL)
        self.assertGreater(itc_paths[0].financial_exposure, 18000.0) # Tax + 18% p.a. interest

    def test_invoice_12_blocked_credit_17_5(self):
        inv12 = self.fixtures[11] # Outdoor catering HSN 9963
        package = ExhaustiveDecisionOrchestrator.evaluate_transaction(inv12)
        itc_paths = [p for p in package.decision_paths if p.rule_id == "ITC_004"]
        self.assertEqual(len(itc_paths), 1)
        self.assertEqual(itc_paths[0].status, DecisionStatus.FAIL)
        self.assertEqual(itc_paths[0].financial_exposure, 9000.0)
