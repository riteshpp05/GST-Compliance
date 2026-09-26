"""
app.security.rbac
=================
Role-Based Access Control (RBAC) definitions and permission matrix for UC15 (Sprint 16).
"""

from enum import Enum
from typing import Dict, Set


class RoleEnum(str, Enum):
    """System roles in UC15."""
    ADMIN = "ADMIN"
    INVESTIGATOR = "INVESTIGATOR"
    REVIEWER = "REVIEWER"
    ANALYST = "ANALYST"
    AUDITOR = "AUDITOR"
    AI_AGENT = "AI_AGENT"


class PermissionEnum(str, Enum):
    """Granular permission definitions across UC15 domain and case operations."""
    # Case Lifecycle Permissions
    CASE_CREATE = "case:create"
    CASE_READ = "case:read"
    CASE_TRIAGE = "case:triage"
    CASE_UPDATE = "case:update"
    CASE_LIST = "case:list"
    CASE_ASSIGN = "case:assign"

    # Investigation & Findings Permissions
    INVESTIGATION_START = "investigation:start"
    INVESTIGATION_PLAN_CREATE = "investigation_plan:create"
    EVIDENCE_CREATE = "evidence:create"
    FINDING_CREATE = "finding:create"
    RISK_ASSESS = "risk:assess"
    RECOMMENDATION_CREATE = "recommendation:create"
    REQUEST_MORE_EVIDENCE = "investigation:request_more_evidence"

    # Human Review & Resolution Permissions (STRICT HUMAN CONTROL)
    REVIEW_SUBMIT = "review:submit"
    APPROVE_CASE = "case:approve"
    REJECT_CASE = "case:reject"
    RESOLVE_CASE = "case:resolve"
    CLOSE_CASE = "case:close"

    # Tool Execution & Knowledge Access Permissions
    TOOL_EXECUTE = "tool:execute"
    KNOWLEDGE_RETRIEVE = "knowledge:retrieve"
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"

    # Data Ingestion & Data Quality Permissions (Sprint 17)
    DATA_INGEST = "data:ingest"
    DATA_READ = "data:read"
    DATA_VALIDATE = "data:validate"
    DATA_REPROCESS = "data:reprocess"
    DATA_ADMIN = "data:admin"


# Centralized Permission Matrix
# Note: AI_AGENT has EXPLICITLY 0 permissions for APPROVE_CASE, REJECT_CASE, RESOLVE_CASE, CLOSE_CASE.
ROLE_PERMISSIONS_MATRIX: Dict[RoleEnum, Set[PermissionEnum]] = {
    RoleEnum.ADMIN: set(PermissionEnum),

    RoleEnum.INVESTIGATOR: {
        PermissionEnum.CASE_CREATE,
        PermissionEnum.CASE_READ,
        PermissionEnum.CASE_TRIAGE,
        PermissionEnum.CASE_UPDATE,
        PermissionEnum.CASE_LIST,
        PermissionEnum.INVESTIGATION_START,
        PermissionEnum.INVESTIGATION_PLAN_CREATE,
        PermissionEnum.EVIDENCE_CREATE,
        PermissionEnum.FINDING_CREATE,
        PermissionEnum.RISK_ASSESS,
        PermissionEnum.RECOMMENDATION_CREATE,
        PermissionEnum.REQUEST_MORE_EVIDENCE,
        PermissionEnum.REVIEW_SUBMIT,
        PermissionEnum.TOOL_EXECUTE,
        PermissionEnum.KNOWLEDGE_RETRIEVE,
        PermissionEnum.AUDIT_READ,
        PermissionEnum.DATA_INGEST,
        PermissionEnum.DATA_READ,
        PermissionEnum.DATA_VALIDATE,
        PermissionEnum.DATA_REPROCESS,
    },

    RoleEnum.REVIEWER: {
        PermissionEnum.CASE_READ,
        PermissionEnum.CASE_TRIAGE,
        PermissionEnum.CASE_LIST,
        PermissionEnum.CASE_ASSIGN,
        PermissionEnum.REVIEW_SUBMIT,
        PermissionEnum.REQUEST_MORE_EVIDENCE,
        PermissionEnum.APPROVE_CASE,
        PermissionEnum.REJECT_CASE,
        PermissionEnum.RESOLVE_CASE,
        PermissionEnum.CLOSE_CASE,
        PermissionEnum.TOOL_EXECUTE,
        PermissionEnum.KNOWLEDGE_RETRIEVE,
        PermissionEnum.AUDIT_READ,
        PermissionEnum.DATA_READ,
        PermissionEnum.DATA_VALIDATE,
    },

    RoleEnum.ANALYST: {
        PermissionEnum.CASE_READ,
        PermissionEnum.CASE_LIST,
        PermissionEnum.EVIDENCE_CREATE,
        PermissionEnum.FINDING_CREATE,
        PermissionEnum.RISK_ASSESS,
        PermissionEnum.RECOMMENDATION_CREATE,
        PermissionEnum.TOOL_EXECUTE,
        PermissionEnum.KNOWLEDGE_RETRIEVE,
        PermissionEnum.AUDIT_READ,
        PermissionEnum.DATA_INGEST,
        PermissionEnum.DATA_READ,
        PermissionEnum.DATA_VALIDATE,
    },

    RoleEnum.AUDITOR: {
        PermissionEnum.CASE_READ,
        PermissionEnum.CASE_LIST,
        PermissionEnum.KNOWLEDGE_RETRIEVE,
        PermissionEnum.AUDIT_READ,
        PermissionEnum.DATA_READ,
    },

    # AI_AGENT: Can investigate, collect evidence, assess risk, create findings/recommendations,
    # ingest data, read data, validate data,
    # BUT CANNOT approve, reject, resolve, or close cases under any circumstance.
    RoleEnum.AI_AGENT: {
        PermissionEnum.CASE_CREATE,
        PermissionEnum.CASE_READ,
        PermissionEnum.CASE_LIST,
        PermissionEnum.INVESTIGATION_START,
        PermissionEnum.INVESTIGATION_PLAN_CREATE,
        PermissionEnum.EVIDENCE_CREATE,
        PermissionEnum.FINDING_CREATE,
        PermissionEnum.RISK_ASSESS,
        PermissionEnum.RECOMMENDATION_CREATE,
        PermissionEnum.REQUEST_MORE_EVIDENCE,
        PermissionEnum.TOOL_EXECUTE,
        PermissionEnum.KNOWLEDGE_RETRIEVE,
        PermissionEnum.DATA_INGEST,
        PermissionEnum.DATA_READ,
        PermissionEnum.DATA_VALIDATE,
    },
}


# Human-Only Resolution Permissions Set
HUMAN_ONLY_RESOLUTIONS: Set[PermissionEnum] = {
    PermissionEnum.APPROVE_CASE,
    PermissionEnum.REJECT_CASE,
    PermissionEnum.RESOLVE_CASE,
    PermissionEnum.CLOSE_CASE,
}
