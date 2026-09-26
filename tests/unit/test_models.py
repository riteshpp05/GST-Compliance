"""
Unit tests for UC15 Domain Models: Invoice, ValidationResult, ValidationReport, ComplianceDecision.
"""
import unittest
from decimal import Decimal
from pydantic import ValidationError

from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster, StateCodeRef
from app.domain.models.validation import ComplianceDecision, ValidationReport, ValidationResult
from app.domain.models.vendor import Counterparty


class TestDomainModels(unittest.TestCase):

    def test_valid_invoice_creation(self):
        inv = Invoice.from_record(
            invoice_no="INV-999",
            invoice_date="2026-03-01",
            direction="AR",
            counterparty_gstin="27AAACB1234A1Z5",
            counterparty_name="Tata Motors",
            place_of_supply="Maharashtra",
            hsn_code="8409",
            item_desc="Engine block",
            taxable_value_inr=50000.00,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=59000.00,
            eway_bill_status="GENERATED",
            gstr2b_reflected=True,
        )
        self.assertEqual(inv.invoice_number, "INV-999")
        self.assertEqual(inv.invoice_no, "INV-999")
        self.assertEqual(inv.taxable_value, Decimal("50000.00"))
        self.assertEqual(inv.total_amount, Decimal("59000.00"))
        self.assertEqual(inv.taxable_value_inr, 50000.00)
        self.assertEqual(inv.direction, "AR")
        self.assertIsNotNone(inv.customer)
        self.assertIsNone(inv.vendor)

    def test_inward_invoice_assigns_vendor(self):
        inv = Invoice.from_record(
            invoice_no="INV-AP-01",
            invoice_date="2026-03-01",
            direction="AP",
            counterparty_gstin="07AAACH8901C1Z1",
            counterparty_name="Supplier Delhi",
            place_of_supply="Delhi",
            hsn_code="8409",
            item_desc="Spare part",
            taxable_value_inr=10000,
            cgst_rate=0,
            sgst_rate=0,
            igst_rate=18,
            total_amt=11800,
        )
        self.assertEqual(inv.direction, "AP")
        self.assertIsNotNone(inv.vendor)
        self.assertIsNone(inv.customer)
        self.assertEqual(inv.vendor.derived_state_code, "07")

    def test_missing_optional_fields(self):
        inv = Invoice(
            invoice_id="INV-MIN-1",
            invoice_number="INV-MIN-1",
            invoice_date="2026-03-01",
            counterparty_name="Minimal Corp",
            gstin="27AAACB1234A1Z5",
            place_of_supply="Maharashtra",
            hsn_sac="8409",
        )
        self.assertEqual(inv.taxable_value, Decimal("0.00"))
        self.assertEqual(inv.eway_bill, "")
        self.assertEqual(inv.eway_bill_status, "")
        self.assertTrue(inv.gstr2b_reflected)
        self.assertEqual(inv.metadata, {})

    def test_invalid_types_raise_validation_error(self):
        with self.assertRaises(ValidationError):
            # Missing mandatory fields like gstin and counterparty_name
            Invoice(invoice_id="INV-BAD")

    def test_validation_result_contract(self):
        res = ValidationResult(
            rule_id="GSTIN_001",
            rule_name="GSTIN Format Validity",
            status=ValidationStatus.PASS,
            severity=Severity.CRITICAL,
            category=RuleCategory.MASTER_DATA,
            message="GSTIN is valid",
            actual_value="27AAACB1234A1Z5",
            expected_value="Standard 15-character GSTIN",
        )
        self.assertEqual(res.status, "PASS")
        self.assertEqual(res.name, "GSTIN Format Validity")
        self.assertEqual(res.detail, "GSTIN is valid")
        self.assertEqual(res.severity, "CRITICAL")
        self.assertEqual(res.category, "MASTER_DATA")

        d = res.to_dict()
        self.assertEqual(d["rule_id"], "GSTIN_001")
        self.assertEqual(d["status"], "PASS")

    def test_validation_report_aggregation(self):
        r1 = ValidationResult(
            rule_id="R1", rule_name="Rule 1", status="PASS", message="ok"
        )
        r2 = ValidationResult(
            rule_id="R2", rule_name="Rule 2", status="FAIL", message="bad"
        )
        r3 = ValidationResult(
            rule_id="R3", rule_name="Rule 3", status="NOT_APPLICABLE", message="n/a"
        )
        report = ValidationReport(invoice_id="INV-100", results=[r1, r2, r3])

        self.assertEqual(report.passed_count, 1)
        self.assertEqual(report.failed_count, 1)
        self.assertEqual(report.not_applicable_count, 1)
        self.assertEqual(report.warning_count, 0)
        self.assertEqual(report.summary["passed"], 1)
        self.assertEqual(report.summary["failed"], 1)

    def test_hsn_master_from_raw(self):
        hsn = HSNMaster.from_raw("8409", "Engines", "9.0", "9.0", "18.0")
        self.assertEqual(hsn.hsn_code, "8409")
        self.assertEqual(hsn.correct_cgst_rate, Decimal("9.0"))
        self.assertEqual(hsn.correct_igst_rate, Decimal("18.0"))


if __name__ == "__main__":
    unittest.main()
