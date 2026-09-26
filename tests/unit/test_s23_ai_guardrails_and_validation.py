"""
UC15 GST Compliance Agent — Sprint 23 AI Guardrails & Validation Unit Tests
Verifies deterministic value protection, anti-hallucination validation, and prompt hardening.
"""
import unittest
from decimal import Decimal

from app.domain.models.invoice import Invoice
from app.investigation.ai.context_builder import CanonicalAIContextBuilder
from app.investigation.ai.output_validator import AIOutputValidator
from app.investigation.ai.value_protector import DeterministicValueProtector
from app.investigation.ai.prompts import HardenedPromptManager, PROMPT_VERSION


class TestS23AIGuardrailsAndValidation(unittest.TestCase):

    def setUp(self):
        self.builder = CanonicalAIContextBuilder()
        self.protector = DeterministicValueProtector()
        self.validator = AIOutputValidator(value_protector=self.protector)
        self.prompt_mgr = HardenedPromptManager()

    def test_value_protection_overrides_conflicting_exposure(self):
        inv = Invoice.from_record(
            invoice_no="INV-VAL-01",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Value Protection Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Goods",
            taxable_value_inr=100000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=118000.0,
        )
        ctx = self.builder.build_context(case_id="CASE-VAL-01", invoice=inv)
        ctx.financial_exposures = [
            {"exposure_id": "EXP-INV-VAL-01-1", "amount": 6000.0, "exposure_type": "TAX_UNDERCHARGE"}
        ]

        ai_out = {
            "what_was_detected": {"summary": "Tax rate mismatch."},
            "financial_impact": [{"exposure_id": "EXP-INV-VAL-01-1", "amount": 10000.0, "exposure_type": "TAX_UNDERCHARGE"}],
        }

        prot_res = self.protector.sanitize_and_protect(ai_out, ctx)
        self.assertTrue(prot_res.has_conflicts)
        self.assertEqual(len(prot_res.conflict_logs), 1)
        self.assertEqual(prot_res.sanitized_output["financial_impact"][0]["amount"], 6000.0)

    def test_forbidden_legal_assertion_rejection(self):
        inv = Invoice.from_record(
            invoice_no="INV-LEG-01",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Legal Test Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Goods",
            taxable_value_inr=10000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=11800.0,
        )
        ctx = self.builder.build_context(case_id="CASE-LEG-01", invoice=inv)

        ai_out = {
            "what_was_detected": {"summary": "Vendor is guilty of fraud and tax evasion confirmed."},
        }

        val_res = self.validator.validate_output(ai_out, ctx)
        self.assertIn(val_res.status, ["PARTIALLY_VALID", "REJECTED"])
        self.assertTrue(len(val_res.rejected_claims) > 0)

    def test_hardened_prompt_manager_versioning(self):
        prompt = self.prompt_mgr.get_system_prompt()
        self.assertIn("v23.1", prompt)
        self.assertIn("DOWNSTREAM, ADVISORY", prompt)
        self.assertIn("READ-ONLY", prompt)


if __name__ == "__main__":
    unittest.main()
