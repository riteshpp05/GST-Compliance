"""
app.infrastructure.metrics
==========================
Application Operational Metrics Collector for UC15 (Sprint 19).
Tracks API request counts, latencies, agent tool calls, ingestion throughput,
database operation timings, and evaluation metric counters.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

_GLOBAL_METRICS_COLLECTOR: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Singleton getter for MetricsCollector."""
    global _GLOBAL_METRICS_COLLECTOR
    if _GLOBAL_METRICS_COLLECTOR is None:
        _GLOBAL_METRICS_COLLECTOR = MetricsCollector()
    return _GLOBAL_METRICS_COLLECTOR


class MetricsSummary(BaseModel):
    """Snapshot summary of operational metrics counters."""
    total_api_requests: int = Field(0, description="Total API requests.")
    successful_api_requests: int = Field(0, description="Successful API requests.")
    failed_api_requests: int = Field(0, description="Failed API requests.")
    average_api_latency_ms: float = Field(0.0, description="Average API latency in ms.")
    total_tool_executions: int = Field(0, description="Total agent tool executions.")
    tool_failures: int = Field(0, description="Failed tool executions count.")
    total_records_ingested: int = Field(0, description="Total ingestion records processed.")
    database_queries_count: int = Field(0, description="Database queries executed.")
    evaluation_runs_count: int = Field(0, description="Evaluation runs executed.")


class MetricsCollector:
    """
    In-memory metrics aggregation engine recording operational application counters.
    """

    def __init__(self) -> None:
        self.api_requests: List[Dict[str, Any]] = []
        self.tool_executions: List[Dict[str, Any]] = []
        self.ingestion_events: List[Dict[str, Any]] = []
        self.db_operations: List[Dict[str, Any]] = []
        self.eval_events: List[Dict[str, Any]] = []

    def record_api_request(self, endpoint: str, method: str, status_code: int, duration_ms: float) -> None:
        """Record an API request event."""
        self.api_requests.append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_tool_execution(self, tool_name: str, success: bool, duration_ms: float) -> None:
        """Record an agent tool execution event."""
        self.tool_executions.append({
            "tool_name": tool_name,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_ingestion(self, job_id: str, total_records: int, accepted_records: int, duration_ms: float) -> None:
        """Record a data ingestion pipeline event."""
        self.ingestion_events.append({
            "job_id": job_id,
            "total_records": total_records,
            "accepted_records": accepted_records,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_db_operation(self, operation: str, table: str, duration_ms: float) -> None:
        """Record a database query operation event."""
        self.db_operations.append({
            "operation": operation,
            "table": table,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def record_evaluation(self, run_id: str, score: float, passed: bool) -> None:
        """Record an AI evaluation run event."""
        self.eval_events.append({
            "run_id": run_id,
            "score": score,
            "passed": passed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_summary(self) -> MetricsSummary:
        """Calculate and return snapshot metrics summary."""
        total_reqs = len(self.api_requests)
        succ_reqs = len([r for r in self.api_requests if r["status_code"] < 400])
        fail_reqs = total_reqs - succ_reqs
        avg_lat = round(sum(r["duration_ms"] for r in self.api_requests) / max(total_reqs, 1), 2) if total_reqs else 0.0

        total_tools = len(self.tool_executions)
        tool_fails = len([t for t in self.tool_executions if not t["success"]])

        total_recs = sum(i["total_records"] for i in self.ingestion_events)

        return MetricsSummary(
            total_api_requests=total_reqs,
            successful_api_requests=succ_reqs,
            failed_api_requests=fail_reqs,
            average_api_latency_ms=avg_lat,
            total_tool_executions=total_tools,
            tool_failures=tool_fails,
            total_records_ingested=total_recs,
            database_queries_count=len(self.db_operations),
            evaluation_runs_count=len(self.eval_events),
        )
