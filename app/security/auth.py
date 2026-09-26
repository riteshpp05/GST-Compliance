"""
app.security.auth
=================
Authentication Service and AuthenticatedPrincipal for UC15 (Sprint 16).
Provides secure API Key and Token authentication without admin fallbacks for HTTP APIs.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

from app.infrastructure.logging import get_logger
from app.security.exceptions import AuthenticationException
from app.security.rbac import PermissionEnum, RoleEnum, ROLE_PERMISSIONS_MATRIX

logger = get_logger(__name__)


class AuthenticatedPrincipal(BaseModel):
    """
    Represents an authenticated user or AI agent principal context.
    Does NOT store raw credentials or secrets.
    """
    principal_id: str = Field(..., description="Unique principal identifier.")
    username: str = Field(..., description="User or agent display name.")
    roles: List[RoleEnum] = Field(default_factory=list, description="Assigned RBAC roles.")
    tenant_id: str = Field("tenant_default", description="Tenant separation identifier.")
    department: Optional[str] = Field(None, description="Department context if applicable.")
    authentication_method: str = Field("API_KEY", description="Authentication mechanism used.")

    def has_role(self, role: Union[RoleEnum, str]) -> bool:
        """Check if principal possesses a specific role."""
        target_role = RoleEnum(role) if isinstance(role, str) else role
        return target_role in self.roles

    def has_permission(self, permission: Union[PermissionEnum, str]) -> bool:
        """Check if principal possesses a permission through any assigned role."""
        target_perm = PermissionEnum(permission) if isinstance(permission, str) else permission
        for role in self.roles:
            role_perms = ROLE_PERMISSIONS_MATRIX.get(role, set())
            if target_perm in role_perms:
                return True
        return False


# Pre-configured Registry of Valid Credentials (In Production, backed by DB/Vault/OAuth)
_REGISTERED_CREDENTIALS: Dict[str, AuthenticatedPrincipal] = {
    # Admin Credentials
    "key-admin-123": AuthenticatedPrincipal(
        principal_id="usr_admin_001",
        username="System Administrator",
        roles=[RoleEnum.ADMIN],
        tenant_id="tenant_default",
        department="IT_SECURITY",
        authentication_method="API_KEY",
    ),
    "token-admin-123": AuthenticatedPrincipal(
        principal_id="usr_admin_001",
        username="System Administrator",
        roles=[RoleEnum.ADMIN],
        tenant_id="tenant_default",
        department="IT_SECURITY",
        authentication_method="TOKEN",
    ),

    # Investigator Credentials
    "key-investigator-123": AuthenticatedPrincipal(
        principal_id="usr_investigator_001",
        username="Lead Investigator Jane",
        roles=[RoleEnum.INVESTIGATOR],
        tenant_id="tenant_default",
        department="TAX_COMPLIANCE",
        authentication_method="API_KEY",
    ),
    "token-investigator-123": AuthenticatedPrincipal(
        principal_id="usr_investigator_001",
        username="Lead Investigator Jane",
        roles=[RoleEnum.INVESTIGATOR],
        tenant_id="tenant_default",
        department="TAX_COMPLIANCE",
        authentication_method="TOKEN",
    ),

    # Tenant B Investigator (for Cross-Tenant Isolation Testing)
    "key-tenant-b-123": AuthenticatedPrincipal(
        principal_id="usr_investigator_tenant_b",
        username="Tenant B Investigator",
        roles=[RoleEnum.INVESTIGATOR],
        tenant_id="tenant_b",
        department="FINANCE_B",
        authentication_method="API_KEY",
    ),
    "token-tenant-b-123": AuthenticatedPrincipal(
        principal_id="usr_investigator_tenant_b",
        username="Tenant B Investigator",
        roles=[RoleEnum.INVESTIGATOR],
        tenant_id="tenant_b",
        department="FINANCE_B",
        authentication_method="TOKEN",
    ),

    # Reviewer Credentials
    "key-reviewer-123": AuthenticatedPrincipal(
        principal_id="usr_reviewer_001",
        username="Senior Tax Reviewer John",
        roles=[RoleEnum.REVIEWER],
        tenant_id="tenant_default",
        department="TAX_AUDIT",
        authentication_method="API_KEY",
    ),
    "token-reviewer-123": AuthenticatedPrincipal(
        principal_id="usr_reviewer_001",
        username="Senior Tax Reviewer John",
        roles=[RoleEnum.REVIEWER],
        tenant_id="tenant_default",
        department="TAX_AUDIT",
        authentication_method="TOKEN",
    ),

    # Analyst Credentials
    "key-analyst-123": AuthenticatedPrincipal(
        principal_id="usr_analyst_001",
        username="Data Analyst Sam",
        roles=[RoleEnum.ANALYST],
        tenant_id="tenant_default",
        department="ANALYTICS",
        authentication_method="API_KEY",
    ),
    "token-analyst-123": AuthenticatedPrincipal(
        principal_id="usr_analyst_001",
        username="Data Analyst Sam",
        roles=[RoleEnum.ANALYST],
        tenant_id="tenant_default",
        department="ANALYTICS",
        authentication_method="TOKEN",
    ),

    # Auditor Credentials
    "key-auditor-123": AuthenticatedPrincipal(
        principal_id="usr_auditor_001",
        username="External Auditor Alice",
        roles=[RoleEnum.AUDITOR],
        tenant_id="tenant_default",
        department="EXTERNAL_AUDIT",
        authentication_method="API_KEY",
    ),
    "token-auditor-123": AuthenticatedPrincipal(
        principal_id="usr_auditor_001",
        username="External Auditor Alice",
        roles=[RoleEnum.AUDITOR],
        tenant_id="tenant_default",
        department="EXTERNAL_AUDIT",
        authentication_method="TOKEN",
    ),

    # AI Agent Credentials (BOUNDED TO AI_AGENT ROLE ONLY)
    "key-ai-agent-123": AuthenticatedPrincipal(
        principal_id="agent_s16_bounded",
        username="UC15 Bounded Investigation AI",
        roles=[RoleEnum.AI_AGENT],
        tenant_id="tenant_default",
        department="AI_AUTONOMOUS",
        authentication_method="API_KEY",
    ),
    "token-ai-agent-123": AuthenticatedPrincipal(
        principal_id="agent_s16_bounded",
        username="UC15 Bounded Investigation AI",
        roles=[RoleEnum.AI_AGENT],
        tenant_id="tenant_default",
        department="AI_AUTONOMOUS",
        authentication_method="TOKEN",
    ),
}


class AuthenticationService:
    """Service providing authentication verification and token/API key lookup."""

    @staticmethod
    def register_principal(secret_key: str, principal: AuthenticatedPrincipal) -> None:
        """Register a principal dynamically (for tests)."""
        _REGISTERED_CREDENTIALS[secret_key] = principal

    @staticmethod
    def authenticate_api_key(api_key: str) -> Optional[AuthenticatedPrincipal]:
        """Authenticate an API Key."""
        if not api_key:
            return None
        return _REGISTERED_CREDENTIALS.get(api_key.strip())

    @staticmethod
    def authenticate_token(token: str) -> Optional[AuthenticatedPrincipal]:
        """Authenticate a Bearer Token."""
        if not token:
            return None
        clean_token = token.replace("Bearer ", "").strip() if token.startswith("Bearer ") else token.strip()
        return _REGISTERED_CREDENTIALS.get(clean_token)

    @classmethod
    def authenticate_headers(
        cls,
        authorization: Optional[str] = None,
        x_api_key: Optional[str] = None,
    ) -> AuthenticatedPrincipal:
        """
        Authenticate HTTP headers.
        Raises AuthenticationException (HTTP 401) if authentication fails.
        """
        principal: Optional[AuthenticatedPrincipal] = None

        if x_api_key:
            principal = cls.authenticate_api_key(x_api_key)
        elif authorization:
            principal = cls.authenticate_token(authorization)

        if not principal:
            logger.warning("HTTP request authentication failed: missing or invalid credentials.")
            raise AuthenticationException("Authentication credentials were not provided or are invalid.")

        return principal


def get_internal_compatibility_principal() -> AuthenticatedPrincipal:
    """
    Fallback context ONLY for non-HTTP internal Python service calls where
    principal was not passed, ensuring 100% backward compatibility for existing unit tests.
    NEVER USED FOR EXTERNAL HTTP/API REQUESTS.
    """
    return AuthenticatedPrincipal(
        principal_id="sys_internal_compatibility",
        username="Internal System Context",
        roles=[RoleEnum.ADMIN],
        tenant_id="tenant_default",
        department="SYSTEM_INTERNAL",
        authentication_method="SYSTEM",
    )
