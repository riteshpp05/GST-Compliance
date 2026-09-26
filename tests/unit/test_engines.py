"""
Unit tests for UC15 ValidationEngine and DecisionEngine.
Verifies separation between rule execution (report) and business classification (decision).
"""
import unittest

from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.engine.decision_engine import DecisionEngine
from app.engine.validation_engine import ValidationEngine
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext
from app.rules.registry import RuleRegistry
from tests.fixtures.sample_invoices import make_test_context, make_test_invoice


class MockFailingRule(ComplianceRule):
    @property
    def rule_id(self) -> str:
        return "MOCK_FAIL"
    @property
    def name(self) -> str:
        return "Mock Failing Rule"
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.OTHER
    def validate(self, invoice: Invoice, context: ValidationContext = None) -> ValidationResult:
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=3,
            status=ValidationStatus.FAIL,
            message="Mock test failure",
        )


class MockCrashingRule(ComplianceRule):
    @property
    def rule_id(self) -> str:
        return "MOCK_CRASH"
    @property
    def name(self) -> str:
        return "Mock Crashing Rule"
    @property
    def category(self) -> RuleCategory:
        return RuleCategory.OTHER
    def validate(self, invoice: Invoice, context: ValidationContext = None) -> ValidationResult:
        raise RuntimeError("Unexpected internal crash in rule")


class TestEngines(unittest.TestCase):

    def setUp(self):
        self.context = make_test_context()
        self.val_engine = ValidationEngine(context=self.context)
        self.dec_engine = DecisionEngine()

    def test_validation_engine_produces_report(self):
        inv = make_test_invoice()
        report = self.val_engine.validate(inv)

        self.assertEqual(report.invoice_id, inv.invoice_number)
        self.assertEqual(len(report.results), 6)
        self.assertEqual(report.failed_count, 0)
        self.assertEqual(report.passed_count, 4)  # 4 pass, 2 not applicable (Gate 5 for <=50k, Gate 6 for AR)
        self.assertEqual(report.not_applicable_count, 2)

    def test_validation_engine_handles_crashing_rule_gracefully(self):
        reg = RuleRegistry()
        reg.register(MockCrashingRule())
        engine = ValidationEngine(registry_or_rules=reg, context=self.context)

        inv = make_test_invoice()
        report = engine.validate(inv)

        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].status, ValidationStatus.ERROR.value)
        self.assertIn("Rule execution error", report.results[0].message)

    def test_decision_engine_clean_is_compliant(self):
        inv = make_test_invoice()
        report = self.val_engine.validate(inv)
        decision = self.dec_engine.decide(inv, report)

        self.assertEqual(decision.status, ComplianceStatus.COMPLIANT.value)
        self.assertEqual(decision.failed_gate_count, 0)
        self.assertFalse(decision.hard_override)
        self.assertIn("ready for GSTR-1/GSTR-3B", decision.sap_action)
        self.assertTrue(decision.audit_trail_ref.startswith("GST-"))

    def test_decision_engine_one_failure_is_needs_review(self):
        # CGST 12%, SGST 12% (official is 9/9) -> Gate 3 fails
        inv = make_test_invoice(cgst_rate=12.0, sgst_rate=12.0)
        report = self.val_engine.validate(inv)
        decision = self.dec_engine.decide(inv, report)

        self.assertEqual(decision.status, ComplianceStatus.NEEDS_REVIEW.value)
        self.assertEqual(decision.failed_gate_count, 1)
        self.assertFalse(decision.hard_override)
        self.assertIn("Flagged in the compliance queue", decision.sap_action)

    def test_decision_engine_gate1_failure_is_hard_override(self):
        inv = make_test_invoice(gstin="27INVALID123")
        report = self.val_engine.validate(inv)
        decision = self.dec_engine.decide(inv, report)

        self.assertEqual(decision.status, ComplianceStatus.NON_COMPLIANT.value)
        self.assertTrue(decision.hard_override)
        self.assertIn("Gate 1 (GSTIN Format Validity) failed", decision.justification)
        self.assertIn("GSTIN correction required in KNA1/LFA1", decision.sap_action)

    def test_decision_engine_multiple_failures_is_non_compliant(self):
        # Tax rate mismatch (Gate 3 FAIL) + POS mismatch (Gate 4 FAIL)
        inv = make_test_invoice(
            hsn_code="8409",
            cgst_rate=12.0,
            sgst_rate=12.0,
            place_of_supply="Delhi",
        )
        report = self.val_engine.validate(inv)
        decision = self.dec_engine.decide(inv, report)

        self.assertEqual(decision.status, ComplianceStatus.NON_COMPLIANT.value)
        self.assertGreaterEqual(decision.failed_gate_count, 2)
        self.assertFalse(decision.hard_override)


if __name__ == "__main__":
    unittest.main()
