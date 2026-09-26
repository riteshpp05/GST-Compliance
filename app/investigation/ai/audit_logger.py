"""
UC15 GST Compliance Agent — AI Audit Logger & RBAC Guardrails (Sprint 23)
Logs structured AI investigation events for auditability without logging sensitive secrets.
Enforces security boundaries preventing AI from executing human-only case state transitions.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.infrastructure.logging import get_logger
from app.security import AuthenticatedPrincipal, CaseAccessControl, ForbiddenException

logger = get_logger(__name__)


@dataclass
class AIAuditEvent:
    event_id: str
    case_id: str
    request_id: str
    principal_id: str
    principal_role: str
    provider_name: str
    model_id: str
    prompt_version: str
    context_schema_version: str
    input_source_ids: List[str] = field(default_factory=list)
    output_status: str = "VALID"
    validation_errors: List[str] = field(default_factory=list)
    rejected_claims_count: int = 0
    latency_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "case_id": self.case_id,
            "request_id": self.request_id,
            "principal_id": self.principal_id,
            "principal_role": self.principal_role,
            "provider_name": self.provider_name,
            "model_id": self.model_id,
            "prompt_version": self.prompt_version,
            "context_schema_version": self.context_schema_version,
            "input_source_ids": self.input_source_ids,
            "output_status": self.output_status,
            "validation_errors": self.validation_errors,
            "rejected_claims_count": self.rejected_claims_count,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }


class AIAuditLogger:
    """
    Audit logging service recording structured AI investigation activity.
    Also provides RBAC verification blocking AI principal from human-only case decisions.
    """

    def __init__(self) -> None:
        self._audit_logs: List[AIAuditEvent] = []

    def log_event(self, event: AIAuditEvent) -> None:
        # Guarantee zero API keys or secrets in logged payload
        ev_dict = event.to_dict()
        self._audit_logs.append(event)
        logger.info(
            f"[AI AUDIT LOG] Case='{event.case_id}' Provider='{event.provider_name}' Model='{event.model_id}' "
            f"Status='{event.output_status}' Sources={len(event.input_source_ids)} Latency={event.latency_ms}ms"
        )

    def verify_case_action_rbac(
        self,
        action: str,
        principal: AuthenticatedPrincipal,
    ) -> None:
        """
        Verify that principal is allowed to perform case action.
        Prevents AI_AGENT principal or unprivileged roles from executing human-only case transitions.
        """
        HUMAN_ONLY_ACTIONS = {
            "RESOLVE_CASE",
            "CLOSE_CASE",
            "APPROVE_CASE",
            "REJECT_INVOICE",
            "OVERRIDE_STATUTORY_RULE",
        }

        p_id = getattr(principal, "principal_id", "") or getattr(principal, "user_id", "")
        roles = set(getattr(principal, "roles", []))

        if action in HUMAN_ONLY_ACTIONS:
            if "AI_AGENT" in roles or p_id == "sys_ai_agent":
                raise ForbiddenException(
                    f"Security RBAC violation: AI agent principal '{p_id}' cannot execute human-only action '{action}'."
                )
            if not (roles.intersection({"ADMIN", "REVIEWER", "TAX_OFFICER", "FINANCE_REVIEWER"})):
                raise ForbiddenException(
                    f"Security RBAC violation: Principal '{p_id}' with roles {roles} lacks permission for action '{action}'."
                )

    def get_logs_for_case(self, case_id: str) -> List[AIAuditEvent]:
        return [e for e in self._audit_logs if e.case_id == case_id]

    def list_all_logs(self) -> List[AIAuditEvent]:
        return list(self._audit_logs)
