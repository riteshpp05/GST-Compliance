"""
UC15 GST Compliance Agent — Sprint 21 Integration Tests
Validates Finance Review Explainable Findings & Historical Case Snapshot Reproducibility.
"""
import unittest

from app.agent.ai.dossier import InvestigationDossier
from app.agent.ai.session import EntityFocus
from app.case.models import InvestigationCase
from app.case.service import CaseService
from app.domain.models.invoice import Invoice
from app.engine.validation_engine import ValidationEngine


class TestS21FinanceReviewIntegration(unittest.TestCase):
    """Integration test suite for finance-readable findings and case reproducibility."""

    def test_validation_engine_produces_s21_traceability(self):
        """ValidationEngine output report contains rule version and explainable fields."""
        engine = ValidationEngine()
        inv = Invoice(
            invoice_id="INV-S21-100",
            invoice_number="INV-S21-100",
            invoice_date="2024-05-15",
            counterparty_name="Acme Corp",
            gstin="29AAACB1084F118",
            hsn_sac="8471",
            cgst_rate=0.09,
            sgst_rate=0.09,
            igst_rate=0.0,
            direction="AP",
            place_of_supply="Karnataka",
            taxable_value=100000.0,
            eway_bill="GENERATED",
            gstr2b_reflected=True,
        )
        report = engine.validate(inv)
        self.assertEqual(report.invoice_id, "INV-S21-100")
        for res in report.results:
            self.assertIsNotNone(res.rule_version)
            self.assertEqual(res.rule_version, "2.0")

    def test_case_snapshot_reproducibility(self):
        """Case created from dossier stores compliance_context_snapshot preserving historical state."""
        inv = Invoice(
            invoice_id="INV-S21-200",
            invoice_number="INV-S21-200",
            invoice_date="2024-05-15",
            counterparty_name="Acme Corp",
            gstin="29AAACB1084F118",
            hsn_sac="8471",
            direction="AP",
            place_of_supply="Karnataka",
            taxable_value=50000.0,
        )
        dossier = InvestigationDossier(
            dossier_id="DOSSIER-S21-200",
            session_id="SESS-S21-200",
            entity_focus=EntityFocus(invoice_id=inv.invoice_id, counterparty_gstin=inv.gstin),
            executive_summary="Executive summary for test dossier",
            gate_breakdown=[
                {
                    "gate": 1,
                    "name": "GSTIN Format Validity",
                    "result": "PASS",
                    "details": "GSTIN 29AAACB1084F118 matches standard format.",
                    "rule_version": "2.0",
                }
            ],
        )
        service = CaseService()
        case = service.create_case_from_dossier(dossier)
        self.assertIsInstance(case, InvestigationCase)
        self.assertIn("compliance_context_snapshot", case.model_dump())
        snapshot = case.compliance_context_snapshot
        self.assertIn("gate_breakdown", snapshot)
        self.assertEqual(snapshot["engine_version"], "2.0")


if __name__ == "__main__":
    unittest.main()
