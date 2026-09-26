"""
app.security.audit
==================
Structured Security Audit Logging Service for UC15 (Sprint 16).
Records authentication failures, permission denials, tool executions, and security events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field

from app.infrastructure.logging import get_logger
from app.security.auth import AuthenticatedPrincipal

logger = get_logger(__name__)


class AuditEventTypeEnum(str, Enum):
    """Event types captured in the security audit trail."""
    AUTH_FAILURE = "AUTH_FAILURE"
    AUTHORIZATION_DENIED = "AUTHORIZATION_DENIED"
    CASE_ACCESS_DENIED = "CASE_ACCESS_DENIED"
    TOOL_EXECUTED = "TOOL_EXECUTED"
    TOOL_FAILED = "TOOL_FAILED"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    TOOL_VALIDATION_FAILED = "TOOL_VALIDATION_FAILED"
    CASE_STATE_CHANGE = "CASE_STATE_CHANGE"
    HUMAN_ACTION_ATTEMPT = "HUMAN_ACTION_ATTEMPT"


class SecurityAuditEvent(BaseModel):
    """Structured security audit event record."""
    event_id: str = Field(default_factory=lambda: f"AUD-SEC-{uuid.uuid4().hex[:8].upper()}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventTypeEnum = Field(..., description="Audit event category.")
    principal_id: str = Field(..., description="Principal ID involved.")
    username: str = Field("ANONYMOUS", description="Username or display name.")
    roles: List[str] = Field(default_factory=list, description="Roles held by principal.")
    tenant_id: str = Field("tenant_default", description="Tenant context.")
    operation: str = Field(..., description="Operation attempted or executed.")
    resource_id: Optional[str] = Field(None, description="Case ID or tool name or target resource.")
    status: str = Field("SUCCESS", description="SUCCESS, DENIED, FAILED, TIMEOUT, or INVALID.")
    reason: Optional[str] = Field(None, description="Detailed explanation or failure message.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional context metadata.")


class SecurityAuditLogger:
    """Singleton security audit logger keeping an in-memory audit stream and file logger."""

    _instance: Optional[SecurityAuditLogger] = None

    def __new__(cls) -> SecurityAuditLogger:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._events: List[SecurityAuditEvent] = []
        return cls._instance

    def log_event(self, event: SecurityAuditEvent) -> None:
        """Record a security audit event."""
        self._events.append(event)
        log_msg = (
            f"[SECURITY AUDIT] [{event.event_type.value}] "
            f"Principal='{event.principal_id}' Roles={event.roles} Tenant='{event.tenant_id}' "
            f"Op='{event.operation}' Resource='{event.resource_id}' Status='{event.status}' "
            f"Reason='{event.reason or 'N/A'}'"
        )
        if event.status in ("DENIED", "FAILED", "TIMEOUT", "INVALID"):
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def log_auth_failure(self, credential_hint: str, reason: str) -> SecurityAuditEvent:
        """Record an authentication failure."""
        event = SecurityAuditEvent(
            event_type=AuditEventTypeEnum.AUTH_FAILURE,
            principal_id="UNAUTHENTICATED",
            username="UNKNOWN",
            roles=[],
            tenant_id="UNKNOWN",
            operation="AUTHENTICATE",
            status="DENIED",
            reason=reason,
            details={"credential_hint": credential_hint[:4] + "***" if credential_hint else "NONE"},
        )
        self.log_event(event)
        return event

    def log_auth_denied(
        self,
        principal: AuthenticatedPrincipal,
        permission: str,
        resource_id: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> SecurityAuditEvent:
        """Record a permission or authorization denial."""
        event = SecurityAuditEvent(
            event_type=AuditEventTypeEnum.AUTHORIZATION_DENIED,
            principal_id=principal.principal_id,
            username=principal.username,
            roles=[r.value for r in principal.roles],
            tenant_id=principal.tenant_id,
            operation=permission,
            resource_id=resource_id,
            status="DENIED",
            reason=reason or f"Missing required permission '{permission}'.",
        )
        self.log_event(event)
        return event

    def get_events(
        self,
        event_type: Optional[AuditEventTypeEnum] = None,
        principal_id: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[SecurityAuditEvent]:
        """Query stored security audit events."""
        res = self._events
        if event_type:
            res = [e for e in res if e.event_type == event_type]
        if principal_id:
            res = [e for e in res if e.principal_id == principal_id]
        if resource_id:
            res = [e for e in res if e.resource_id == resource_id]
        return res

    def clear(self) -> None:
        """Clear audit history (for tests)."""
        self._events.clear()


def get_security_audit_logger() -> SecurityAuditLogger:
    return SecurityAuditLogger()
