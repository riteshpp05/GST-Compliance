"""
tests.unit.test_s18_orchestration
==================================
Unit Test Suite for Sprint 18 Advanced Investigation Orchestration.
Verifies planning, dependency graph resolution, bounded budget limits, conflict detection,
and finding consolidation.
"""

import unittest
from app.investigation.plan import InvestigationBudget, InvestigationPlan, StepResultStatusEnum
from app.investigation.graph import InvestigationGraph
from app.investigation.confidence import InvestigationConfidenceEngine, ConfidenceLevelEnum
from app.investigation.consolidation import FindingConsolidationService
from app.investigation.orchestrator import EnterpriseInvestigationOrchestrator


class TestS18Orchestration(unittest.TestCase):

    def test_investigation_graph_dependency_resolution(self):
        plan = InvestigationGraph.build_default_plan("CASE-TEST-100", "Validate GST compliance", "INV-100")
        self.assertEqual(len(plan.steps), 8)

        # Initially, only Step 1 (no dependencies) is executable
        executable = InvestigationGraph.get_executable_steps(plan)
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0].tool_name, "get_compliance_result")

        # Mark Step 1 SUCCESS
        executable[0].status = StepResultStatusEnum.SUCCESS
        next_executable = InvestigationGraph.get_executable_steps(plan)
        # Steps 2, 3, 4, 5 depend on Step 1
        tool_names = {s.tool_name for s in next_executable}
        self.assertIn("get_risk_assessment", tool_names)
        self.assertIn("find_duplicates", tool_names)
        self.assertIn("get_financial_exposure", tool_names)
        self.assertIn("get_historical_patterns", tool_names)

    def test_confidence_engine_scoring(self):
        engine = InvestigationConfidenceEngine()
        score, level, reasons = engine.calculate_confidence(
            validation_result={"status": "COMPLIANT", "failed_gate_count": 0},
            risk_assessment={"risk_level": "LOW", "risk_score": 10.0},
            evidence_count=5,
            data_quality_score=90.0,
            has_contradictions=False,
        )
        self.assertGreaterEqual(score, 0.85)
        self.assertEqual(level, ConfidenceLevelEnum.VERY_HIGH)
        self.assertTrue(any("Grounded in deterministic" in r for r in reasons))

    def test_conflict_detection_and_consolidation(self):
        service = FindingConsolidationService()
        tool_results = {
            "get_compliance_result": {"status": "COMPLIANT", "failed_gate_count": 0},
            "get_risk_assessment": {"risk_level": "HIGH", "risk_score": 75.0, "risk_drivers": ["HIGH_VALUE"]},
        }
        findings, has_contradictions = service.consolidate_findings("CASE-CONF-1", tool_results, ["EVD-1"])
        self.assertTrue(has_contradictions)
        conf_finding = next(f for f in findings if f.category == "CONFLICTING_ANALYSIS")
        self.assertIn("Conflicting Analysis", conf_finding.title)

    def test_bounded_orchestrator_execution(self):
        orch = EnterpriseInvestigationOrchestrator()
        case = orch.case_service.create_case(title="Test Exec Case", invoice_id="INV-8000001")
        plan = orch.create_plan(case.case_id, "Investigate compliance", "INV-8000001")
        res = orch.execute_investigation(plan)

        self.assertEqual(res["case_id"], case.case_id)
        self.assertIn(res["status"], {"COMPLETED", "LIMIT_REACHED"})
        self.assertGreaterEqual(res["completed_steps"], 5)
        self.assertGreaterEqual(res["evidence_count"], 5)
        self.assertIn("confidence_level", res)
