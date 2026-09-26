"""
tests.unit.test_repository_factory
===================================
Unit tests for repository factory dynamic selection based on PERSISTENCE_BACKEND.
"""

import os
import unittest
from app.agent.ai.session import get_session_manager, _session_manager, InMemorySessionRepository
from app.agent.ai.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.case.repository import get_case_repository, _case_repository, InMemoryCaseRepository
from app.case.sqlalchemy_case_repository import SQLAlchemyCaseRepository


class TestRepositoryFactory(unittest.TestCase):

    def setUp(self):
        # Reset globals
        import app.agent.ai.session as sess_module
        import app.case.repository as repo_module
        sess_module._session_manager = None
        repo_module._case_repository = None

    def test_factory_memory_backend(self):
        os.environ["PERSISTENCE_BACKEND"] = "memory"
        
        sm = get_session_manager()
        self.assertIsInstance(sm.repository, InMemorySessionRepository)

        import app.case.repository as repo_module
        repo_module._case_repository = None
        cr = get_case_repository()
        self.assertIsInstance(cr, InMemoryCaseRepository)

    def test_factory_db_backend(self):
        os.environ["PERSISTENCE_BACKEND"] = "sqlite"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"

        import app.agent.ai.session as sess_module
        import app.case.repository as repo_module
        sess_module._session_manager = None
        repo_module._case_repository = None

        sm = get_session_manager()
        self.assertIsInstance(sm.repository, SQLAlchemySessionRepository)

        cr = get_case_repository()
        self.assertIsInstance(cr, SQLAlchemyCaseRepository)


if __name__ == "__main__":
    unittest.main()
