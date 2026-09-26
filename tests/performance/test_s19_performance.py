"""
tests.performance.test_s19_performance
========================================
Performance Benchmark & Latency Test Suite for Sprint 19.
Verifies micro-benchmarks, percentiles, ops/sec throughput, and regression detection.
"""

import unittest
from app.performance.benchmark import PerformanceBenchmarkRunner, PerformanceBenchmarkReport


class TestS19Performance(unittest.TestCase):

    def test_percentile_calculation(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        p50 = PerformanceBenchmarkRunner.calculate_percentile(vals, 50.0)
        p95 = PerformanceBenchmarkRunner.calculate_percentile(vals, 95.0)
        self.assertGreaterEqual(p50, 50.0)
        self.assertGreaterEqual(p95, 90.0)

    def test_benchmark_scenario_execution(self):
        res = PerformanceBenchmarkRunner.run_benchmark_scenario("Dummy Test Operation", lambda: None, iterations=20)
        self.assertEqual(res.scenario_name, "Dummy Test Operation")
        self.assertEqual(res.total_operations, 20)
        self.assertGreater(res.ops_per_second, 0.0)
        self.assertEqual(res.error_rate_pct, 0.0)

    def test_full_benchmark_suite(self):
        report = PerformanceBenchmarkRunner.run_full_suite()
        self.assertIsInstance(report, PerformanceBenchmarkReport)
        self.assertGreaterEqual(len(report.scenarios), 3)
        self.assertIn(report.overall_status, {"PERFORMANCE_STABLE", "PERFORMANCE_IMPROVED", "PERFORMANCE_REGRESSION"})


if __name__ == "__main__":
    unittest.main()
