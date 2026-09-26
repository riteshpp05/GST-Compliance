"""
Unit tests for RiskEngine: scoring, categorization, boundary testing,
determinism, explainability, confidence, and configuration overrides.
"""
from datetime import date
from decimal import Decimal
import unittest

from app.config.risk_config import RiskConfig, RiskLevelRange, RiskSeverityWeights, load_risk_config
from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.confidence_level import ConfidenceLevel
from app.domain.enums.risk_level import RiskLevel
from app.domain.enums.risk_priority import RiskPriority
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationReport, ValidationResult
from app.engine.risk_engine import RiskEngine


def _make_dummy_invoice(invoice_no="INV-100", direction="AR") -> Invoice:
    return Invoice.from_record(
        invoice_no=invoice_no,
        invoice_date="2023-10-15",
        direction=direction,
        counterparty_name="Acme Corp",
        counterparty_gstin="27AAACB1234A1ZJ",
        place_of_supply="Maharashtra",
        hsn_code="8471",
        item_desc="Laptops",
        taxable_value_inr=100000.00,
        cgst_rate=9.0,
        sgst_rate=9.0,
        igst_rate=0.0,
        total_amt=118000.00,
    )




def _make_dummy_decision(invoice: Invoice, failed_count=0, hard_override=False) -> ComplianceDecision:
    status = ComplianceStatus.COMPLIANT.value
    if hard_override or failed_count >= 2:
        status = ComplianceStatus.NON_COMPLIANT.value
    elif failed_count == 1:
        status = ComplianceStatus.NEEDS_REVIEW.value

    return ComplianceDecision(
        invoice_no=invoice.invoice_number,
        invoice_date=str(invoice.invoice_date),
        direction=invoice.direction,
        counterparty_gstin=invoice.counterparty_gstin,
        counterparty_name=invoice.counterparty_name,
        place_of_supply=invoice.place_of_supply,
        hsn_code=invoice.hsn_code,
        item_desc=invoice.item_desc,
        taxable_value_inr=float(invoice.taxable_value),
        total_amt=float(invoice.total_amount),
        gates=[],
        failed_gate_count=failed_count,
        status=status,
        justification="Test",
        recommended_action="Test action",
        sap_action="Test sap action",
        audit_trail_ref="GST-TEST12345",
        hard_override=hard_override,
    )


