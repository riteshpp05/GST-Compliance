"""
UC15 GST Compliance Agent — Sprint 23 AI Context & Grounding Unit Tests
Verifies canonical context construction and evidence grounding evaluation.
"""
import unittest

from app.domain.models.invoice import Invoice
from app.investigation.ai.context_builder import CanonicalAIContextBuilder, ControlledInvestigationContext
from app.investigation.ai.grounding import EvidenceGroundingEvaluator, AIClaim, GroundingStatus


class TestS23AIContextAndGrounding(unittest.TestCase):

    def setUp(self):
        self.builder = CanonicalAIContextBuilder()
        self.evaluator = EvidenceGroundingEvaluator()

    def test_context_builder_structures_sources(self):
        inv = Invoice.from_record(
            invoice_no="INV-CONTEXT-01",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Context Test Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Servers",
            taxable_value_inr=100000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=118000.0,
        )

        ctx = self.builder.build_context(case_id="CASE-CTX-01", invoice=inv)
        self.assertIsInstance(ctx, ControlledInvestigationContext)
        self.assertEqual(ctx.case_id, "CASE-CTX-01")
        self.assertEqual(ctx.invoice_id, "INV-CONTEXT-01")

        valid_sources = ctx.get_valid_source_ids()
        self.assertIn("CASE-CTX-01", valid_sources)
        self.assertIn("INV-CONTEXT-01", valid_sources)
        self.assertIn("EVD-INV-CONTEXT-01-INVOICE", valid_sources)

    def test_grounded_claim_validation(self):
        inv = Invoice.from_record(
            invoice_no="INV-GROUND-01",
            invoice_date="2026-03-10",
            direction="AP",
            counterparty_gstin="27AAACB1234C1Z1",
            counterparty_name="Grounding Test Vendor",
            place_of_supply="27",
            hsn_code="8471",
            item_desc="Goods",
            taxable_value_inr=10000.0,
            cgst_rate=9.0,
            sgst_rate=9.0,
            igst_rate=0.0,
            total_amt=11800.0,
        )
        ctx = self.builder.build_context(case_id="CASE-G01", invoice=inv)

        valid_claim = AIClaim(
            claim_id="CLM-01",
            claim_text="Invoice record processed.",
            source_ids=["EVD-INV-GROUND-01-INVOICE"],
        )
        res_valid = self.evaluator.evaluate_claim(valid_claim, ctx)
        self.assertEqual(res_valid.grounding_status, GroundingStatus.GROUNDED)

        invalid_claim = AIClaim(
            claim_id="CLM-02",
            claim_text="Fake evidence claimed.",
            source_ids=["EVD-FAKE-999"],
        )
        res_invalid = self.evaluator.evaluate_claim(invalid_claim, ctx)
        self.assertEqual(res_invalid.grounding_status, GroundingStatus.UNSUPPORTED)


if __name__ == "__main__":
    unittest.main()
