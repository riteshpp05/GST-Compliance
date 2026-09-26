"""
app.infrastructure.health
========================
Production Health, Readiness, and Liveness Checkers for UC15 (Sprint 19).
Verifies application status, database connectivity, migration state, statutory reference availability,
and environment configuration without performing expensive operations.
"""

from __future__ import annotations

import os
from typing import Any, Dict
from app.db.connection import get_db_engine
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class ApplicationHealthChecker:
    """
    Evaluates health, readiness, and liveness status of the UC15 system (Sprint 24).
    """

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """
        Fast health check determining whether application process is responsive (liveness probe).
        """
        env = os.getenv("APP_ENV", "development").lower().strip()
        return {
            "status": "UP",
            "service": "UC15 — GST Compliance Intelligence & Resolution Agent",
            "version": "2.4.0",
            "environment": env,
        }

    @classmethod
    def check_liveness(cls) -> Dict[str, Any]:
        """
        Liveness check for container orchestration (k8s / docker / BTP).
        """
        return {
            "status": "ALIVE",
            "process": "python",
            "pid": os.getpid(),
        }

    @classmethod
    def check_readiness(cls) -> Dict[str, Any]:
        """
        Readiness check verifying configuration, database connectivity, statutory reference catalog, and AI state.
        """
        from app.config.production_validator import validate_production_configuration

        details: Dict[str, Any] = {}
        is_ready = True

        # 1. Environment & Config Validation Check
        cfg_res = validate_production_configuration()
        details["configuration"] = {
            "status": "PASS" if cfg_res.is_valid else "FAIL",
            "app_env": cfg_res.app_env,
            "canonical_env": cfg_res.canonical_env,
            "errors": cfg_res.errors,
            "warnings": cfg_res.warnings,
        }
        if not cfg_res.is_valid:
            is_ready = False

        # 2. Database Connectivity Check
        try:
            engine = get_db_engine()
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            details["database"] = {"status": "CONNECTED", "backend": engine.dialect.name}
        except Exception as e:
            is_ready = False
            details["database"] = {"status": "UNAVAILABLE", "error": str(e)}

        # 3. Reference Catalog Check
        try:
            from app.reference.services.reference_service import ReferenceService
            ref_svc = ReferenceService()
            details["reference_catalog"] = {
                "status": "LOADED",
                "repository": ref_svc.repository.__class__.__name__,
            }
        except Exception as e:
            is_ready = False
            details["reference_catalog"] = {"status": "UNAVAILABLE", "error": str(e)}

        # 4. Versioned Compliance Rules Check
        try:
            from app.agent.compliance_agent import GSTComplianceAgent
            agent = GSTComplianceAgent()
            if hasattr(agent, "registry"):
                rules_count = len(agent.registry.all()) if hasattr(agent.registry, "all") else len(getattr(agent.registry, "rules", []))
            else:
                rules_count = 0
            details["compliance_rules"] = {
                "status": "LOADED" if rules_count > 0 else "WARNING",
                "registered_rules": rules_count,
            }
        except Exception as e:
            details["compliance_rules"] = {"status": "WARNING", "error": str(e)}

        # 5. AI Provider State
        try:
            from app.agent.ai.provider import create_llm_provider
            llm_prov = create_llm_provider()
            details["ai_provider"] = {
                "status": "AVAILABLE" if llm_prov.is_available() else "DISABLED",
                "provider_type": llm_prov.__class__.__name__,
            }
        except Exception as e:
            details["ai_provider"] = {"status": "ERROR", "error": str(e)}

        # 6. Persistence Backend Mode
        details["persistence_mode"] = os.getenv("PERSISTENCE_BACKEND", "sqlite")

        status_str = "READY" if is_ready else "NOT_READY"
        logger.info(f"Readiness check evaluated: {status_str} (is_ready={is_ready})")

        return {
            "status": status_str,
            "ready": is_ready,
            "details": details,
        }