class TestRiskEngine(unittest.TestCase):

    def setUp(self):
        self.engine = RiskEngine()

    def test_clean_invoice_zero_risk(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="GSTIN_001", rule_name="GSTIN Check", status="PASS", message="Valid", gate_no=1),
            ValidationResult(rule_id="HSN_001", rule_name="HSN Check", status="PASS", message="Valid", gate_no=2),
        ])
        decision = _make_dummy_decision(inv, failed_count=0)

        assessment = self.engine.assess(inv, report, decision)

        self.assertEqual(assessment.risk_score, 0.0)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW.value)
        self.assertEqual(assessment.priority, RiskPriority.P4.value)
        self.assertEqual(assessment.confidence, ConfidenceLevel.HIGH.value)
        self.assertEqual(assessment.confidence_score, 1.0)
        self.assertEqual(len(assessment.risk_factors), 0)
        self.assertIn("Clean invoice", assessment.explanation)

    def test_single_low_severity_finding(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="POS_001", rule_name="Place of Supply", status="FAIL", message="Minor POS issue", severity="LOW", category="PLACE_OF_SUPPLY", gate_no=4),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        assessment = self.engine.assess(inv, report, decision)

        # Expected score: Severity LOW (5) + Category PLACE_OF_SUPPLY (15) = 20.0
        self.assertEqual(assessment.risk_score, 20.0)
        self.assertEqual(assessment.risk_level, RiskLevel.MODERATE.value)
        self.assertEqual(assessment.priority, RiskPriority.P4.value)
        self.assertEqual(len(assessment.risk_factors), 2)  # 1 severity + 1 category

    def test_single_high_severity_finding(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="TAX_001", rule_name="Tax Rate", status="FAIL", message="Incorrect rate applied", severity="HIGH", category="TAX", gate_no=3),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        assessment = self.engine.assess(inv, report, decision)

        # Expected score: Severity HIGH (25) + Category TAX (20) = 45.0
        self.assertEqual(assessment.risk_score, 45.0)
        self.assertEqual(assessment.risk_level, RiskLevel.MEDIUM.value)
        self.assertEqual(assessment.priority, RiskPriority.P3.value)

    def test_critical_finding_policy_floor(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="GSTIN_001", rule_name="GSTIN Format", status="FAIL", message="Malformed GSTIN", severity="CRITICAL", category="MASTER_DATA", gate_no=1),
        ])
        decision = _make_dummy_decision(inv, failed_count=1, hard_override=True)

        assessment = self.engine.assess(inv, report, decision)

        # Raw score: Severity CRITICAL (40) + Category MASTER_DATA (5) = 45.0
        # Policy floor triggers for CRITICAL: score bumped to 80.0
        self.assertEqual(assessment.risk_score, 80.0)
        self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL.value)
        self.assertEqual(assessment.priority, RiskPriority.P1.value)
        # Check floor factor exists
        floor_factor = next((f for f in assessment.risk_factors if f.factor_id == "CRITICAL_OVERRIDE"), None)
        self.assertIsNotNone(floor_factor)
        self.assertEqual(floor_factor.contribution, 35.0)  # 80 - 45

    def test_multiple_findings_compounding_penalty(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="TAX_001", rule_name="Tax Rate", status="FAIL", message="Wrong rate", severity="HIGH", category="TAX", gate_no=3),
            ValidationResult(rule_id="EWB_001", rule_name="E-Way Bill", status="FAIL", message="Missing EWB", severity="MEDIUM", category="EWAY_BILL", gate_no=5),
        ])
        decision = _make_dummy_decision(inv, failed_count=2)

        assessment = self.engine.assess(inv, report, decision)

        # TAX severity: 25, EWB severity: 15 -> Severity contrib = 40
        # TAX category: 20, EWB category: 10 -> Category contrib = 30
        # Multiple findings penalty (2 failures -> 1 extra * 10): 10
        # Total = 40 + 30 + 10 = 80.0 -> CRITICAL
        self.assertEqual(assessment.risk_score, 80.0)
        self.assertEqual(assessment.risk_level, RiskLevel.CRITICAL.value)
        mult_factor = next((f for f in assessment.risk_factors if f.factor_id == "MULTIPLE_FINDINGS"), None)
        self.assertIsNotNone(mult_factor)
        self.assertEqual(mult_factor.contribution, 10.0)

    def test_data_quality_finding_affects_confidence_and_score(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="DATA_002", rule_name="Invoice Date Bounds", status="FAIL", message="Date in future", severity="MEDIUM", category="DATA_QUALITY", gate_no=None),
        ])
        decision = _make_dummy_decision(inv, failed_count=0)

        assessment = self.engine.assess(inv, report, decision)

        # Only DQ penalty: 5.0
        self.assertEqual(assessment.risk_score, 5.0)
        self.assertEqual(assessment.risk_level, RiskLevel.LOW.value)
        # Confidence penalized by 0.10: 1.0 - 0.10 = 0.90 -> HIGH
        self.assertEqual(assessment.confidence_score, 0.90)

    def test_missing_master_data_reduces_confidence(self):
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="HSN_001", rule_name="HSN Master", status="FAIL", message="HSN code 9999 was not found in the HSN/SAC master.", severity="HIGH", category="CLASSIFICATION", gate_no=2),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        assessment = self.engine.assess(inv, report, decision)

        # Confidence penalized by missing_hsn_master (0.20): 1.0 - 0.20 = 0.80 -> MEDIUM
        self.assertEqual(assessment.confidence_score, 0.80)
        self.assertEqual(assessment.confidence, ConfidenceLevel.MEDIUM.value)

    def test_score_boundaries_explicit(self):
        """Test exact boundary points: 0, 19, 20, 39, 40, 59, 60, 79, 80, 100."""
        self.assertEqual(self.engine.level_for_score(0.0), RiskLevel.LOW.value)
        self.assertEqual(self.engine.level_for_score(19.0), RiskLevel.LOW.value)
        self.assertEqual(self.engine.level_for_score(19.99), RiskLevel.LOW.value)

        self.assertEqual(self.engine.level_for_score(20.0), RiskLevel.MODERATE.value)
        self.assertEqual(self.engine.level_for_score(39.0), RiskLevel.MODERATE.value)
        self.assertEqual(self.engine.level_for_score(39.99), RiskLevel.MODERATE.value)

        self.assertEqual(self.engine.level_for_score(40.0), RiskLevel.MEDIUM.value)
        self.assertEqual(self.engine.level_for_score(59.0), RiskLevel.MEDIUM.value)
        self.assertEqual(self.engine.level_for_score(59.99), RiskLevel.MEDIUM.value)

        self.assertEqual(self.engine.level_for_score(60.0), RiskLevel.HIGH.value)
        self.assertEqual(self.engine.level_for_score(79.0), RiskLevel.HIGH.value)
        self.assertEqual(self.engine.level_for_score(79.99), RiskLevel.HIGH.value)

        self.assertEqual(self.engine.level_for_score(80.0), RiskLevel.CRITICAL.value)
        self.assertEqual(self.engine.level_for_score(100.0), RiskLevel.CRITICAL.value)

    def test_determinism(self):
        """Verify identical invoice + report produces identical score, level, factors 10 times."""
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="TAX_001", rule_name="Tax Rate", status="FAIL", message="Wrong rate", severity="HIGH", category="TAX", gate_no=3),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        first_assessment = self.engine.assess(inv, report, decision)
        for _ in range(10):
            repeated = self.engine.assess(inv, report, decision)
            self.assertEqual(first_assessment.risk_score, repeated.risk_score)
            self.assertEqual(first_assessment.risk_level, repeated.risk_level)
            self.assertEqual(first_assessment.priority, repeated.priority)
            self.assertEqual(len(first_assessment.risk_factors), len(repeated.risk_factors))

    def test_explainability_traceability(self):
        """Every non-zero score has explicit factors whose sum or floor matches the score."""
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="EWB_001", rule_name="E-Way Bill", status="FAIL", message="Missing EWB", severity="MEDIUM", category="EWAY_BILL", gate_no=5),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        assessment = self.engine.assess(inv, report, decision)
        self.assertGreater(assessment.risk_score, 0)
        self.assertGreater(len(assessment.risk_factors), 0)
        factor_sum = sum(f.contribution for f in assessment.risk_factors)
        self.assertEqual(assessment.risk_score, factor_sum)

        for f in assessment.risk_factors:
            self.assertIsNotNone(f.factor_id)
            self.assertIsNotNone(f.name)
            self.assertGreater(f.contribution, 0)

    def test_configuration_customization(self):
        """Modifying RiskConfig weights changes scores without touching Python logic."""
        custom_config = RiskConfig()
        custom_config.weights.severity.HIGH = 50.0  # Double HIGH severity weight

        custom_engine = RiskEngine(config=custom_config)
        inv = _make_dummy_invoice()
        report = ValidationReport(invoice_id=inv.invoice_number, results=[
            ValidationResult(rule_id="TAX_001", rule_name="Tax Rate", status="FAIL", message="Wrong rate", severity="HIGH", category="TAX", gate_no=3),
        ])
        decision = _make_dummy_decision(inv, failed_count=1)

        assessment = custom_engine.assess(inv, report, decision)
        # Severity HIGH (50) + Category TAX (20) = 70.0 (High risk)
        self.assertEqual(assessment.risk_score, 70.0)
        self.assertEqual(assessment.risk_level, RiskLevel.HIGH.value)


if __name__ == "__main__":
    unittest.main()
