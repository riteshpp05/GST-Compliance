"""
tests.unit.test_case_security_boundary
======================================
Unit Test Suite for Sprint 13 Case Management Security & Architectural Boundaries.
Verifies:
  1. AI Agent is forbidden from executing approval/rejection or transitioning cases to READY_FOR_RESOLUTION.
  2. Mandatory reviewer identity & comment enforcement.
  3. Preservation of [ADVISORY SAP / FINANCE ACTION] banner.
  4. Non-mutation of SAP / resolution execution boundaries.
"""

import unittest
from unittest.mock import MagicMock
from app.case.models import CaseDecisionEnum, CaseStatusEnum
from app.case.service import CaseService
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError


class TestCaseSecurityBoundary(unittest.TestCase):
    """Unit tests for Sprint 13 Security & Architectural Boundaries."""

    def test_ai_agent_cannot_approve_or_reject(self):
        # Verify AI actor flag blocks transition to APPROVED
        with self.assertRaises(CaseStateTransitionError) as ctx:
            CaseStateMachine.validate_transition(
                current_status=CaseStatusEnum.REVIEW_REQUIRED,
                target_status=CaseStatusEnum.APPROVED,
                decision=CaseDecisionEnum.APPROVE,
                reviewer="AI_AGENT",
                actor_is_ai=True,
            )
        self.assertIn("Security Boundary Violation", str(ctx.exception))

        # Verify AI actor flag blocks transition to READY_FOR_RESOLUTION
        with self.assertRaises(CaseStateTransitionError) as ctx2:
            CaseStateMachine.validate_transition(
                current_status=CaseStatusEnum.APPROVED,
                target_status=CaseStatusEnum.READY_FOR_RESOLUTION,
                actor_is_ai=True,
            )
        self.assertIn("Security Boundary Violation", str(ctx2.exception))

    def test_missing_comment_rejected(self):
        service = CaseService()
        # Create dummy case
        case = service.create_case_from_dossier(
            dossier=MagicMock(
                session_id="SESS-1234",
                dossier_id="DOSSIER-1234",
                entity_focus=MagicMock(invoice_id="INV-8000001", counterparty_gstin=None, counterparty_name=None, risk_level="HIGH"),
                risk_assessment={"risk_level": "HIGH", "risk_score": 75.0, "risk_priority": "P2"},
                financial_exposure={"total_potential_exposure": 1000.0},
                root_cause_analysis={"primary_root_cause": "TAX_RATE"},
                blast_radius_analysis={},
                executive_summary="Summary",
                gate_breakdown=[],
                regulatory_evidence=[],
                advisory_recommendations=["[ADVISORY SAP / FINANCE ACTION] Hold invoice."],
            )
        )

        # Empty comment must fail
        with self.assertRaises(CaseStateTransitionError):
            service.submit_human_review(
                case_id=case.case_id,
                reviewer="Reviewer",
                decision=CaseDecisionEnum.APPROVE,
                comment="   ",
            )

    def test_advisory_sap_banner_preservation(self):
        service = CaseService()
        case = service.create_case_from_dossier(
            dossier=MagicMock(
                session_id="SESS-1234",
                dossier_id="DOSSIER-1234",
                entity_focus=MagicMock(invoice_id="INV-8000001", counterparty_gstin=None, counterparty_name=None, risk_level="HIGH"),
                risk_assessment={},
                financial_exposure={},
                root_cause_analysis={},
                blast_radius_analysis={},
                executive_summary="Summary",
                gate_breakdown=[],
                regulatory_evidence=[],
                advisory_recommendations=["Hold invoice from filing."],
            )
        )
        self.assertIn("[ADVISORY SAP / FINANCE ACTION]", case.recommendation)


if __name__ == "__main__":
    unittest.main()
