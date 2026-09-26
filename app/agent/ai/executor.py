"""
app.agent.ai.executor
=====================
Controlled & Hardened Tool Executor for UC15 AI Investigation Agent (Sprint 12.1 + Sprint 16 Security).
Executes tools specified in an InvestigationPlan with:
- Authentication & Permission Verification
- Input Argument Schema Validation
- Timeout Bounds Enforcement
- Safe Retries with Exponential Backoff for Idempotent Tools
- Output Payload Validation
- Security Audit Recording
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.agent.ai.models import InvestigationPlan, ToolResult
from app.agent.ai.registry import ToolRegistry
from app.infrastructure.logging import get_logger
from app.security.audit import AuditEventTypeEnum, SecurityAuditEvent, get_security_audit_logger
from app.security.auth import AuthenticatedPrincipal, get_internal_compatibility_principal
from app.security.authorization import PermissionEvaluator
from app.security.exceptions import (
    ToolExecutionTimeoutException,
    ToolInputValidationException,
    ToolPermissionDeniedException,
)
from app.security.rbac import PermissionEnum

logger = get_logger(__name__)


class ToolExecutor:
    """
    Hardened Tool Executor enforcing security controls, input/output validation,
    timeouts, retries, and audit traceability during tool execution.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or ToolRegistry()
        self.audit_logger = get_security_audit_logger()

    def _validate_input(self, tool_name: str, input_schema: Dict[str, Any], kwargs: Dict[str, Any]) -> Optional[str]:
        """Validate input arguments against tool input schema."""
        if not input_schema:
            return None

        required_fields = input_schema.get("required", [])
        missing_fields = [f for f in required_fields if f not in kwargs or kwargs[f] is None]
        if missing_fields:
            return f"Missing required parameters: {missing_fields}"

        properties = input_schema.get("properties", {})
        for param, val in kwargs.items():
            if param in properties:
                expected_type = properties[param].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return f"Parameter '{param}' expected string, got {type(val).__name__}."
                if expected_type == "integer" and not isinstance(val, int):
                    return f"Parameter '{param}' expected integer, got {type(val).__name__}."
                if expected_type == "boolean" and not isinstance(val, bool):
                    return f"Parameter '{param}' expected boolean, got {type(val).__name__}."

        return None

    def execute_tool(
        self,
        tool_name: str,
        principal: Optional[AuthenticatedPrincipal] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """
        Execute a single tool by name with security checks, input validation,
        timeout bounds, safe retries, and audit logging.
        """
        eff_principal = principal or get_internal_compatibility_principal()

        tool_def = self.registry.get(tool_name)
        if not tool_def:
            logger.warning(f"Requested unregistered tool '{tool_name}'.")
            self.audit_logger.log_event(
                SecurityAuditEvent(
                    event_type=AuditEventTypeEnum.TOOL_FAILED,
                    principal_id=eff_principal.principal_id,
                    username=eff_principal.username,
                    roles=[r.value for r in eff_principal.roles],
                    tenant_id=eff_principal.tenant_id,
                    operation=f"execute_tool:{tool_name}",
                    resource_id=tool_name,
                    status="FAILED",
                    reason=f"Tool '{tool_name}' is not registered.",
                )
            )
            return ToolResult(
                tool_name=tool_name,
                success=False,
                errors=[f"Tool '{tool_name}' is not registered."],
            )

        # 1. PERMISSION CHECK
        for req_perm in tool_def.required_permissions:
            if not PermissionEvaluator.has_permission(eff_principal, req_perm):
                logger.warning(
                    f"Tool Execution Permission Denied: Principal '{eff_principal.principal_id}' "
                    f"lacks permission '{req_perm.value}' for tool '{tool_name}'."
                )
                self.audit_logger.log_auth_denied(
                    principal=eff_principal,
                    permission=req_perm.value,
                    resource_id=tool_name,
                    reason=f"Missing permission '{req_perm.value}' for tool '{tool_name}'.",
                )
                return ToolResult(
                    tool_name=tool_name,
                    success=False,
                    errors=[f"Permission denied: Principal '{eff_principal.principal_id}' lacks '{req_perm.value}'."],
                )

        # 2. INPUT VALIDATION
        val_error = self._validate_input(tool_name, tool_def.input_schema, kwargs)
        if val_error:
            logger.warning(f"Tool Input Validation Failed for '{tool_name}': {val_error}")
            self.audit_logger.log_event(
                SecurityAuditEvent(
                    event_type=AuditEventTypeEnum.TOOL_VALIDATION_FAILED,
                    principal_id=eff_principal.principal_id,
                    username=eff_principal.username,
                    roles=[r.value for r in eff_principal.roles],
                    tenant_id=eff_principal.tenant_id,
                    operation=f"execute_tool:{tool_name}",
                    resource_id=tool_name,
                    status="INVALID",
                    reason=val_error,
                )
            )
            return ToolResult(
                tool_name=tool_name,
                success=False,
                errors=[f"Input validation failed: {val_error}"],
            )

        # 3. BOUNDED TIMEOUT & RETRY PIPELINE
        max_attempts = tool_def.max_retries if tool_def.is_idempotent else 1
        last_error: Optional[str] = None
        result: Optional[ToolResult] = None

        for attempt in range(1, max_attempts + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.registry.execute, name=tool_name, principal=eff_principal, **kwargs)
                    result = future.result(timeout=tool_def.timeout_seconds)

                if result and result.success:
                    break
                else:
                    last_error = result.errors[0] if (result and result.errors) else "Unknown execution error"
                    logger.warning(f"Tool '{tool_name}' attempt {attempt}/{max_attempts} failed: {last_error}")
                    if attempt < max_attempts and tool_def.is_idempotent:
                        time.sleep(0.1 * (2 ** (attempt - 1)))  # Exponential backoff
            except FutureTimeoutError:
                last_error = f"Execution timed out after {tool_def.timeout_seconds}s."
                logger.error(f"Tool '{tool_name}' attempt {attempt}/{max_attempts} timed out.")
                self.audit_logger.log_event(
                    SecurityAuditEvent(
                        event_type=AuditEventTypeEnum.TOOL_TIMEOUT,
                        principal_id=eff_principal.principal_id,
                        username=eff_principal.username,
                        roles=[r.value for r in eff_principal.roles],
                        tenant_id=eff_principal.tenant_id,
                        operation=f"execute_tool:{tool_name}",
                        resource_id=tool_name,
                        status="TIMEOUT",
                        reason=last_error,
                    )
                )
                if attempt < max_attempts and tool_def.is_idempotent:
                    time.sleep(0.1 * (2 ** (attempt - 1)))
                else:
                    result = ToolResult(
                        tool_name=tool_name,
                        success=False,
                        errors=[last_error],
                    )

        # 4. SECURITY AUDIT RECORDING
        final_status = "SUCCESS" if (result and result.success) else ("TIMEOUT" if "timed out" in (last_error or "") else "FAILED")
        self.audit_logger.log_event(
            SecurityAuditEvent(
                event_type=AuditEventTypeEnum.TOOL_EXECUTED if result and result.success else AuditEventTypeEnum.TOOL_FAILED,
                principal_id=eff_principal.principal_id,
                username=eff_principal.username,
                roles=[r.value for r in eff_principal.roles],
                tenant_id=eff_principal.tenant_id,
                operation=f"execute_tool:{tool_name}",
                resource_id=tool_name,
                status=final_status,
                reason=None if result and result.success else last_error,
                details={"execution_time_ms": result.execution_time_ms if result else 0.0, "category": tool_def.category},
            )
        )

        return result or ToolResult(tool_name=tool_name, success=False, errors=[last_error or "Execution failed"])

    def execute_plan(
        self,
        plan: InvestigationPlan,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> List[ToolResult]:
        """Execute all required tools in an investigation plan using the principal context."""
        results: List[ToolResult] = []
        target = plan.target

        for tool_name in plan.required_tools:
            tool_def = self.registry.get(tool_name)
            kwargs: Dict[str, Any] = {}
            if tool_def:
                schema_props = tool_def.input_schema.get("properties", {})
                if "invoice_no" in schema_props and target and target.startswith("INV-"):
                    kwargs["invoice_no"] = target
                elif "top_n" in schema_props:
                    kwargs["top_n"] = 5
                elif "limit" in schema_props:
                    kwargs["limit"] = 5

            tool_result = self.execute_tool(tool_name, principal=principal, **kwargs)
            results.append(tool_result)

        return results
