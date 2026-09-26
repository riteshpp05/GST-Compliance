"""
tests.integration.test_postgres_session_repository
===================================================
Integration tests for SQLAlchemySessionRepository implementing BaseSessionRepository.
Verifies persistence, retrieval, entity focus updates, turn appends, listing, and deletion.
"""

import os
import unittest
from app.db.connection import init_db, reset_db_connection
from app.agent.ai.session import InvestigationSession, EntityFocus, InvestigationTurn
from app.agent.ai.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.agent.ai.models import InvestigationIntentEnum




class TestPostgresSessionRepository(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        init_db()

    def setUp(self):
        reset_db_connection()
        init_db()
        self.repo = SQLAlchemySessionRepository()

    def test_save_and_get_session(self):
        session = InvestigationSession(session_id="SESS-INTEG-001")
        session.entity_focus.invoice_id = "INV-8000001"
        self.repo.save_session(session)

        retrieved = self.repo.get_session("SESS-INTEG-001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.session_id, "SESS-INTEG-001")
        self.assertEqual(retrieved.entity_focus.invoice_id, "INV-8000001")

    def test_add_turns_and_accumulated_findings(self):
        session = InvestigationSession(session_id="SESS-INTEG-002")
        turn = InvestigationTurn(
            turn_index=1,
            user_query="Why is INV-8000001 high risk?",
            resolved_query="Why is INV-8000001 high risk?",
            intent=InvestigationIntentEnum.INVOICE_INVESTIGATION,
            tools_used=["get_compliance_result"],
            findings=[{"invoice_id": "INV-8000001", "risk_score": 85}],

            synthesized_answer="INV-8000001 failed Gate 4 Intra-State tax classification.",
            confidence="HIGH"
        )
        session.add_turn(turn)
        self.repo.save_session(session)

        retrieved = self.repo.get_session("SESS-INTEG-002")
        self.assertIsNotNone(retrieved)
        self.assertEqual(len(retrieved.turns), 1)
        self.assertEqual(retrieved.turns[0].turn_index, 1)
        self.assertEqual(retrieved.turns[0].user_query, "Why is INV-8000001 high risk?")

    def test_list_and_delete_sessions(self):
        s1 = InvestigationSession(session_id="SESS-LIST-001")
        s2 = InvestigationSession(session_id="SESS-LIST-002")
        self.repo.save_session(s1)
        self.repo.save_session(s2)

        sessions = self.repo.list_sessions()
        session_ids = [s.session_id for s in sessions]
        self.assertIn("SESS-LIST-001", session_ids)
        self.assertIn("SESS-LIST-002", session_ids)

        deleted = self.repo.delete_session("SESS-LIST-001")
        self.assertTrue(deleted)
        self.assertIsNone(self.repo.get_session("SESS-LIST-001"))


if __name__ == "__main__":
    unittest.main()
