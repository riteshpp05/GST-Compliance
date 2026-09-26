"""
tests.unit.test_dossier
=======================
Unit Test Suite for Sprint 12.4 Audit Dossier Building & PDF Export Engine.
Verifies:
  1. DossierBuilder creation from session state
  2. Markdown rendering and section formatting
  3. JSON serialization
  4. ReportLab PDF generation to BytesIO buffer
  5. Enforcement of user rule #4: Explicit 'INSUFFICIENT EVIDENCE / NOT AVAILABLE' notices
  6. Advisory SAP guidance notice preservation
"""

import io
import unittest
from app.agent.ai.dossier import DossierBuilder, InvestigationDossier
from app.agent.ai.pdf_exporter import DossierPDFExporter
from app.agent.ai.session import EntityFocus, InvestigationSession, InvestigationTurn


class TestDossierEngine(unittest.TestCase):
    """Unit test suite for Dossier Building & PDF Export Engine."""

    def setUp(self):
        self.session = InvestigationSession(
            session_id="SESS-TEST1234",
            entity_focus=EntityFocus(invoice_id="INV-8000001", risk_level="CRITICAL"),
        )
        turn = InvestigationTurn(
            turn_index=1,
            user_query="Why is invoice INV-8000001 high risk?",
            resolved_query="Why is invoice INV-8000001 high risk?",
            intent="INVOICE_INVESTIGATION",
            tools_used=["get_compliance_result", "get_risk_assessment", "get_financial_exposure"],
            findings=[
                {
                    "type": "COMPLIANCE_RESULT",
                    "data": {
                        "invoice_no": "INV-8000001",
                        "compliance_status": "NON_COMPLIANT",
                        "gates": [
                            {"gate": 1, "name": "GSTIN Format", "result": "PASS", "details": "GSTIN valid."},
                            {"gate": 4, "name": "Place of Supply", "result": "FAIL", "details": "Intra-state IGST mismatch."},
                        ],
                    },
                },
                {"type": "RISK_ASSESSMENT", "data": {"risk_score": 100.0, "risk_level": "CRITICAL", "risk_priority": "P1"}},
                {"type": "FINANCIAL_EXPOSURE", "data": {"total_potential_exposure": 15840.0, "itc_at_risk": 15840.0}},
            ],
            regulatory_knowledge=[
                {
                    "status": "SUPPORTED",
                    "relevance_score": 0.95,
                    "chunk": {"content": "Rule 36(4) specifies 100% GSTR-2B reflection condition for ITC claim."},
                    "provenance": {
                        "document_id": "DOC-RULE-36-4",
                        "document_name": "GST Rule 36(4) ITC Policy",
                        "source": "CBIC Notification",
                        "section": "Rule 36(4)",
                    },
                }
            ],
            synthesized_answer="Invoice INV-8000001 is NON_COMPLIANT with CRITICAL risk.\nSAP action: Held from GSTR-1/GSTR-3B filing pending multi-issue correction.",
        )
        self.session.add_turn(turn)

    def test_dossier_building(self):
        dossier = DossierBuilder.build_dossier(self.session)
        self.assertEqual(dossier.session_id, "SESS-TEST1234")
        self.assertEqual(dossier.entity_focus.invoice_id, "INV-8000001")
        self.assertIn("INV-8000001", dossier.executive_summary)
        self.assertEqual(len(dossier.regulatory_evidence), 1)

    def test_dossier_markdown_export(self):
        dossier = DossierBuilder.build_dossier(self.session)
        md = dossier.to_markdown()
        self.assertIn("# UC15 GST COMPLIANCE & INVESTIGATION DOSSIER", md)
        self.assertIn("INV-8000001", md)
        self.assertIn("Rule 36(4)", md)
        self.assertIn("ADVISORY NOTICE", md)

    def test_dossier_json_export(self):
        dossier = DossierBuilder.build_dossier(self.session)
        json_str = dossier.to_json()
        self.assertIn("DOSSIER-SESS-TEST1234", json_str)
        self.assertIn("INV-8000001", json_str)

    def test_insufficient_evidence_notices(self):
        empty_session = InvestigationSession(session_id="SESS-EMPTY")
        dossier = DossierBuilder.build_dossier(empty_session)
        self.assertTrue(len(dossier.insufficient_evidence_notices) > 0)
        self.assertIn("INSUFFICIENT EVIDENCE / NOT AVAILABLE", dossier.to_markdown())

    def test_pdf_exporter(self):
        dossier = DossierBuilder.build_dossier(self.session)
        buf = io.BytesIO()
        DossierPDFExporter.export_pdf(dossier, buf)
        pdf_bytes = buf.getvalue()
        self.assertTrue(len(pdf_bytes) > 0)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
