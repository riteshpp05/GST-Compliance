"""
UC15 GST Compliance Agent — Integration Tests: Reference Intelligence Pipeline (Sprint 4)
Verifies end-to-end temporal validation, historical consistency, conflict handling, and snapshot persistence.
"""
from datetime import date
from decimal import Decimal
import unittest

from app.domain.models.invoice import Invoice
from app.engine.decision_engine import DecisionEngine
from app.engine.validation_engine import ValidationEngine
from app.reference.models.hsn import HSNReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.services.reference_service import ReferenceService
from app.rules.context import ValidationContext


class TestReferencePipelineIntegration(unittest.TestCase):
    """End-to-end integration tests for Reference Intelligence and temporal compliance validation."""

    def setUp(self):
        self.ref_service = ReferenceService()
        self.context = ValidationContext(reference_service=self.ref_service)
        self.val_engine = ValidationEngine(context=self.context)
        self.decision_engine = DecisionEngine()

    def test_historical_tax_rate_shift_end_to_end(self):
        """
        Verify that an invoice in 2020 with 12% IGST passes against 2020 rates,
        while an identical invoice in 2022 with 12% IGST fails against 2022 restored 18% rates.
        """
        # 1. 2020 Invoice with 12% IGST (6% CGST + 6% SGST)
        inv_2020 = Invoice(
            invoice_id="INV-HIST-2020",
            invoice_number="INV-HIST-2020",
            invoice_date="2020-05-15",
            direction="AR",
            counterparty_name="Acme Tech",
            gstin="27AABCT1234F1ZP",
            place_of_supply="Maharashtra",
            hsn_sac="84713010_TEMP",
            taxable_value=Decimal("40000.00"),
            cgst_rate=Decimal("0.06"),
            sgst_rate=Decimal("0.06"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("4800.00"),
            total_amount=Decimal("44800.00"),
        )
        report_2020 = self.val_engine.validate(inv_2020)
        tax_res_2020 = next(r for r in report_2020.results if r.rule_id == "TAX_001")
        self.assertEqual(tax_res_2020.status, "PASS")
        self.assertEqual(tax_res_2020.evidence["reference_version"], "1.0")

        # 2. 2022 Invoice with same 12% IGST — should fail because rate increased to 18%
        inv_2022 = Invoice(
            invoice_id="INV-HIST-2022",
            invoice_number="INV-HIST-2022",
            invoice_date="2022-06-15",
            direction="AR",
            counterparty_name="Acme Tech",
            gstin="27AABCT1234F1ZP",
            place_of_supply="Maharashtra",
            hsn_sac="84713010_TEMP",
            taxable_value=Decimal("40000.00"),
            cgst_rate=Decimal("0.06"),
            sgst_rate=Decimal("0.06"),
            igst_rate=Decimal("0.00"),
            total_tax=Decimal("4800.00"),
            total_amount=Decimal("44800.00"),
        )
        report_2022 = self.val_engine.validate(inv_2022)
        tax_res_2022 = next(r for r in report_2022.results if r.rule_id == "TAX_001")
        self.assertEqual(tax_res_2022.status, "FAIL")
        self.assertEqual(tax_res_2022.evidence["reference_version"], "2.0")

    def test_expired_hsn_code_fails_validation(self):
        """Invoice dated after HSN code expired fails Gate 2 and Gate 3 with NOT_FOUND status."""
        inv_expired = Invoice(
            invoice_id="INV-EXP-001",
            invoice_number="INV-EXP-001",
            invoice_date="2023-01-01",  # 999999_EXP expired on 2020-12-31
            direction="AR",
            counterparty_name="Legacy Tech",
            gstin="27AABCT1234F1ZP",
            place_of_supply="Maharashtra",
            hsn_sac="999999_EXP",
            taxable_value=Decimal("10000.00"),
            cgst_rate=Decimal("0.09"),
            sgst_rate=Decimal("0.09"),
            total_tax=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
        )
        report = self.val_engine.validate(inv_expired)
        hsn_res = next(r for r in report.results if r.rule_id == "HSN_001")
        self.assertEqual(hsn_res.status, "NEEDS_REVIEW")
        self.assertEqual(hsn_res.evidence["resolution_status"], "NOT_FOUND")

    def test_conflicting_hsn_reference_fails_deterministically(self):
        """Injected overlapping active references cause CONFLICT status without silent guessing."""
        # Inject conflicting overlapping HSN in repository
        conflict_hsn_1 = HSNReference(
            reference_id="HSN_CONF_1",
            code="777777",
            description="Conflict Item A",
            version="1.0",
            effective_from=date(2023, 1, 1),
            effective_to=date(2023, 12, 31),
        )
        conflict_hsn_2 = HSNReference(
            reference_id="HSN_CONF_2",
            code="777777",
            description="Conflict Item B",
            version="2.0",
            effective_from=date(2023, 6, 1),
            effective_to=date(2024, 6, 1),
        )
        self.ref_service.repository.add_hsn(conflict_hsn_1)
        self.ref_service.repository.add_hsn(conflict_hsn_2)
        self.ref_service.clear_cache()

        inv_conflict = Invoice(
            invoice_id="INV-CONF-001",
            invoice_number="INV-CONF-001",
            invoice_date="2023-08-01",
            direction="AR",
            counterparty_name="Conflict Corp",
            gstin="27AABCT1234F1ZP",
            place_of_supply="Maharashtra",
            hsn_sac="777777",
            taxable_value=Decimal("10000.00"),
            cgst_rate=Decimal("0.09"),
            sgst_rate=Decimal("0.09"),
            total_tax=Decimal("1800.00"),
            total_amount=Decimal("11800.00"),
        )
        report = self.val_engine.validate(inv_conflict)
        hsn_res = next(r for r in report.results if r.rule_id == "HSN_001")
        self.assertEqual(hsn_res.status, "NEEDS_REVIEW")
        self.assertEqual(hsn_res.evidence["resolution_status"], "CONFLICT")
        self.assertIn("multiple active versions", hsn_res.message)

    def test_reference_snapshot_audit_trail_in_decision(self):
        """Verify that ValidationReport and ComplianceDecision contain complete reference snapshot."""
        inv = Invoice(
            invoice_id="INV-SNAP-001",
            invoice_number="INV-SNAP-001",
            invoice_date="2023-04-10",
            direction="AR",
            counterparty_name="Dell India",
            gstin="27AABCT1234F1ZP",
            place_of_supply="Maharashtra",
            hsn_sac="84713010",
            taxable_value=Decimal("30000.00"),
            cgst_rate=Decimal("0.09"),
            sgst_rate=Decimal("0.09"),
            total_tax=Decimal("5400.00"),
            total_amount=Decimal("35400.00"),
        )
        report = self.val_engine.validate(inv)
        self.assertIn("reference_snapshot", report.metadata)
        snapshot_dict = report.metadata["reference_snapshot"]
        self.assertEqual(snapshot_dict["invoice_id"], "INV-SNAP-001")
        self.assertEqual(snapshot_dict["transaction_date"], "2023-04-10")
        self.assertIsNotNone(snapshot_dict["hsn_reference_id"])
        self.assertIsNotNone(snapshot_dict["tax_rate_reference_id"])
        self.assertIsNotNone(snapshot_dict["state_reference_id"])

        decision = self.decision_engine.decide(inv, report)
        self.assertIsNotNone(decision.reference_snapshot)
        self.assertEqual(decision.reference_snapshot["invoice_id"], "INV-SNAP-001")


if __name__ == "__main__":
    unittest.main()
