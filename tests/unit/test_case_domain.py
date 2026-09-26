"""
tests.unit.test_case_domain
============================
Unit Test Suite for Sprint 13 Case Domain Models and InMemoryCaseRepository.
Verifies case creation, ID generation, evidence reference serialization, and repository operations.
"""

import unittest
from app.case.models import (
    CaseAssignment,
    CaseDecision,
    CaseDecisionEnum,
    CaseEvent,
    CaseEvidenceReference,
    CaseEventTypeEnum,
    CaseStatusEnum,
    InvestigationCase,
)
from app.case.repository import InMemoryCaseRepository


class TestCaseDomain(unittest.TestCase):
    """Unit tests for Case Management domain models and repository."""

    def test_case_id_formatting(self):
        case = InvestigationCase(title="Test GST Risk Review", invoice_id="INV-8000001")
        self.assertTrue(case.case_id.startswith("CASE-"))
        self.assertEqual(len(case.case_id), 13)

    def test_evidence_reference_creation(self):
        ref = CaseEvidenceReference(
            source_type="GATE_DETERMINATION",
            source_identifier="Gate-4",
            invoice_id="INV-8000001",
            gate_id=4,
            summary="Gate 4 Place of Supply mismatch",
        )
        self.assertTrue(ref.reference_id.startswith("REF-"))
        self.assertEqual(ref.gate_id, 4)

    def test_case_decision_model(self):
        dec = CaseDecision(
            case_id="CASE-12345678",
            reviewer="Alice Accountant",
            reviewer_role="Finance Manager",
            decision=CaseDecisionEnum.APPROVE,
            comment="Approved following vendor clarification.",
        )
        self.assertTrue(dec.decision_id.startswith("DEC-"))
        self.assertEqual(dec.reviewer, "Alice Accountant")
        self.assertEqual(dec.decision, CaseDecisionEnum.APPROVE)

    def test_in_memory_repository(self):
        repo = InMemoryCaseRepository()
        case = InvestigationCase(
            case_id="CASE-TEST0001",
            title="Test Case",
            status=CaseStatusEnum.REVIEW_REQUIRED,
            priority="P1",
            risk_level="CRITICAL",
        )
        repo.save_case(case)

        retrieved = repo.get_case("CASE-TEST0001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.title, "Test Case")

        cases_p1 = repo.list_cases(priority="P1")
        self.assertEqual(len(cases_p1), 1)

        # Event logging
        event = CaseEvent(
            case_id="CASE-TEST0001",
            event_type=CaseEventTypeEnum.CASE_CREATED,
            actor="SYSTEM",
        )
        repo.save_event(event)
        events = repo.get_events("CASE-TEST0001")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, CaseEventTypeEnum.CASE_CREATED)


if __name__ == "__main__":
    unittest.main()
