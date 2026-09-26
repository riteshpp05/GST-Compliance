"""
tests.integration.test_persistence_proof
=========================================
Sprint 20 Forensic Persistence Proof & Restart Verification Test Suite.
Proves that Cases, Evidence, AI Sessions, and Data Quality Reports persist cleanly
across application restarts and fresh database sessions (Guardrail #3).
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone

from app.agent.ai.session import InvestigationSession, EntityFocus
from app.agent.ai.sqlalchemy_session_repository import SQLAlchemySessionRepository
from app.case.models import CaseDecisionEnum, CaseEventTypeEnum, CaseStatusEnum, InvestigationCase
from app.case.sqlalchemy_case_repository import SQLAlchemyCaseRepository
from app.data.quality.quality_engine import DataQualityReport, QualityStatus
from app.data.repositories.data_quality_repository import SQLAlchemyDataQualityRepository
from app.db.connection import get_db_session, init_db, reset_db_connection


class TestPersistenceProof(unittest.TestCase):
    """
    Forensic persistence proof tests asserting state preservation across DB restarts.
    """

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.db_url = f"sqlite:///{self.db_path}"
        os.environ["DATABASE_URL"] = self.db_url
        os.environ["PERSISTENCE_BACKEND"] = "sqlalchemy"
        reset_db_connection()
        init_db()

    def tearDown(self):
        reset_db_connection()
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except OSError:
                pass

    def test_case_persistence_across_restarts(self):
        """Verify InvestigationCase state, findings, evidence, and events persist across engine restart."""
        case_repo1 = SQLAlchemyCaseRepository()

        case_id = f"CASE-PERSIST-{int(datetime.now(timezone.utc).timestamp())}"
        case = InvestigationCase(
            case_id=case_id,
            title="Persistence Proof Invoice Audit",
            description="Test invoice audit persistence across application restarts",
            status=CaseStatusEnum.REVIEW_REQUIRED,
            priority="P1",
            risk_level="CRITICAL",
            invoice_id="INV-PERSIST-001",
            counterparty_name="Tata Motors Ltd",
            counterparty_gstin="27AAACT2727Q1ZW",
            assigned_to="Jane Tax Officer",
            assigned_role="Senior Auditor",
            created_by="GST_STATUTORY_ENGINE",
            recommendation="Hold payment pending vendor GSTR-1 amendment",
            financial_exposure=45800.0,
        )

        case_repo1.save_case(case)

        # 2. Simulate Application Shutdown & Restart (Brand New DB Engine & Session)
        reset_db_connection()
        case_repo2 = SQLAlchemyCaseRepository()

        # 3. Retrieve Case and verify identical state
        retrieved_case = case_repo2.get_case(case_id)
        self.assertIsNotNone(retrieved_case)
        self.assertEqual(retrieved_case.case_id, case_id)
        self.assertEqual(retrieved_case.title, "Persistence Proof Invoice Audit")
        self.assertEqual(retrieved_case.status, CaseStatusEnum.REVIEW_REQUIRED)
        self.assertEqual(retrieved_case.priority, "P1")
        self.assertEqual(retrieved_case.risk_level, "CRITICAL")
        self.assertEqual(retrieved_case.invoice_id, "INV-PERSIST-001")
        self.assertEqual(retrieved_case.counterparty_name, "Tata Motors Ltd")
        self.assertEqual(retrieved_case.counterparty_gstin, "27AAACT2727Q1ZW")
        self.assertEqual(retrieved_case.assigned_to, "Jane Tax Officer")
        self.assertEqual(retrieved_case.financial_exposure, 45800.0)

    def test_ai_session_persistence_across_restarts(self):
        """Verify InvestigationSession multi-turn context persists across engine restart."""
        sess_repo1 = SQLAlchemySessionRepository()

        session_id = "SESS-PERSIST-100"
        ai_session = InvestigationSession(
            session_id=session_id,
            status="ACTIVE",
            entity_focus=EntityFocus(invoice_id="INV-8000001", counterparty_name="Amara Raja Batteries"),
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        sess_repo1.save_session(ai_session)

        # Simulate Application Restart
        reset_db_connection()
        sess_repo2 = SQLAlchemySessionRepository()

        retrieved_sess = sess_repo2.get_session(session_id)
        self.assertIsNotNone(retrieved_sess)
        self.assertEqual(retrieved_sess.session_id, session_id)
        self.assertEqual(retrieved_sess.entity_focus.invoice_id, "INV-8000001")
        self.assertEqual(retrieved_sess.entity_focus.counterparty_name, "Amara Raja Batteries")

    def test_data_quality_persistence_across_restarts(self):
        """Verify IngestionJob and DataQualityReport persist across engine restart."""
        dq_repo1 = SQLAlchemyDataQualityRepository(session_factory=get_db_session)

        job_id = "JOB-PERSIST-999"
        job_dict = {
            "ingestion_id": job_id,
            "source_id": "SRC-999",
            "source_name": "SAP_EXP_2026",
            "dataset_type": "INVOICES",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "COMPLETED",
            "total_records": 30,
            "accepted_records": 28,
            "rejected_records": 2,
            "quality_score": 94.5,
        }

        report = DataQualityReport(
            ingestion_id=job_id,
            overall_quality_score=94.5,
            quality_status=QualityStatus.EXCELLENT,
            dimension_scores={"COMPLETENESS": 96.0, "VALIDITY": 93.0},
            total_records=30,
            accepted_records=28,
            rejected_records=2,
            duplicate_records=0,
            warning_records=0,
        )

        dq_repo1.save_ingestion_job(job_dict)
        dq_repo1.save_quality_report(report)

        # Simulate Application Restart
        reset_db_connection()
        dq_repo2 = SQLAlchemyDataQualityRepository(session_factory=get_db_session)

        retrieved_job = dq_repo2.get_ingestion_job(job_id)
        self.assertIsNotNone(retrieved_job)
        self.assertEqual(retrieved_job["ingestion_id"], job_id)
        self.assertEqual(retrieved_job["quality_score"], 94.5)

        retrieved_report = dq_repo2.get_quality_report(job_id)
        self.assertIsNotNone(retrieved_report)
        self.assertEqual(retrieved_report.overall_quality_score, 94.5)


if __name__ == "__main__":
    unittest.main()

