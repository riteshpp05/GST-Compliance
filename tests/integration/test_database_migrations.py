"""
tests.integration.test_database_migrations
============================================
Integration test verifying Alembic database migration capabilities.
"""

import os
import unittest
try:
    from alembic.config import Config
    from alembic import command
    HAS_ALEMBIC = True
except (ImportError, ModuleNotFoundError):
    HAS_ALEMBIC = False
from app.db.connection import get_db_engine, reset_db_connection
from sqlalchemy import inspect


class TestDatabaseMigrations(unittest.TestCase):

    def setUp(self):
        if not HAS_ALEMBIC:
            self.skipTest("Alembic library not installed in Python environment")
        self.db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "test_mig.db")
        )
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
            
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.db_path}"
        reset_db_connection()

    def tearDown(self):
        reset_db_connection()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_alembic_upgrade_and_downgrade(self):
        alembic_cfg_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "alembic.ini")
        )
        alembic_cfg = Config(alembic_cfg_path)

        # Run upgrade head
        command.upgrade(alembic_cfg, "head")

        engine = get_db_engine()
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = {
            "investigation_sessions",
            "investigation_turns",
            "investigation_cases",
            "case_decisions",
            "case_events",
            "case_evidence_references",
        }
        for tbl in expected_tables:
            self.assertIn(tbl, tables)

        # Run downgrade base
        command.downgrade(alembic_cfg, "base")
        inspector_after = inspect(get_db_engine())
        tables_after = inspector_after.get_table_names()
        for tbl in expected_tables:
            self.assertNotIn(tbl, tables_after)


if __name__ == "__main__":
    unittest.main()
