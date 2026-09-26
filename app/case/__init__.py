"""
app.case package
================
Sprint 13 Case Management & Human Approval Subsystem.
Exposes Case domain models, StateMachine, Repository, and CaseService.
"""

from app.case.models import (
    CaseAssignment,
    CaseAssignRequest,
    CaseCreateRequest,
    CaseDecision,
    CaseDecisionEnum,
    CaseEvent,
    CaseEvidenceRecord,
    CaseEvidenceReference,
    CaseEventTypeEnum,
    CaseFinding,
    CaseRecommendation,
    CaseReviewRequest,
    CaseRiskAssessment,
    CaseStatusEnum,
    CaseTriageRequest,
    CaseTriageResult,
    EvidenceCreateRequest,
    FindingCreateRequest,
    InvestigationCase,
    InvestigationPlanCreateRequest,
    InvestigationPlanDomain,
    RecommendationCreateRequest,
    RiskAssessmentCreateRequest,
)
from app.case.repository import BaseCaseRepository, InMemoryCaseRepository, get_case_repository
from app.case.service import CaseService, get_case_service, reset_case_service
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError

__all__ = [
    "CaseStatusEnum",
    "CaseDecisionEnum",
    "CaseEventTypeEnum",
    "CaseEvidenceReference",
    "CaseDecision",
    "CaseEvent",
    "CaseAssignment",
    "InvestigationCase",
    "InvestigationPlanDomain",
    "CaseEvidenceRecord",
    "CaseFinding",
    "CaseRiskAssessment",
    "CaseRecommendation",
    "CaseTriageResult",
    "CaseCreateRequest",
    "CaseTriageRequest",
    "CaseAssignRequest",
    "CaseReviewRequest",
    "InvestigationPlanCreateRequest",
    "EvidenceCreateRequest",
    "FindingCreateRequest",
    "RiskAssessmentCreateRequest",
    "RecommendationCreateRequest",
    "CaseStateTransitionError",
    "CaseStateMachine",
    "BaseCaseRepository",
    "InMemoryCaseRepository",
    "get_case_repository",
    "CaseService",
    "get_case_service",
    "reset_case_service",
]
