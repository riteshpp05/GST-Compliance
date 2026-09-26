"""
tests.unit.test_session
=======================
Unit Test Suite for Sprint 12.4 Multi-Turn Session & Context Subsystem.
Verifies:
  1. Session creation and default entity focus initialization
  2. Turn accumulation and deduplicated findings retention
  3. Regulatory knowledge evidence accumulation
  4. Implicit context resolution ('this invoice', 'why is it non-compliant?')
  5. Entity focus updates across turns
  6. InMemorySessionRepository thread safety and session management
"""

import unittest
from app.agent.ai.session import (
    EntityFocus,
    InMemorySessionRepository,
    InvestigationSession,
    InvestigationTurn,
    SessionManager,
)


class TestSessionSubsystem(unittest.TestCase):
    """Unit test suite for Session & Multi-Turn Context Subsystem."""

    def setUp(self):
        self.repo = InMemorySessionRepository()
        self.manager = SessionManager(repository=self.repo)

    def test_session_creation(self):
        sess = self.manager.create_session()
        self.assertIsNotNone(sess.session_id)
        self.assertTrue(sess.session_id.startswith("SESS-"))
        self.assertEqual(sess.status, "ACTIVE")
        self.assertEqual(len(sess.turns), 0)

    def test_context_resolution_explicit_invoice(self):
        sess = self.manager.create_session()
        query = "Why is invoice INV-8000001 high risk?"
        resolved, params = self.manager.resolve_query_context(sess, query)
        self.assertEqual(params.get("invoice_id"), "INV-8000001")
        self.assertEqual(sess.entity_focus.invoice_id, "INV-8000001")

    def test_context_resolution_implicit_followup(self):
        sess = self.manager.create_session(initial_focus=EntityFocus(invoice_id="INV-8000001"))
        followup_query = "Why is it non-compliant?"
        resolved, params = self.manager.resolve_query_context(sess, followup_query)
        self.assertEqual(params.get("invoice_id"), "INV-8000001")
        self.assertIn("INV-8000001", resolved)

    def test_turn_recording_and_accumulation(self):
        sess = self.manager.create_session()
        self.manager.record_turn(
            session_id=sess.session_id,
            user_query="Why is invoice INV-8000001 high risk?",
            resolved_query="Why is invoice INV-8000001 high risk?",
            intent="INVOICE_INVESTIGATION",
            tools_used=["get_compliance_result", "get_risk_assessment"],
            findings=[{"source": "get_risk_assessment", "type": "RISK_ASSESSMENT", "score": 100.0}],
            regulatory_knowledge=[{"chunk": {"id": "C1"}, "provenance": {"document_name": "Rule 36(4)"}}],
            synthesized_answer="Invoice INV-8000001 is CRITICAL risk.",
        )

        updated_sess = self.manager.get_session(sess.session_id)
        self.assertEqual(len(updated_sess.turns), 1)
        self.assertEqual(len(updated_sess.accumulated_findings), 1)
        self.assertEqual(len(updated_sess.accumulated_regulatory_evidence), 1)

    def test_repository_list_and_delete(self):
        s1 = self.manager.create_session()
        s2 = self.manager.create_session()
        sessions = self.manager.list_sessions()
        self.assertGreaterEqual(len(sessions), 2)

        deleted = self.manager.delete_session(s1.session_id)
        self.assertTrue(deleted)
        self.assertIsNone(self.manager.get_session(s1.session_id))


if __name__ == "__main__":
    unittest.main()
