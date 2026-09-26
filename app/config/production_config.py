"""
app.config.production_config
============================
Production Configuration & Hardening Manager for UC15 (Sprint 19).
Manages environment-based settings, database connection pool parameters, secret validation,
CORS security, request payload limits, and input protection helpers.
"""

from __future__ import annotations

import os
import re
from typing import List
from pydantic import BaseModel, Field
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ProductionSecurityConfig(BaseModel):
    """Production configuration and security hardening settings."""
    environment: str = Field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    persistence_backend: str = Field(default_factory=lambda: os.getenv("PERSISTENCE_BACKEND", "sqlite"))
    database_url: str = Field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./app_data.db"))
    
    # DB Pool Parameters
    db_pool_size: int = Field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "10")))
    db_max_overflow: int = Field(default_factory=lambda: int(os.getenv("DB_MAX_OVERFLOW", "20")))
    db_pool_timeout: int = Field(default_factory=lambda: int(os.getenv("DB_POOL_TIMEOUT", "30")))
    db_pool_recycle: int = Field(default_factory=lambda: int(os.getenv("DB_POOL_RECYCLE", "1800")))

    # Security & CORS Parameters
    allowed_cors_origins: List[str] = Field(
        default_factory=lambda: os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000").split(",")
    )
    max_request_payload_bytes: int = Field(10 * 1024 * 1024, description="Maximum HTTP payload size (10MB).")
    enable_rate_limiting: bool = Field(True, description="Enable request rate limiting heuristics.")

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def validate_production_readiness(self) -> List[str]:
        """Validate production configuration and return list of hardening warnings."""
        warnings: List[str] = []

        if self.is_production:
            if "sqlite" in self.database_url.lower():
                warnings.append("Production environment using SQLite database instead of PostgreSQL.")
            if "*" in self.allowed_cors_origins:
                warnings.append("Production CORS policy contains permissive wildcard '*'.")
            if os.getenv("SECRET_KEY", "default-key") == "default-key":
                warnings.append("Production SECRET_KEY environment variable is missing or default.")

        return warnings


_CONFIG_INSTANCE: Optional[ProductionSecurityConfig] = None


def get_production_config() -> ProductionSecurityConfig:
    """Get active ProductionSecurityConfig instance."""
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = ProductionSecurityConfig()
    return _CONFIG_INSTANCE


class InputSanitizer:
    """
    Input protection utility validating external strings against path traversal, SQL injection, and XSS.
    """

    PATH_TRAVERSAL_REGEX = re.compile(r"(\.\./|\.\.\\|/etc/|/var/|C:\\Windows)", re.IGNORECASE)
    SQL_INJECTION_REGEX = re.compile(r"(\bUNION\b|\bSELECT\b.*\bFROM\b|\bDROP\b\s+\bTABLE\b|\bTRUNCATE\b)", re.IGNORECASE)
    XSS_REGEX = re.compile(r"(<script.*?>|javascript:|onload=)", re.IGNORECASE)

    @classmethod
    def sanitize_string(cls, val: str) -> str:
        """Sanitize raw input string."""
        if not val:
            return val

        if cls.PATH_TRAVERSAL_REGEX.search(val):
            logger.warning(f"Sanitizer detected potential path traversal attempt: '{val[:50]}'")
            raise ValueError("Invalid input: Path traversal pattern detected.")

        if cls.SQL_INJECTION_REGEX.search(val):
            logger.warning(f"Sanitizer detected potential SQL injection attempt: '{val[:50]}'")
            raise ValueError("Invalid input: Malformed SQL injection pattern detected.")

        if cls.XSS_REGEX.search(val):
            logger.warning(f"Sanitizer detected potential XSS script pattern: '{val[:50]}'")
            val = cls.XSS_REGEX.sub("", val)

        return val.strip()
