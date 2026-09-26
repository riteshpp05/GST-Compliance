"""
UC15 GST Compliance Agent — Sprint 23 Provider & Resilience Unit Tests
Verifies provider failure handling, fallback execution, and explicit mock/real separation.
"""
import os
import unittest

from app.agent.ai.provider import (
    DisabledProvider,
    LLMConfig,
    MockProvider,
    create_llm_provider,
    LLMProviderUnavailableError,
)
from app.investigation.ai.audit_logger import AIAuditLogger, AIAuditEvent
from app.security import AuthenticatedPrincipal, ForbiddenException


class TestS23AIProviderAndResilience(unittest.TestCase):

    def setUp(self):
        self.audit_logger = AIAuditLogger()

    def test_disabled_provider_raises_unavailable(self):
        provider = DisabledProvider()
        self.assertFalse(provider.is_available())
        with self.assertRaises(LLMProviderUnavailableError):
            provider.generate("Test prompt")

    def test_mock_provider_explicit_isolation(self):
        cfg = LLMConfig(provider_name="mock")
        provider = create_llm_provider(cfg)
        self.assertIsInstance(provider, MockProvider)
        self.assertTrue(provider.is_available())

    def test_production_mode_blocks_mock_provider(self):
        os.environ["APP_ENV"] = "production"
        try:
            cfg = LLMConfig(provider_name="mock")
            provider = create_llm_provider(cfg)
            self.assertIsInstance(provider, DisabledProvider)
            self.assertFalse(provider.is_available())
        finally:
            os.environ["APP_ENV"] = "development"

    def test_audit_logger_rbac_prevents_ai_human_decisions(self):
        ai_principal = AuthenticatedPrincipal(
            principal_id="sys_ai_agent",
            user_id="sys_ai_agent",
            username="sys_ai_agent",
            roles=["AI_AGENT"],
        )
        with self.assertRaises(ForbiddenException):
            self.audit_logger.verify_case_action_rbac("RESOLVE_CASE", ai_principal)


if __name__ == "__main__":
    unittest.main()
