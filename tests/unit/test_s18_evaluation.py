"""
tests.unit.test_s18_evaluation
===============================
Unit Test Suite for Sprint 18 AI Evaluation Framework.
Verifies golden dataset execution, 9 weighted metric scoring, and baseline regression detection.
"""

import unittest
from app.evaluation.framework import AIEvaluationFramework
from app.evaluation.golden_dataset import get_golden_dataset


class TestS18Evaluation(unittest.TestCase):

    def test_golden_dataset_structure(self):
        dataset = get_golden_dataset()
        self.assertEqual(len(dataset), 10)
        golden_ids = {tc.golden_id for tc in dataset}
        self.assertIn("GOLDEN-001", golden_ids)
        self.assertIn("GOLDEN-010", golden_ids)

    def test_evaluation_framework_run(self):
        framework = AIEvaluationFramework()
        run = framework.run_evaluation()

        self.assertEqual(run.total_cases, 10)
        self.assertEqual(len(run.case_results), 10)
        self.assertGreaterEqual(run.overall_score, 80.0)
        self.assertIn("INVESTIGATION_CORRECTNESS", run.metric_averages)
        self.assertIn("SECURITY_COMPLIANCE", run.metric_averages)
        self.assertEqual(run.metric_averages["SECURITY_COMPLIANCE"], 100.0)

    def test_regression_comparison(self):
        framework = AIEvaluationFramework()
        run1 = framework.run_evaluation()
        run2 = framework.run_evaluation()

        comparison = framework.compare_runs(candidate_run=run2, baseline_run=run1)
        self.assertEqual(comparison.status, "UNCHANGED")
        self.assertAlmostEqual(comparison.score_difference, 0.0, places=1)
