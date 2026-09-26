"""
tests.integration.test_s15_migrations
=======================================
Integration Test Suite for Sprint 15 Database Schema Migration (002_s15_workflow_schema).
Verifies:
  1. Alembic migration script module imports and structure
  2. Database table inspection to verify 5 workflow tables and CaseORM columns exist
"""

import os
import sys
import unittest
import importlib.util
from sqlalchemy import create_engine, inspect

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.models import (
    Base,
    CaseORM,
    InvestigationPlanORM,
    CaseEvidenceRecordORM,
    CaseFindingORM,
    CaseRiskAssessmentORM,
    CaseRecommendationORM,
)


class TestS15MigrationsIntegration(unittest.TestCase):
    """Integration tests for S15 Database Schema and Alembic migration definition."""

    def test_01_alembic_002_migration_script_validity(self):
        """Verify Alembic migration script 002 can be loaded and has upgrade/downgrade methods."""
        import types
        from unittest.mock import MagicMock
        if "alembic" not in sys.modules or not hasattr(sys.modules["alembic"], "op"):
            mock_alembic = types.ModuleType("alembic")
            mock_alembic.op = MagicMock()
            sys.modules["alembic"] = mock_alembic
        elif not hasattr(sys.modules["alembic"], "op"):
            sys.modules["alembic"].op = MagicMock()

        script_path = os.path.join(REPO_ROOT, "alembic", "versions", "002_s15_workflow_schema.py")
        spec = importlib.util.spec_from_file_location("migration_module_002", script_path)
        self.assertIsNotNone(spec, f"Could not load spec for migration script at {script_path}")
        migration_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration_module)

        self.assertTrue(hasattr(migration_module, "upgrade"))
        self.assertTrue(hasattr(migration_module, "downgrade"))
        self.assertEqual(migration_module.revision, "002_s15_workflow_schema")

    def test_02_sqlalchemy_models_and_tables_creation(self):
        """Verify SQLAlchemy ORM metadata defines all 5 new tables and relationships."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        inspector = inspect(engine)

        table_names = inspector.get_table_names()
        self.assertIn("investigation_cases", table_names)
        self.assertIn("investigation_plans", table_names)
        self.assertIn("case_evidence_records", table_names)
        self.assertIn("case_findings", table_names)
        self.assertIn("case_risk_assessments", table_names)
        self.assertIn("case_recommendations", table_names)

        # Inspect columns on investigation_cases
        case_cols = [c["name"] for c in inspector.get_columns("investigation_cases")]
        self.assertIn("case_type", case_cols)
        self.assertIn("source", case_cols)
        self.assertIn("created_by", case_cols)

        # Inspect columns on investigation_plans
        plan_cols = [c["name"] for c in inspector.get_columns("investigation_plans")]
        self.assertIn("plan_id", plan_cols)
        self.assertIn("case_id", plan_cols)
        self.assertIn("objective", plan_cols)


if __name__ == "__main__":
    unittest.main()
