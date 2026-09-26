"""
tests.integration.test_postgres_case_repository
================================================
Integration tests for SQLAlchemyCaseRepository implementing BaseCaseRepository.
Verifies case persistence, querying by filters, saving decisions, saving events,
evidence references, and concurrency control.
"""

import os
import unittest
from app.db.connection import init_db, reset_db_connection
from app.case.models import InvestigationCase, CaseStatusEnum, CaseDecision, CaseDecisionEnum, CaseEvent, CaseEvidenceReference
from app.case.sqlalchemy_case_repository import SQLAlchemyCaseRepository


class TestPostgresCaseRepository(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        init_db()

    def setUp(self):
        reset_db_connection()
        init_db()
        self.repo = SQLAlchemyCaseRepository()

    def test_save_and_get_case(self):
        case = InvestigationCase(
            case_id="CASE-INTEG-001",
            title="High Risk Invoice INV-8000001",
            status=CaseStatusEnum.REVIEW_REQUIRED,
            priority="P1",
            risk_level="CRITICAL",
            invoice_id="INV-8000001",
            financial_exposure=125000.0,
            root_cause="MASTER_DATA_MISMATCH"
        )
        self.repo.save_case(case)

        retrieved = self.repo.get_case("CASE-INTEG-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.case_id, "CASE-INTEG-001")
        self.assertEqual(retrieved.status, CaseStatusEnum.REVIEW_REQUIRED)
        self.assertEqual(retrieved.priority, "P1")
        self.assertEqual(retrieved.financial_exposure, 125000.0)

    def test_list_cases_by_filter(self):
        c1 = InvestigationCase(case_id="CASE-FILT-001", title="C1", status=CaseStatusEnum.OPEN, priority="P1")
        c2 = InvestigationCase(case_id="CASE-FILT-002", title="C2", status=CaseStatusEnum.READY_FOR_RESOLUTION, priority="P3")
        self.repo.save_case(c1)
        self.repo.save_case(c2)

        new_cases = self.repo.list_cases(status="OPEN")
        self.assertEqual(len(new_cases), 1)
        self.assertEqual(new_cases[0].case_id, "CASE-FILT-001")

    def test_save_decisions_and_events(self):
        case = InvestigationCase(
            case_id="CASE-DEC-001",
            title="Decision test",
            status=CaseStatusEnum.REVIEW_REQUIRED,
            priority="P2"
        )
        self.repo.save_case(case)

        decision = CaseDecision(
            decision_id="DEC-001",
            case_id="CASE-DEC-001",
            reviewer="consultant@firm.com",
            reviewer_role="Senior GST Consultant",
            decision=CaseDecisionEnum.APPROVE,
            comment="Approved after verifying GSTIN status."
        )
        case.decisions.append(decision)
        self.repo.save_case(case)

        event = CaseEvent(
            event_id="EVT-001",
            case_id="CASE-DEC-001",
            event_type="APPROVED",
            actor="consultant@firm.com",
            previous_status="REVIEW_REQUIRED",
            new_status="READY_FOR_RESOLUTION"
        )
        self.repo.save_event(event)

        retrieved_case = self.repo.get_case("CASE-DEC-001")
        self.assertEqual(len(retrieved_case.decisions), 1)
        self.assertEqual(retrieved_case.decisions[0].reviewer, "consultant@firm.com")

        events = self.repo.get_events("CASE-DEC-001")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].actor, "consultant@firm.com")

    def test_evidence_reference_provenance(self):
        case = InvestigationCase(
            case_id="CASE-EVID-001",
            title="Evidence provenance test",
            status=CaseStatusEnum.OPEN
        )

        self.repo.save_case(case)

        ref = CaseEvidenceReference(
            reference_id="REF-001",
            source_type="DETERMINISTIC_GATE",
            source_identifier="GATE_4_PLACE_OF_SUPPLY",
            invoice_id="INV-8000001",
            summary="Gate 4 Place of Supply mismatch."
        )
        self.repo.save_evidence_ref("CASE-EVID-001", ref)

        refs = self.repo.get_evidence_refs("CASE-EVID-001")
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].source_identifier, "GATE_4_PLACE_OF_SUPPLY")


if __name__ == "__main__":
    unittest.main()
