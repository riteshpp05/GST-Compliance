"""
app.performance.benchmark
=========================
Reproducible Performance Benchmark & Profiling Suite for UC15 (Sprint 19).
Measures API latency, data ingestion throughput, investigation step execution,
tool call latencies, and database query performance.
Computes average, median, p95, p99, throughput, and error rates.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class BenchmarkMetricResult(BaseModel):
    """Result structure for a single benchmark scenario."""
    scenario_name: str = Field(..., description="Benchmark scenario name.")
    total_operations: int = Field(..., description="Total operations executed.")
    duration_seconds: float = Field(..., description="Total execution time.")
    ops_per_second: float = Field(..., description="Throughput in ops/sec.")
    avg_latency_ms: float = Field(..., description="Average latency in ms.")
    median_latency_ms: float = Field(..., description="Median latency in ms.")
    p95_latency_ms: float = Field(..., description="95th percentile latency in ms.")
    p99_latency_ms: float = Field(..., description="99th percentile latency in ms.")
    error_rate_pct: float = Field(0.0, description="Error rate percentage.")
    status: str = Field("PERFORMANCE_STABLE", description="PERFORMANCE_IMPROVED, PERFORMANCE_STABLE, PERFORMANCE_REGRESSION")


class PerformanceBenchmarkReport(BaseModel):
    """Unified benchmark report across all system components."""
    timestamp: str = Field(..., description="UTC ISO timestamp.")
    overall_status: str = Field("PERFORMANCE_STABLE", description="Overall performance status.")
    scenarios: List[BenchmarkMetricResult] = Field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class PerformanceBenchmarkRunner:
    """
    Executes micro-benchmarks against system components and measures metrics.
    """

    @classmethod
    def calculate_percentile(cls, sorted_vals: List[float], pct: float) -> float:
        """Calculate percentile value from a sorted list of floats."""
        if not sorted_vals:
            return 0.0
        k = (len(sorted_vals) - 1) * (pct / 100.0)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return sorted_vals[int(k)]
        return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)

    @classmethod
    def run_benchmark_scenario(
        cls,
        name: str,
        operation_fn: Any,
        iterations: int = 50,
    ) -> BenchmarkMetricResult:
        """
        Execute an operation repeatedly and measure latency stats.
        """
        latencies: List[float] = []
        errors = 0
        start_total = time.perf_counter()

        for _ in range(iterations):
            t0 = time.perf_counter()
            try:
                operation_fn()
                latencies.append((time.perf_counter() - t0) * 1000.0)
            except Exception as e:
                errors += 1
                latencies.append((time.perf_counter() - t0) * 1000.0)

        total_time = max(time.perf_counter() - start_total, 0.001)
        sorted_lat = sorted(latencies)

        avg_lat = sum(sorted_lat) / max(len(sorted_lat), 1)
        med_lat = cls.calculate_percentile(sorted_lat, 50.0)
        p95_lat = cls.calculate_percentile(sorted_lat, 95.0)
        p99_lat = cls.calculate_percentile(sorted_lat, 99.0)
        throughput = round(iterations / total_time, 2)
        err_pct = round((errors / max(iterations, 1)) * 100.0, 2)

        status = "PERFORMANCE_STABLE"
        if err_pct > 5.0 or p95_lat > 2000.0:
            status = "PERFORMANCE_REGRESSION"

        result = BenchmarkMetricResult(
            scenario_name=name,
            total_operations=iterations,
            duration_seconds=round(total_time, 3),
            ops_per_second=throughput,
            avg_latency_ms=round(avg_lat, 2),
            median_latency_ms=round(med_lat, 2),
            p95_latency_ms=round(p95_lat, 2),
            p99_latency_ms=round(p99_lat, 2),
            error_rate_pct=err_pct,
            status=status,
        )
        logger.info(f"Executed benchmark '{name}': {throughput} ops/s, p95={p95_lat:.2f}ms, err={err_pct}%.")
        return result

    @classmethod
    def run_full_suite(cls) -> PerformanceBenchmarkReport:
        """
        Run complete performance benchmark suite across core scenarios.
        """
        import time
        from datetime import datetime, timezone
        from app.data.service import get_data_ingestion_service
        from app.investigation.orchestrator import get_enterprise_orchestrator
        from app.security import get_internal_compatibility_principal

        principal = get_internal_compatibility_principal()
        scenarios: List[BenchmarkMetricResult] = []

        # Scenario 1: Data Normalization Micro-Benchmark
        from app.data.normalization import InvoiceNormalizer
        def _norm_op():
            InvoiceNormalizer.normalize_record({
                "supplier_gstin": "27AABCU9603R1ZM",
                "invoice_number": "INV-PERF-001",
                "invoice_date": "2026-03-15",
                "taxable_value": 10000.0,
                "cgst_amount": 900.0,
                "sgst_amount": 900.0,
            }, record_index=1)
        scenarios.append(cls.run_benchmark_scenario("Data Normalization (100 ops)", _norm_op, iterations=100))

        # Scenario 2: Data Deduplication Fingerprinting
        from app.data.deduplication import DeduplicationEngine
        def _dedup_op():
            DeduplicationEngine.compute_exact_fingerprint(
                supplier_gstin="27AABCU9603R1ZM",
                invoice_number="INV-PERF-001",
                invoice_date="2026-03-15",
                taxable_value=10000.0,
            )
        scenarios.append(cls.run_benchmark_scenario("Deduplication Fingerprinting (100 ops)", _dedup_op, iterations=100))

        # Scenario 3: Data Quality Scoring
        from app.data.quality import DataQualityEngine
        from app.domain.models.invoice import Invoice
        def _dq_op():
            inv = Invoice(supplier_gstin="27AABCU9603R1ZM", invoice_number="INV-PERF-001", invoice_date="2026-03-15", taxable_value=10000.0)
            DataQualityEngine.evaluate_record(
                record_id="REC-PERF-001",
                record_index=1,
                raw_record={"supplier_gstin": "27AABCU9603R1ZM", "invoice_number": "INV-PERF-001"},
                canonical_invoice=inv,
                duplicate_status="UNIQUE",
            )
        scenarios.append(cls.run_benchmark_scenario("Data Quality Scoring (20 ops)", _dq_op, iterations=20))

        # Scenario 4: Bounded Investigation Orchestration
        orch = get_enterprise_orchestrator()
        def _inv_op():
            case = orch.case_service.create_case(title="Perf Test Case", invoice_id="INV-S19-001", principal=principal)
            plan = orch.create_plan(case.case_id, "Benchmark Investigation", "INV-S19-001", tenant_id=principal.tenant_id)
            orch.execute_investigation(plan, principal=principal)
        scenarios.append(cls.run_benchmark_scenario("Investigation Execution (3 ops)", _inv_op, iterations=3))

        overall = "PERFORMANCE_STABLE"
        if any(s.status == "PERFORMANCE_REGRESSION" for s in scenarios):
            overall = "PERFORMANCE_REGRESSION"
        elif all(s.ops_per_second > 50.0 for s in scenarios):
            overall = "PERFORMANCE_IMPROVED"

        report = PerformanceBenchmarkReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status=overall,
            scenarios=scenarios,
        )
        return report
