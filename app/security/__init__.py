"""
app.security
============
Security, Authentication, RBAC, Authorization, and Audit Module for UC15 (Sprint 16).
"""
from app.security.rbac import RoleEnum, PermissionEnum, ROLE_PERMISSIONS_MATRIX
from app.security.auth import AuthenticatedPrincipal, AuthenticationService, get_internal_compatibility_principal
from app.security.authorization import PermissionEvaluator, CaseAccessControl
from app.security.audit import SecurityAuditLogger, SecurityAuditEvent, AuditEventTypeEnum, get_security_audit_logger
from app.security.exceptions import (
    SecurityException,
    AuthenticationException,
    ForbiddenException,
    CaseAccessDeniedException,
    ToolPermissionDeniedException,
    ToolExecutionTimeoutException,
    ToolInputValidationException,
    ToolOutputValidationException,
)

__all__ = [
    "RoleEnum",
    "PermissionEnum",
    "ROLE_PERMISSIONS_MATRIX",
    "AuthenticatedPrincipal",
    "AuthenticationService",
    "get_internal_compatibility_principal",
    "PermissionEvaluator",
    "CaseAccessControl",
    "SecurityAuditLogger",
    "SecurityAuditEvent",
    "AuditEventTypeEnum",
    "get_security_audit_logger",
    "SecurityException",
    "AuthenticationException",
    "ForbiddenException",
    "CaseAccessDeniedException",
    "ToolPermissionDeniedException",
    "ToolExecutionTimeoutException",
    "ToolInputValidationException",
    "ToolOutputValidationException",
]
