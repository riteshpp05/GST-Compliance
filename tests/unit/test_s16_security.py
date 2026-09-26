"""
tests.unit.test_s16_security
=============================
Sprint 16 Unit Test Suite: Authentication, RBAC, Case Authorization, & Hard AI Security Boundary.
"""

import unittest
from app.case import CaseDecisionEnum, CaseService, InMemoryCaseRepository
from app.security import (
    AuditEventTypeEnum,
    AuthenticatedPrincipal,
    AuthenticationException,
    AuthenticationService,
    CaseAccessControl,
    CaseAccessDeniedException,
    ForbiddenException,
    PermissionEnum,
    PermissionEvaluator,
    RoleEnum,
    get_security_audit_logger,
)


class TestAuthenticationAndRBAC(unittest.TestCase):
    """Test suite for authentication mechanisms and RBAC permissions."""

    def test_valid_api_key_authentication(self):
        principal = AuthenticationService.authenticate_api_key("key-investigator-123")
        self.assertIsNotNone(principal)
        self.assertEqual(principal.principal_id, "usr_investigator_001")
        self.assertIn(RoleEnum.INVESTIGATOR, principal.roles)
        self.assertEqual(principal.tenant_id, "tenant_default")

    def test_valid_token_authentication(self):
        principal = AuthenticationService.authenticate_token("Bearer token-admin-123")
        self.assertIsNotNone(principal)
        self.assertEqual(principal.principal_id, "usr_admin_001")
        self.assertIn(RoleEnum.ADMIN, principal.roles)

    def test_invalid_credentials_rejected(self):
        self.assertIsNone(AuthenticationService.authenticate_api_key("invalid-key-999"))
        self.assertIsNone(AuthenticationService.authenticate_token("Bearer invalid-token-999"))

        with self.assertRaises(AuthenticationException):
            AuthenticationService.authenticate_headers(authorization="Bearer invalid-token-999")

    def test_rbac_permission_matrix(self):
        admin = AuthenticationService.authenticate_api_key("key-admin-123")
        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")
        reviewer = AuthenticationService.authenticate_api_key("key-reviewer-123")
        auditor = AuthenticationService.authenticate_api_key("key-auditor-123")

        self.assertTrue(PermissionEvaluator.has_permission(admin, PermissionEnum.APPROVE_CASE))
        self.assertTrue(PermissionEvaluator.has_permission(reviewer, PermissionEnum.APPROVE_CASE))
        self.assertFalse(PermissionEvaluator.has_permission(investigator, PermissionEnum.APPROVE_CASE))
        self.assertFalse(PermissionEvaluator.has_permission(auditor, PermissionEnum.CASE_CREATE))


class TestAISecurityBoundary(unittest.TestCase):
    """Test suite ensuring AI_AGENT is strictly forbidden from human resolution operations."""

    def test_ai_agent_lacks_human_resolution_permissions(self):
        ai_principal = AuthenticationService.authenticate_api_key("key-ai-agent-123")
        self.assertIsNotNone(ai_principal)
        self.assertIn(RoleEnum.AI_AGENT, ai_principal.roles)

        # Explicit check that AI lacks all 4 human-only permissions
        self.assertFalse(PermissionEvaluator.has_permission(ai_principal, PermissionEnum.APPROVE_CASE))
        self.assertFalse(PermissionEvaluator.has_permission(ai_principal, PermissionEnum.REJECT_CASE))
        self.assertFalse(PermissionEvaluator.has_permission(ai_principal, PermissionEnum.RESOLVE_CASE))
        self.assertFalse(PermissionEvaluator.has_permission(ai_principal, PermissionEnum.CLOSE_CASE))

    def test_ai_agent_blocked_from_submitting_approval(self):
        audit_logger = get_security_audit_logger()
        audit_logger.clear()

        ai_principal = AuthenticationService.authenticate_api_key("key-ai-agent-123")
        service = CaseService(repository=InMemoryCaseRepository())

        # Create case as investigator
        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")
        case = service.create_case(title="AI Boundary Test Case", principal=investigator)

        # AI Agent attempts approval -> MUST FAIL WITH ForbiddenException
        with self.assertRaises(ForbiddenException) as cm:
            service.submit_human_review(
                case_id=case.case_id,
                reviewer="AI_AGENT",
                decision=CaseDecisionEnum.APPROVE,
                comment="AI attempting automated approval",
                principal=ai_principal,
            )

        err_msg = str(cm.exception)
        self.assertTrue("AI_AGENT" in err_msg or "forbidden" in err_msg.lower())

        # Verify security audit event was logged
        events = audit_logger.get_events(event_type=AuditEventTypeEnum.AUTHORIZATION_DENIED)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[-1].principal_id, "agent_s16_bounded")

    def test_ai_agent_blocked_from_resolve_and_close(self):
        ai_principal = AuthenticationService.authenticate_api_key("key-ai-agent-123")
        service = CaseService(repository=InMemoryCaseRepository())
        investigator = AuthenticationService.authenticate_api_key("key-investigator-123")
        case = service.create_case(title="AI Resolve Test Case", principal=investigator)

        with self.assertRaises(ForbiddenException):
            service.resolve_case(case_id=case.case_id, principal=ai_principal)

        with self.assertRaises(ForbiddenException):
            service.close_case(case_id=case.case_id, principal=ai_principal)


class TestMultiTenantCaseAuthorization(unittest.TestCase):
    """Test suite verifying cross-tenant case isolation and case access control."""

    def test_same_tenant_access_allowed(self):
        tenant_a_inv = AuthenticationService.authenticate_api_key("key-investigator-123")
        service = CaseService(repository=InMemoryCaseRepository())

        case = service.create_case(title="Tenant A Case", principal=tenant_a_inv)
        retrieved = service.get_case(case.case_id, principal=tenant_a_inv)

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.case_id, case.case_id)

    def test_cross_tenant_access_denied(self):
        tenant_a_inv = AuthenticationService.authenticate_api_key("key-investigator-123")
        tenant_b_inv = AuthenticationService.authenticate_api_key("key-tenant-b-123")

        service = CaseService(repository=InMemoryCaseRepository())
        case_a = service.create_case(title="Tenant A Private Case", principal=tenant_a_inv)

        # Tenant B attempts to read Tenant A case -> raises CaseAccessDeniedException
        with self.assertRaises(CaseAccessDeniedException):
            service.get_case(case_a.case_id, principal=tenant_b_inv)

        # Tenant B attempts write operation on Tenant A case -> raises CaseAccessDeniedException
        with self.assertRaises(CaseAccessDeniedException):
            service.triage_case(case_id=case_a.case_id, priority="P1", principal=tenant_b_inv)

    def test_admin_cross_tenant_access_allowed(self):
        tenant_a_inv = AuthenticationService.authenticate_api_key("key-investigator-123")
        admin = AuthenticationService.authenticate_api_key("key-admin-123")

        service = CaseService(repository=InMemoryCaseRepository())
        case_a = service.create_case(title="Tenant A Case", principal=tenant_a_inv)

        retrieved = service.get_case(case_a.case_id, principal=admin)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.case_id, case_a.case_id)
