"""
tests.integration.test_s24_demo_production_isolation
======================================================
Sprint 24 — Integration tests for DEMO vs PRODUCTION runtime isolation.
"""

import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.db.connection import get_database_url, reset_db_connection
from app.infrastructure.health import ApplicationHealthChecker
from ui.app import app


class TestDemoProductionIsolation(unittest.TestCase):
    """Integration tests for environment separation and fail-closed security rules."""

    def setUp(self) -> None:
        reset_db_connection()
        os.environ["APP_ENV"] = "development"

    def tearDown(self) -> None:
        reset_db_connection()
        os.environ["APP_ENV"] = "development"

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "DATABASE_URL": "",
        },
        clear=True,
    )
    def test_production_sqlite_fallback_raises_runtime_error(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            get_database_url()
        self.assertIn("SQLite fallback is strictly forbidden", str(ctx.exception))

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "demo",
        },
        clear=True,
    )
    def test_health_and_readiness_endpoints_demo_mode(self) -> None:
        client = TestClient(app)

        resp_health = client.get("/health")
        self.assertEqual(resp_health.status_code, 200)
        data_h = resp_health.json()
        self.assertEqual(data_h["status"], "UP")
        self.assertEqual(data_h["environment"], "demo")

        resp_ready = client.get("/ready")
        self.assertEqual(resp_ready.status_code, 200)
        data_r = resp_ready.json()
        self.assertEqual(data_r["status"], "READY")
        self.assertTrue(data_r["ready"])

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
            "PERSISTENCE_BACKEND": "sqlite",
            "DATABASE_URL": "",
        },
        clear=True,
    )
    def test_readiness_returns_503_in_invalid_production_config(self) -> None:
        client = TestClient(app)
        resp_ready = client.get("/ready")
        self.assertEqual(resp_ready.status_code, 503)
        data = resp_ready.json()["detail"]
        self.assertEqual(data["status"], "NOT_READY")
        self.assertFalse(data["ready"])
        self.assertEqual(data["details"]["configuration"]["status"], "FAIL")

    @patch.dict(
        os.environ,
        {
            "APP_ENV": "production",
        },
        clear=True,
    )
    def test_production_sanitized_500_response(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)

        # Trigger unhandled exception handler on route
        @app.get("/api/test-error")
        def route_with_error():
            raise ValueError("Secret database password trace!")

        resp = client.get("/api/test-error")
        self.assertEqual(resp.status_code, 500)
        body = resp.json()
        self.assertEqual(body["detail"], "An internal server error occurred.")
        self.assertEqual(body["code"], "INTERNAL_SERVER_ERROR")
        self.assertIn("correlation_id", body)
        self.assertNotIn("Secret database password trace!", str(body))


if __name__ == "__main__":
    unittest.main()
