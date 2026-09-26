"""
app.security.authorization
==========================
Authorization Service, Permission Evaluation, and Case Access Control for UC15 (Sprint 16).
"""

from typing import Any, Optional

from app.infrastructure.logging import get_logger
from app.security.auth import AuthenticatedPrincipal
from app.security.exceptions import CaseAccessDeniedException, ForbiddenException
from app.security.rbac import HUMAN_ONLY_RESOLUTIONS, PermissionEnum, RoleEnum

logger = get_logger(__name__)


class PermissionEvaluator:
    """Evaluates whether an authenticated principal has permission to perform an action."""

    @staticmethod
    def has_permission(principal: AuthenticatedPrincipal, permission: PermissionEnum) -> bool:
        """Check if principal possesses the required permission."""
        if not principal:
            return False

        # STRICT SERVER-SIDE AI SECURITY BOUNDARY
        if permission in HUMAN_ONLY_RESOLUTIONS:
            if principal.has_role(RoleEnum.AI_AGENT):
                logger.warning(
                    f"AI Security Boundary Violation: Principal '{principal.principal_id}' "
                    f"attempted human-only resolution permission '{permission.value}'."
                )
                return False

        return principal.has_permission(permission)

    @classmethod
    def check_permission(cls, principal: AuthenticatedPrincipal, permission: PermissionEnum) -> None:
        """
        Enforce permission evaluation.
        Raises ForbiddenException if permission is denied.
        """
        if not principal:
            raise ForbiddenException("Unauthenticated access denied.")

        # Explicit check for AI boundary to log and give detailed error message
        if permission in HUMAN_ONLY_RESOLUTIONS and principal.has_role(RoleEnum.AI_AGENT):
            logger.warning(
                f"AI Security Boundary Enforced: AI Agent '{principal.principal_id}' "
                f"blocked from attempting human-only action '{permission.value}'."
            )
            from app.security.audit import get_security_audit_logger
            get_security_audit_logger().log_auth_denied(
                principal=principal,
                permission=permission.value,
                reason="AI Security Boundary Enforcement",
            )
            raise ForbiddenException(
                f"AI Security Boundary Enforcement: AI_AGENT principal '{principal.principal_id}' "
                f"is strictly forbidden from performing human resolution action '{permission.value}'."
            )

        if not cls.has_permission(principal, permission):
            logger.warning(
                f"Authorization Denied: Principal '{principal.principal_id}' "
                f"(roles: {[r.value for r in principal.roles]}) lacks required permission '{permission.value}'."
            )
            from app.security.audit import get_security_audit_logger
            get_security_audit_logger().log_auth_denied(
                principal=principal,
                permission=permission.value,
                reason=f"Missing required permission '{permission.value}'.",
            )
            raise ForbiddenException(
                f"Operation forbidden: Principal '{principal.principal_id}' "
                f"lacks required permission '{permission.value}'."
            )


class CaseAccessControl:
    """Evaluates case-level access control, tenant boundary, assignment, and visibility policies."""

    @staticmethod
    def get_case_tenant_id(case: Any) -> str:
        """Extract tenant_id from a case object (domain model or ORM model or dict)."""
        if hasattr(case, "tenant_id") and getattr(case, "tenant_id", None):
            return str(getattr(case, "tenant_id"))
        if isinstance(case, dict) and "tenant_id" in case:
            return str(case["tenant_id"])
        return "tenant_default"

    @classmethod
    def can_access_case(
        cls,
        principal: AuthenticatedPrincipal,
        case: Any,
        action: Optional[PermissionEnum] = None,
    ) -> bool:
        """
        Evaluates whether principal can access a specific case entity.
        Enforces tenant separation and case assignment policies.
        """
        if not principal:
            return False

        # 1. Tenant Separation Policy
        case_tenant = cls.get_case_tenant_id(case)
        if principal.tenant_id != case_tenant and not principal.has_role(RoleEnum.ADMIN):
            logger.warning(
                f"Cross-Tenant Access Denied: Principal tenant '{principal.tenant_id}' "
                f"cannot access Case tenant '{case_tenant}'."
            )
            return False

        # 2. Action Permission Check if provided
        if action and not PermissionEvaluator.has_permission(principal, action):
            return False

        return True

    @classmethod
    def check_case_access(
        cls,
        principal: AuthenticatedPrincipal,
        case: Any,
        action: Optional[PermissionEnum] = None,
    ) -> None:
        """
        Enforce case-level access control.
        Raises CaseAccessDeniedException or ForbiddenException if access is denied.
        """
        if not principal:
            raise ForbiddenException("Unauthenticated access denied.")

        case_tenant = cls.get_case_tenant_id(case)
        if principal.tenant_id != case_tenant and not principal.has_role(RoleEnum.ADMIN):
            raise CaseAccessDeniedException(
                f"Cross-tenant access denied: Principal tenant '{principal.tenant_id}' "
                f"cannot operate on case belonging to tenant '{case_tenant}'."
            )

        if action:
            PermissionEvaluator.check_permission(principal, action)
