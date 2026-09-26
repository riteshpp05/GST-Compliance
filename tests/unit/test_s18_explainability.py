"""
tests.unit.test_s18_explainability
===================================
Unit Test Suite for Sprint 18 Explainability & Unsupported Claim Detection.
"""

import unittest
from app.case.models import CaseEvidenceRecord, CaseFinding
from app.investigation.explainability import InvestigationExplainer, UnsupportedClaimDetector


class TestS18Explainability(unittest.TestCase):

    def test_unsupported_claim_detection(self):
        ev = CaseEvidenceRecord(
            case_id="CASE-1",
            evidence_type="VALIDATION_RESULT",
            source="TEST",
            description="Gate 3 tax rate mismatch",
        )
        safe_text = "Potential compliance anomaly detected in tax rate calculation."
        unsupported = UnsupportedClaimDetector.detect_unsupported_claims(safe_text, [ev])
        self.assertEqual(len(unsupported), 0)

        prohibited_text = "The taxpayer committed fraud and tax evasion."
        unsupported_bad = UnsupportedClaimDetector.detect_unsupported_claims(prohibited_text, [ev])
        self.assertGreaterEqual(len(unsupported_bad), 1)
        self.assertTrue(any("UC15 safety policy requires objective compliance wording" in u for u in unsupported_bad))

    def test_structured_explanation_generation(self):
        finding = CaseFinding(
            case_id="CASE-EXP-1",
            title="Statutory GST Gate Mismatch",
            description="Invoice tax rate shows 28% instead of statutory 18%.",
            category="STATUTORY_COMPLIANCE",
            severity="HIGH",
        )
        ev = CaseEvidenceRecord(
            case_id="CASE-EXP-1",
            evidence_type="VALIDATION_RESULT",
            source="Gate-3",
            description="Official rate for HSN 3926 is 18%.",
        )

        explainer = InvestigationExplainer()
        exp = explainer.explain_finding(finding, [ev], confidence_level="HIGH")

        self.assertEqual(exp.finding_id, finding.finding_id)
        self.assertGreaterEqual(len(exp.facts), 1)
        self.assertGreaterEqual(len(exp.inferences), 2)
        self.assertTrue(exp.is_grounded)
        self.assertEqual(len(exp.unsupported_claims), 0)
        self.assertIn("Flag for compliance review", exp.recommendation)
