"""
app.case.state_machine
======================
State Machine & Transition Validator for Investigation Cases (Sprint 13 & Sprint 15).
Enforces deterministic lifecycle transitions, human decision boundaries, and security rules.
Prevents arbitrary or automated status mutation into terminal/resolution states.
"""

from __future__ import annotations

from typing import Dict, Optional, Set
from app.case.models import CaseDecisionEnum, CaseStatusEnum
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CaseStateTransitionError(Exception):
    """Raised when an invalid case state transition or illegal automated decision is attempted."""
    pass


class CaseStateMachine:
    """
    Deterministic State Machine controlling lifecycle state transitions for InvestigationCase.
    Enforces strict rules:
      - Human approval/review is required to transition to terminal/resolution states.
      - AI cannot approve, reject, or transition cases to RESOLVED, CLOSED, APPROVED, or READY_FOR_RESOLUTION.
      - Transition from PENDING_REVIEW or REVIEW_REQUIRED requires an explicit human decision.
    """

    # Map of target_status -> set of allowed source_statuses
    _ALLOWED_TRANSITIONS: Dict[CaseStatusEnum, Set[CaseStatusEnum]] = {
        CaseStatusEnum.TRIAGED: {
            CaseStatusEnum.CREATED,
            CaseStatusEnum.OPEN,
        },
        CaseStatusEnum.INVESTIGATING: {
            CaseStatusEnum.CREATED,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.OPEN,
            CaseStatusEnum.MORE_EVIDENCE_REQUIRED,
            CaseStatusEnum.RETURNED_FOR_INVESTIGATION,
            CaseStatusEnum.ESCALATED,
        },
        CaseStatusEnum.EVIDENCE_COLLECTED: {
            CaseStatusEnum.INVESTIGATING,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.MORE_EVIDENCE_REQUIRED,
            CaseStatusEnum.RETURNED_FOR_INVESTIGATION,
        },
        CaseStatusEnum.FINDINGS_READY: {
            CaseStatusEnum.EVIDENCE_COLLECTED,
            CaseStatusEnum.INVESTIGATING,
        },
        CaseStatusEnum.RESOLUTION_PROPOSED: {
            CaseStatusEnum.FINDINGS_READY,
            CaseStatusEnum.EVIDENCE_COLLECTED,
            CaseStatusEnum.INVESTIGATING,
        },
        CaseStatusEnum.PENDING_REVIEW: {
            CaseStatusEnum.RESOLUTION_PROPOSED,
            CaseStatusEnum.FINDINGS_READY,
            CaseStatusEnum.EVIDENCE_COLLECTED,
            CaseStatusEnum.INVESTIGATING,
            CaseStatusEnum.ESCALATED,
        },
        CaseStatusEnum.REVIEW_REQUIRED: {
            CaseStatusEnum.CREATED,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.INVESTIGATING,
            CaseStatusEnum.OPEN,
            CaseStatusEnum.RESOLUTION_PROPOSED,
            CaseStatusEnum.FINDINGS_READY,
            CaseStatusEnum.EVIDENCE_COLLECTED,
            CaseStatusEnum.ESCALATED,
        },
        CaseStatusEnum.APPROVED: {
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.RESOLUTION_PROPOSED,
        },
        CaseStatusEnum.REJECTED: {
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.RESOLUTION_PROPOSED,
        },
        CaseStatusEnum.MORE_EVIDENCE_REQUIRED: {
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.RESOLUTION_PROPOSED,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.INVESTIGATING,
        },
        CaseStatusEnum.RETURNED_FOR_INVESTIGATION: {
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.RESOLUTION_PROPOSED,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.INVESTIGATING,
        },

        CaseStatusEnum.READY_FOR_RESOLUTION: {
            CaseStatusEnum.APPROVED,
        },
        CaseStatusEnum.ESCALATED: {
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.INVESTIGATING,
            CaseStatusEnum.EVIDENCE_COLLECTED,
            CaseStatusEnum.FINDINGS_READY,
        },
        CaseStatusEnum.RESOLVED: {
            CaseStatusEnum.APPROVED,
            CaseStatusEnum.READY_FOR_RESOLUTION,
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
        },
        CaseStatusEnum.CLOSED: {
            CaseStatusEnum.RESOLVED,
            CaseStatusEnum.APPROVED,
            CaseStatusEnum.REJECTED,
            CaseStatusEnum.READY_FOR_RESOLUTION,
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.REVIEW_REQUIRED,
            CaseStatusEnum.CANCELLED,
            CaseStatusEnum.ESCALATED,
        },
        CaseStatusEnum.CANCELLED: {
            CaseStatusEnum.CREATED,
            CaseStatusEnum.TRIAGED,
            CaseStatusEnum.OPEN,
            CaseStatusEnum.INVESTIGATING,
        },
    }

    @classmethod
    def validate_transition(
        cls,
        current_status: CaseStatusEnum,
        target_status: CaseStatusEnum,
        decision: Optional[CaseDecisionEnum] = None,
        reviewer: Optional[str] = None,
        actor_is_ai: bool = False,
    ) -> None:
        """
        Validate whether transitioning from current_status to target_status is permitted.
        Raises CaseStateTransitionError if transition is invalid or security boundary is violated.
        """
        # 1. AI Boundary Check: AI cannot perform human approval or transition to terminal/resolution states
        if actor_is_ai:
            forbidden_ai_targets = {
                CaseStatusEnum.APPROVED,
                CaseStatusEnum.REJECTED,
                CaseStatusEnum.READY_FOR_RESOLUTION,
                CaseStatusEnum.RESOLVED,
                CaseStatusEnum.CLOSED,
            }
            if target_status in forbidden_ai_targets:
                raise CaseStateTransitionError(
                    f"Security Boundary Violation: AI agent is forbidden from transitioning case to '{target_status.value}'."
                )

        # Convert string to Enum if needed
        if isinstance(current_status, str):
            try:
                current_status = CaseStatusEnum(current_status)
            except ValueError:
                pass
        if isinstance(target_status, str):
            try:
                target_status = CaseStatusEnum(target_status)
            except ValueError:
                pass

        # 2. Same status idempotent transition check
        if current_status == target_status:
            return

        # 3. Source-to-Target Allowed Transition Check
        allowed_sources = cls._ALLOWED_TRANSITIONS.get(target_status, set())
        if current_status not in allowed_sources:
            curr_val = current_status.value if hasattr(current_status, 'value') else str(current_status)
            targ_val = target_status.value if hasattr(target_status, 'value') else str(target_status)
            raise CaseStateTransitionError(
                f"Invalid Case State Transition: Cannot move from '{curr_val}' to '{targ_val}'."
            )

        # 4. Human Decision & Reviewer Identity Requirement Check
        review_outcomes = {
            CaseStatusEnum.APPROVED,
            CaseStatusEnum.REJECTED,
            CaseStatusEnum.MORE_EVIDENCE_REQUIRED,
            CaseStatusEnum.RETURNED_FOR_INVESTIGATION,
        }
        if target_status in review_outcomes:
            if not decision:
                raise CaseStateTransitionError(
                    f"State Transition Error: Moving from {current_status.value} to '{target_status.value}' requires an explicit human decision."
                )
            if not reviewer or not reviewer.strip():
                raise CaseStateTransitionError(
                    "State Transition Error: Reviewer identity must be explicitly provided for human review decisions."
                )

            # Validate decision enum maps correctly to target status
            if target_status == CaseStatusEnum.APPROVED and decision != CaseDecisionEnum.APPROVE:
                raise CaseStateTransitionError(f"Decision mismatch: Cannot transition to APPROVED with decision '{decision.value}'.")
            if target_status == CaseStatusEnum.REJECTED and decision != CaseDecisionEnum.REJECT:
                raise CaseStateTransitionError(f"Decision mismatch: Cannot transition to REJECTED with decision '{decision.value}'.")
            if target_status == CaseStatusEnum.MORE_EVIDENCE_REQUIRED and decision != CaseDecisionEnum.REQUEST_MORE_EVIDENCE:
                raise CaseStateTransitionError(f"Decision mismatch: Cannot transition to MORE_EVIDENCE_REQUIRED with decision '{decision.value}'.")
            if target_status == CaseStatusEnum.RETURNED_FOR_INVESTIGATION and decision != CaseDecisionEnum.RETURN_FOR_INVESTIGATION:
                raise CaseStateTransitionError(f"Decision mismatch: Cannot transition to RETURNED_FOR_INVESTIGATION with decision '{decision.value}'.")

        logger.info(f"State transition validated: '{current_status.value}' -> '{target_status.value}' (Actor AI: {actor_is_ai})")

