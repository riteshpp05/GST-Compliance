"""
tests.unit.test_s24_production_validation
===========================================
Sprint 24 — Unit tests for fail-closed production configuration validation.
"""

import os
import unittest
from unittest.mock import patch

from app.config.production_validator import (
    validate_production_configuration,
    normalize_app_env,
    ConfigurationValidationResult,
)
from app.agent.ai.provider import MockProvider, LLMConfig, create_llm_provider


class TestProductionValidation(unittest.TestCase):
    """Unit tests for app.config.production_validator module."""

    def test_normalize_app_env(self) -> None:
        self.assertEqual(normalize_app_env("production"), "production")
        self.assertEqual(normalize_app_env("PROD"), "production")
        self.assertEqual(normalize_app_env("demo"), "demo")
        self.assertEqual(normalize_app_env("test"), "test")
        self.assertEqual(normalize_app_env("development"), "development")
        self.assertEqual(normalize_app_env("banana"), "banana")

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "development",
            "PERSISTENCE_BACKEND": "sqlite",
            "LLM_PROVIDER": "mock",
        },
        clear=True,
    )
    def test_development_config_valid(self) -> None:
        res = validate_production_configuration()
        self.assertTrue(res.is_valid)
        self.assertEqual(res.canonical_env, "development")
        self.assertEqual(len(res.errors), 0)

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "banana",
        },
        clear=True,
    )
    def test_invalid_app_env_rejected(self) -> None:
        res = validate_production_configuration()
        self.assertFalse(res.is_valid)
        self.assertTrue(any("Invalid APP_ENV" in err for err in res.errors))

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "PERSISTENCE_BACKEND": "sqlite",
            "DATABASE_URL": "",
            "LLM_PROVIDER": "mock",
            "JWT_SECRET_KEY": "default-secret",
        },
        clear=True,
    )
    def test_production_fails_all_unhealthy_defaults(self) -> None:
        res = validate_production_configuration()
        self.assertFalse(res.is_valid)
        self.assertGreaterEqual(len(res.errors), 3)

        # Check error types
        err_text = " ".join(res.errors)
        self.assertIn("PERSISTENCE_BACKEND cannot be 'sqlite'", err_text)
        self.assertIn("PostgreSQL DATABASE_URL is required", err_text)
        self.assertIn("LLM_PROVIDER cannot be 'mock'", err_text)
        self.assertIn("JWT_SECRET_KEY must be set", err_text)

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "PERSISTENCE_BACKEND": "postgresql",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/uc15_prod",
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "sk-proj-prodkey1234567890",
            "JWT_SECRET_KEY": "prod-secure-random-jwt-key-998877",
            "CORS_ORIGINS": "https://gst.enterprise.com",
        },
        clear=True,
    )
    def test_production_valid_configuration(self) -> None:
        res = validate_production_configuration()
        self.assertTrue(res.is_valid)
        self.assertEqual(res.canonical_env, "production")
        self.assertEqual(len(res.errors), 0)
        self.assertTrue(res.checks.get("database_url"))
        self.assertTrue(res.checks.get("jwt_secret_secure"))

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
        },
        clear=True,
    )
    def test_mock_provider_direct_instantiation_raises_in_production(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            MockProvider()
        self.assertIn("Security violation", str(ctx.exception))

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "PERSISTENCE_BACKEND": "postgresql",
            "VCAP_SERVICES": '{"postgresql-db":[{"credentials":{"uri":"postgresql://vcap_user:vcap_pass@postgres.internal:5432/vcap_db"}}]}',
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "sk-proj-prodkey1234567890",
            "JWT_SECRET_KEY": "prod-secure-random-jwt-key-998877",
            "CORS_ORIGINS": "https://gst.enterprise.com",
        },
        clear=True,
    )
    def test_production_valid_with_vcap_services(self) -> None:
        res = validate_production_configuration()
        self.assertTrue(res.is_valid)
        self.assertTrue(res.checks.get("database_url"))

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
        },
        clear=True,
    )
    def test_factory_blocks_mock_llm_in_production(self) -> None:
        cfg = LLMConfig(provider_name="mock")
        provider = create_llm_provider(cfg)
        self.assertFalse(provider.is_available())
        self.assertEqual(provider.__class__.__name__, "DisabledProvider")


if __name__ == "__main__":
    unittest.main()
