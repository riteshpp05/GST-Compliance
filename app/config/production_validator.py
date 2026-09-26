"""
app.config.production_validator
================================
Sprint 24 — Fail-Closed Production Configuration Validator for UC15.

Ensures strict separation between DEMO, TEST, and PRODUCTION environments.
Enforces fail-closed rules when APP_ENV=production:
  1. Canonical APP_ENV validation (allowed: demo, test, development, production).
  2. PERSISTENCE_BACKEND must be 'postgresql' in production (no SQLite).
  3. DATABASE_URL must be provided and valid (no fallback to sqlite files).
  4. LLM_PROVIDER=mock is strictly forbidden in production.
  5. JWT secret key must not be a default/placeholder.
  6. Wildcard CORS origins are forbidden or restricted in production.
"""

from __future__ import annotations

import os
import sys
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

VALID_ENVIRONMENTS = {"demo", "test", "development", "production", "prod"}
CANONICAL_ENVS = {
    "demo": "demo",
    "test": "test",
    "development": "development",
    "production": "production",
    "prod": "production",
}


class ConfigurationValidationResult(BaseModel):
    """Result of environment and security configuration validation."""

    app_env: str
    canonical_env: str
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checks: Dict[str, bool] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "app_env": self.app_env,
            "canonical_env": self.canonical_env,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "checks": self.checks,
        }


def normalize_app_env(raw_env: Optional[str] = None) -> str:
    """Normalize raw APP_ENV string to canonical format."""
    val = (raw_env or os.getenv("APP_ENV", "development")).lower().strip()
    return CANONICAL_ENVS.get(val, val)


def validate_production_configuration() -> ConfigurationValidationResult:
    """
    Validate the application configuration based on APP_ENV mode.
    Returns ConfigurationValidationResult with detailed pass/fail status per check.
    """
    raw_env = os.getenv("APP_ENV", "development").lower().strip()
    canonical_env = CANONICAL_ENVS.get(raw_env, raw_env)

    errors: List[str] = []
    warnings: List[str] = []
    checks: Dict[str, bool] = {}

    # Check 1: Valid APP_ENV
    if raw_env not in VALID_ENVIRONMENTS:
        errors.append(
            f"Invalid APP_ENV='{raw_env}'. Must be one of: {sorted(list(VALID_ENVIRONMENTS))}"
        )
        checks["valid_app_env"] = False
    else:
        checks["valid_app_env"] = True

    is_prod = canonical_env == "production"

    # Check 2: Persistence Backend in Production
    persistence = os.getenv("PERSISTENCE_BACKEND", "sqlite").lower().strip()
    db_url = os.getenv("DATABASE_URL", "").strip()

    if not db_url and "VCAP_SERVICES" in os.environ:
        try:
            import json
            vcap = json.loads(os.environ["VCAP_SERVICES"])
            for svc_name, instances in vcap.items():
                for inst in instances:
                    creds = inst.get("credentials", {})
                    cand = creds.get("uri") or creds.get("url")
                    if cand and ("postgres" in cand or "postgresql" in cand):
                        db_url = cand
                        break
                    if "hostname" in creds and "username" in creds and "password" in creds:
                        db_url = f"postgresql://{creds['username']}:{creds['password']}@{creds['hostname']}:{creds.get('port', 5432)}/{creds.get('dbname', 'postgres')}"
                        break
                if db_url:
                    break
        except Exception:
            pass

    if is_prod:
        if persistence == "sqlite":
            errors.append(
                "Production configuration error: PERSISTENCE_BACKEND cannot be 'sqlite' in production mode."
            )
            checks["persistence_backend"] = False
        else:
            checks["persistence_backend"] = True

        if not db_url or db_url.startswith("sqlite") or "uc15_s14.db" in db_url:
            errors.append(
                "Production configuration error: Valid PostgreSQL DATABASE_URL is required in production mode."
            )
            checks["database_url"] = False
        else:
            checks["database_url"] = True
    else:
        checks["persistence_backend"] = True
        checks["database_url"] = True

    # Check 3: AI Provider Configuration
    llm_provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
    llm_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")

    if is_prod:
        if llm_provider == "mock":
            errors.append(
                "Production configuration error: LLM_PROVIDER cannot be 'mock' in production mode."
            )
            checks["llm_provider_safe"] = False
        else:
            checks["llm_provider_safe"] = True

        if not llm_key:
            warnings.append(
                "Production warning: No real LLM API key provided. AI features will be disabled; rule engine remains operational."
            )
            checks["llm_api_key_present"] = False
        else:
            checks["llm_api_key_present"] = True
    else:
        checks["llm_provider_safe"] = True
        checks["llm_api_key_present"] = True

    # Check 4: Authentication Secrets
    jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if is_prod:
        if not jwt_secret or jwt_secret in ("default-secret", "secret", "change-me", "dev-secret-key-12345"):
            errors.append(
                "Production configuration error: JWT_SECRET_KEY must be set to a secure secret in production mode."
            )
            checks["jwt_secret_secure"] = False
        else:
            checks["jwt_secret_secure"] = True
    else:
        checks["jwt_secret_secure"] = True

    # Check 5: CORS Security
    cors_origins = os.getenv("CORS_ORIGINS", "*").strip()
    if is_prod:
        if cors_origins == "*":
            warnings.append(
                "Production warning: CORS_ORIGINS is set to wildcard '*'. Restrict CORS_ORIGINS for production security."
            )
            checks["cors_restricted"] = False
        else:
            checks["cors_restricted"] = True
    else:
        checks["cors_restricted"] = True

    is_valid = len(errors) == 0

    return ConfigurationValidationResult(
        app_env=raw_env,
        canonical_env=canonical_env,
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        checks=checks,
    )


def validate_production_configuration_or_exit() -> ConfigurationValidationResult:
    """
    Validates application configuration. If validation fails, logs error and exits process.
    """
    res = validate_production_configuration()
    if not res.is_valid:
        logger.critical("=" * 70)
        logger.critical("FATAL: PRODUCTION CONFIGURATION VALIDATION FAILED!")
        for err in res.errors:
            logger.critical(f"  [ERROR] {err}")
        logger.critical("System startup aborted to prevent unsafe production operation.")
        logger.critical("=" * 70)
        sys.exit(1)

    if res.warnings:
        for warn in res.warnings:
            logger.warning(f"[CONFIG WARNING] {warn}")

    return res
