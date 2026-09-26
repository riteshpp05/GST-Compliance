"""
tests.unit.test_case_state_machine
===================================
Unit Test Suite for Sprint 13 Case State Machine & Transition Validation.
Verifies valid state machine transitions and enforces rejection of invalid transitions.
"""

import unittest
from app.case.models import CaseDecisionEnum, CaseStatusEnum
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError


class TestCaseStateMachine(unittest.TestCase):
    """Unit tests for CaseStateMachine lifecycle rules."""

    def test_valid_transitions(self):
        # OPEN -> INVESTIGATING
        CaseStateMachine.validate_transition(CaseStatusEnum.OPEN, CaseStatusEnum.INVESTIGATING)

        # INVESTIGATING -> REVIEW_REQUIRED
        CaseStateMachine.validate_transition(CaseStatusEnum.INVESTIGATING, CaseStatusEnum.REVIEW_REQUIRED)

        # REVIEW_REQUIRED -> APPROVED (with human decision)
        CaseStateMachine.validate_transition(
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.APPROVED,
            decision=CaseDecisionEnum.APPROVE,
            reviewer="John Manager",
        )

        # APPROVED -> READY_FOR_RESOLUTION
        CaseStateMachine.validate_transition(CaseStatusEnum.APPROVED, CaseStatusEnum.READY_FOR_RESOLUTION)

        # REVIEW_REQUIRED -> REJECTED
        CaseStateMachine.validate_transition(
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.REJECTED,
            decision=CaseDecisionEnum.REJECT,
            reviewer="John Manager",
        )

        # REVIEW_REQUIRED -> MORE_EVIDENCE_REQUIRED
        CaseStateMachine.validate_transition(
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.MORE_EVIDENCE_REQUIRED,
            decision=CaseDecisionEnum.REQUEST_MORE_EVIDENCE,
            reviewer="John Manager",
        )

        # MORE_EVIDENCE_REQUIRED -> INVESTIGATING
        CaseStateMachine.validate_transition(CaseStatusEnum.MORE_EVIDENCE_REQUIRED, CaseStatusEnum.INVESTIGATING)

    def test_invalid_transitions_rejected(self):
        # OPEN -> APPROVED (Illegal direct jump)
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(CaseStatusEnum.OPEN, CaseStatusEnum.APPROVED)

        # OPEN -> READY_FOR_RESOLUTION (Illegal direct jump)
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(CaseStatusEnum.OPEN, CaseStatusEnum.READY_FOR_RESOLUTION)

        # INVESTIGATING -> APPROVED (Illegal bypass of REVIEW_REQUIRED)
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(CaseStatusEnum.INVESTIGATING, CaseStatusEnum.APPROVED)

        # REVIEW_REQUIRED -> READY_FOR_RESOLUTION without APPROVED state first
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(CaseStatusEnum.REVIEW_REQUIRED, CaseStatusEnum.READY_FOR_RESOLUTION)

    def test_missing_decision_or_reviewer_fails(self):
        # Missing decision
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(
                CaseStatusEnum.REVIEW_REQUIRED,
                CaseStatusEnum.APPROVED,
                decision=None,
                reviewer="John Manager",
            )

        # Missing reviewer
        with self.assertRaises(CaseStateTransitionError):
            CaseStateMachine.validate_transition(
                CaseStatusEnum.REVIEW_REQUIRED,
                CaseStatusEnum.APPROVED,
                decision=CaseDecisionEnum.APPROVE,
                reviewer="",
            )


if __name__ == "__main__":
    unittest.main()
