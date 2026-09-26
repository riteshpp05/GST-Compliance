"""
tests.unit.test_s19_operations
===============================
Unit test suite for Sprint 19 Operations Center, Dashboard Aggregation,
Correlation ID tracking, Health Checkers, and Operational Alerts.
"""

import unittest
from app.infrastructure.correlation import get_correlation_id, set_correlation_id, reset_correlation_id
from app.infrastructure.health import ApplicationHealthChecker
from app.infrastructure.metrics import MetricsCollector
from app.operations.alerts import OperationalAlertEvaluator
from app.operations.models import AlertCategoryEnum, AlertSeverityEnum, OperationsDashboardOverview
from app.operations.service import OperationsCenterService


class TestS19Operations(unittest.TestCase):

    def test_correlation_id_context(self):
        reset_correlation_id()
        cid1 = get_correlation_id()
        self.assertTrue(cid1.startswith("corr-"))

        set_correlation_id("custom-correlation-123")
        self.assertEqual(get_correlation_id(), "custom-correlation-123")
        reset_correlation_id()

    def test_health_checkers(self):
        h = ApplicationHealthChecker.check_health()
        self.assertEqual(h["status"], "UP")

        l = ApplicationHealthChecker.check_liveness()
        self.assertEqual(l["status"], "ALIVE")

        r = ApplicationHealthChecker.check_readiness()
        self.assertIn("status", r)
        self.assertTrue(r["ready"])

    def test_metrics_collector(self):
        collector = MetricsCollector()
        collector.record_api_request("/api/test", "GET", 200, 15.0)
        collector.record_tool_execution("get_compliance_result", True, 25.0)
        collector.record_ingestion("JOB-1", 100, 95, 120.0)

        summary = collector.get_summary()
        self.assertEqual(summary.total_api_requests, 1)
        self.assertEqual(summary.total_tool_executions, 1)
        self.assertEqual(summary.total_records_ingested, 100)

    def test_alert_evaluator(self):
        class DummyCase:
            risk_level = "CRITICAL"
            financial_exposure = 75000.0
            case_id = "CASE-ALERT-1"

        alerts = OperationalAlertEvaluator.generate_alerts(
            tenant_id="tenant_default",
            cases=[DummyCase()],
        )
        self.assertGreaterEqual(len(alerts), 2)
        categories = {a.category for a in alerts}
        self.assertIn(AlertCategoryEnum.HIGH_RISK_CASE, categories)
        self.assertIn(AlertCategoryEnum.HIGH_FINANCIAL_EXPOSURE, categories)


if __name__ == "__main__":
    unittest.main()
