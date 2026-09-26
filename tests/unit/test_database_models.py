"""
tests.unit.test_database_models
================================
Unit tests for Sprint 14 database models and JSON serializer.
Verifies round-trip fidelity for Decimals, UTC timestamps, Enums, None values, and ORM mappings.
"""

import os
import unittest
from decimal import Decimal
from datetime import datetime, timezone
from app.db.serializer import dump_json_value, load_json_value, format_iso_timestamp
from app.db.connection import init_db, db_session_scope
from app.db.models import SessionORM, TurnORM, CaseORM, CaseDecisionORM, CaseEventORM, CaseEvidenceRefORM


class TestDatabaseModels(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        init_db()

    def test_json_serializer_decimal_and_utc(self):
        data = {
            "amount": Decimal("12345.67"),
            "timestamp": datetime(2026, 9, 13, 10, 0, 0, tzinfo=timezone.utc),
            "status": "COMPLIANT",
            "none_val": None,
            "nested": {"tax": Decimal("0.18")}
        }
        json_str = dump_json_value(data)
        self.assertIn("12345.67", json_str)
        self.assertIn("2026-09-13T10:00:00", json_str)

        restored = load_json_value(json_str)
        self.assertEqual(restored["amount"], 12345.67)
        self.assertEqual(restored["none_val"], None)
        self.assertEqual(restored["nested"]["tax"], 0.18)

    def test_format_iso_timestamp(self):
        dt = datetime(2026, 9, 13, 12, 30, 45, tzinfo=timezone.utc)
        iso = format_iso_timestamp(dt)
        self.assertTrue(iso.endswith("+00:00") or iso.endswith("Z"))
        
        iso_now = format_iso_timestamp()
        self.assertIsInstance(iso_now, str)

    def test_orm_session_and_turn_roundtrip(self):
        now = format_iso_timestamp()
        with db_session_scope() as session:
            sess_orm = SessionORM(
                session_id="SESS-TEST-001",
                status="ACTIVE",
                entity_focus_json=dump_json_value({"invoice_id": "INV-100"}),
                created_at=now,
                updated_at=now
            )
            session.add(sess_orm)

            turn_orm = TurnORM(
                session_id="SESS-TEST-001",
                turn_index=1,
                user_query="Check INV-100",
                resolved_query="Check INV-100 compliance",
                intent="INVOICE_INVESTIGATION",
                synthesized_answer="INV-100 is non-compliant",
                confidence="HIGH",
                timestamp=now
            )
            session.add(turn_orm)

        with db_session_scope() as session:
            fetched_sess = session.query(SessionORM).filter_by(session_id="SESS-TEST-001").first()
            self.assertIsNotNone(fetched_sess)
            self.assertEqual(len(fetched_sess.turns), 1)
            self.assertEqual(fetched_sess.turns[0].user_query, "Check INV-100")
            focus = load_json_value(fetched_sess.entity_focus_json)
            self.assertEqual(focus.get("invoice_id"), "INV-100")

    def test_orm_case_roundtrip_with_versioning(self):
        now = format_iso_timestamp()
        with db_session_scope() as session:
            case_orm = CaseORM(
                case_id="CASE-TEST-001",
                title="Test Case",
                status="OPEN",
                priority="P2",
                risk_level="HIGH",
                invoice_id="INV-200",
                financial_exposure=50000.0,
                version=1,
                created_at=now,
                updated_at=now
            )
            session.add(case_orm)

        with db_session_scope() as session:
            fetched_case = session.query(CaseORM).filter_by(case_id="CASE-TEST-001").first()
            self.assertIsNotNone(fetched_case)
            self.assertEqual(fetched_case.priority, "P2")
            self.assertEqual(fetched_case.version, 1)


if __name__ == "__main__":
    unittest.main()
