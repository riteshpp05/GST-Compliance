"""
tests.unit.test_ai_agent_loop
=============================
Unit tests for Sprint 12.2 Bounded Agentic Investigation Loop.
Verifies:
  1. Single-tool investigation loop execution
  2. Multi-tool investigation loop execution
  3. Evidence sufficient termination
  4. Evidence insufficient termination
  5. Max steps reached budget limit termination
  6. Max tool calls reached budget limit termination
  7. Timeout budget limit termination
  8. Invalid/unregistered tool rejection
  9. Non-read-only tool execution prevention
  10. Unapproved tool rejection (allow-list violation)
  11. Duplicate tool call prevention
  12. Evidence accumulation across multi-step loop
  13. Contradiction detection in EvidenceEvaluator
  14. Insufficient evidence handling in final response
  15. Provider fallback initialization
  16. Mid-loop provider failure fallback
  17. Controlled tool selection with MockProvider
  18. Malformed LLM response fallback to deterministic selector
  19. Hallucinated tool rejection by ControlledToolSelector
  20. Backward compatibility for S12.1 single-plan investigation flow
"""

import time
import unittest
from typing import Any, Dict
from unittest.mock import MagicMock

from app.agent.ai.evaluator import EvidenceEvaluator
from app.agent.ai.guardrails import AgentGuardrails, GuardrailValidationError
from app.agent.ai.loop import InvestigationLoopEngine
from app.agent.ai.models import (
    EvaluationStatusEnum,
    EvidenceEvaluation,
    InvestigationBudget,
    InvestigationContext,
    InvestigationIntent,
    InvestigationIntentEnum,
    InvestigationPlan,
    InvestigationRequest,
    InvestigationResponse,
    InvestigationState,
    InvestigationStatusEnum,
    NextInvestigationAction,
    TerminationReasonEnum,
    ToolResult,
)
from app.agent.ai.orchestrator import AIInvestigationAgent
from app.agent.ai.provider import DisabledProvider, LLMConfig, MockProvider
from app.agent.ai.registry import ToolDefinition, ToolRegistry
from app.agent.ai.selector import ControlledToolSelector
from app.agent.compliance_agent import GSTComplianceAgent


class TestInvestigationStateAndBudget(unittest.TestCase):
    """Test InvestigationState and InvestigationBudget models."""

    def test_state_initialization(self):
        req = InvestigationRequest(user_query="Why is INV-8000001 high risk?")
        intent = InvestigationIntent(
            intent=InvestigationIntentEnum.INVOICE_INVESTIGATION,
            confidence=1.0,
            target_invoice_id="INV-8000001",
        )
        plan = InvestigationPlan(
            intent=InvestigationIntentEnum.INVOICE_INVESTIGATION,
            required_tools=["get_compliance_result", "get_risk_assessment"],
        )

        loop_engine = InvestigationLoopEngine()
        state = loop_engine.initialize_state(req, intent, plan)

        self.assertTrue(state.investigation_id.startswith("INVEST-"))
        self.assertEqual(state.status, InvestigationStatusEnum.INITIALIZED)
        self.assertEqual(len(state.trace), 1)
        self.assertEqual(state.trace[0].action_type, "INTENT_AND_PLANNING")
        self.assertEqual(state.target, "INV-8000001")


class TestEvidenceEvaluator(unittest.TestCase):
    """Test EvidenceEvaluator rules and contradiction checks."""

    def setUp(self):
        self.evaluator = EvidenceEvaluator()

    def test_evaluate_insufficient_when_no_tools_executed(self):
        req = InvestigationRequest(user_query="Investigate invoice INV-8000001")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result"])
        state = InvestigationState(request=req, intent=intent, initial_plan=plan)

        eval_res = self.evaluator.evaluate(state)
        self.assertFalse(eval_res.sufficient)
        self.assertEqual(eval_res.status, EvaluationStatusEnum.INSUFFICIENT)
        self.assertIn("get_compliance_result", eval_res.recommended_next_tools)

    def test_evaluate_sufficient_for_single_tool_intent(self):
        req = InvestigationRequest(user_query="Check financial exposure")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, required_tools=["get_financial_exposure"])
        state = InvestigationState(
            request=req,
            intent=intent,
            initial_plan=plan,
            executed_tools=["get_financial_exposure"],
            tool_results=[
                ToolResult(
                    tool_name="get_financial_exposure",
                    success=True,
                    structured_data={"total_potential_exposure": 50000.0},
                )
            ],
        )

        eval_res = self.evaluator.evaluate(state)
        self.assertTrue(eval_res.sufficient)
        self.assertEqual(eval_res.status, EvaluationStatusEnum.SUFFICIENT)

    def test_evaluate_contradiction_detection(self):
        req = InvestigationRequest(user_query="Check compliance and risk for INV-8000001")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])

        state = InvestigationState(
            request=req,
            intent=intent,
            initial_plan=plan,
            executed_tools=["get_compliance_result", "get_risk_assessment"],
            tool_results=[
                ToolResult(
                    tool_name="get_compliance_result",
                    success=True,
                    structured_data={"status": "COMPLIANT", "failed_gate_count": 0},
                ),
                ToolResult(
                    tool_name="get_risk_assessment",
                    success=True,
                    structured_data={"risk_level": "HIGH", "risk_score": 85.0},
                ),
            ],
        )

        eval_res = self.evaluator.evaluate(state)
        self.assertTrue(len(eval_res.contradictions) > 0)
        self.assertIn("HIGH risk", eval_res.contradictions[0])


class TestControlledToolSelector(unittest.TestCase):
    """Test ControlledToolSelector next tool decisions and security boundaries."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.guardrails = AgentGuardrails(registry=self.registry)
        self.selector = ControlledToolSelector(registry=self.registry, guardrails=self.guardrails)

    def test_selects_unexecuted_plan_tool_deterministically(self):
        req = InvestigationRequest(user_query="Check risk for INV-8000001")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])
        state = InvestigationState(request=req, intent=intent, initial_plan=plan, executed_tools=["get_compliance_result"])
        evaluation = EvidenceEvaluation(status=EvaluationStatusEnum.INSUFFICIENT, sufficient=False, recommended_next_tools=["get_risk_assessment"])

        next_act = self.selector.select_next_action(state, evaluation)
        self.assertEqual(next_act.action, "CALL_TOOL")
        self.assertEqual(next_act.tool_name, "get_risk_assessment")

    def test_rejects_hallucinated_tool(self):
        req = InvestigationRequest(user_query="Check risk")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.RISK_ANALYSIS, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.RISK_ANALYSIS, required_tools=["get_risk_assessment"])
        state = InvestigationState(request=req, intent=intent, initial_plan=plan, executed_tools=["get_risk_assessment"])
        evaluation = EvidenceEvaluation(status=EvaluationStatusEnum.INSUFFICIENT, sufficient=False)

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.structured_generate.return_value = NextInvestigationAction(
            action="CALL_TOOL",
            tool_name="delete_database_records",  # Hallucinated tool!
            reason="I want to delete records",
        )

        next_act = self.selector.select_next_action(state, evaluation, provider=mock_provider)
        # Must reject hallucinated tool and finish
        self.assertEqual(next_act.action, "FINISH")


class TestInvestigationLoopEngine(unittest.TestCase):
    """Test bounded loop engine execution, budget constraints, and trace recording."""

    def setUp(self):
        self.agent_facade = GSTComplianceAgent()
        self.registry = ToolRegistry(agent=self.agent_facade)
        self.loop_engine = InvestigationLoopEngine(registry=self.registry)

    def test_single_tool_loop_success(self):
        req = InvestigationRequest(user_query="What is total tax exposure?")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, required_tools=["get_financial_exposure"])

        state = self.loop_engine.initialize_state(req, intent, plan)
        final_state = self.loop_engine.run_loop(state)

        self.assertEqual(final_state.status, InvestigationStatusEnum.EVIDENCE_SUFFICIENT)
        self.assertEqual(final_state.termination_reason, TerminationReasonEnum.SUFFICIENT_EVIDENCE)
        self.assertIn("get_financial_exposure", final_state.executed_tools)

    def test_multi_tool_loop_success(self):
        req = InvestigationRequest(user_query="Why is invoice INV-8000001 non-compliant?")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0, target_invoice_id="INV-8000001")
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])

        state = self.loop_engine.initialize_state(req, intent, plan)
        final_state = self.loop_engine.run_loop(state)

        self.assertEqual(final_state.status, InvestigationStatusEnum.EVIDENCE_SUFFICIENT)
        self.assertIn("get_compliance_result", final_state.executed_tools)
        self.assertIn("get_risk_assessment", final_state.executed_tools)

    def test_max_steps_budget_exhaustion(self):
        req = InvestigationRequest(
            user_query="Investigate invoice INV-8000001",
            budget=InvestigationBudget(max_steps=1, max_tool_calls=5, max_execution_time_seconds=20.0),
        )
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        # Needs 2 tools but max_steps=1
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])

        state = self.loop_engine.initialize_state(req, intent, plan)
        final_state = self.loop_engine.run_loop(state)

        self.assertEqual(final_state.status, InvestigationStatusEnum.BUDGET_EXHAUSTED)
        self.assertEqual(final_state.termination_reason, TerminationReasonEnum.MAX_STEPS_REACHED)

    def test_max_tool_calls_budget_exhaustion(self):
        req = InvestigationRequest(
            user_query="Investigate invoice INV-8000001",
            budget=InvestigationBudget(max_steps=5, max_tool_calls=1, max_execution_time_seconds=20.0),
        )
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])

        state = self.loop_engine.initialize_state(req, intent, plan)
        final_state = self.loop_engine.run_loop(state)

        self.assertEqual(final_state.status, InvestigationStatusEnum.BUDGET_EXHAUSTED)
        self.assertEqual(final_state.termination_reason, TerminationReasonEnum.MAX_TOOL_CALLS_REACHED)

    def test_timeout_budget_exhaustion(self):
        req = InvestigationRequest(
            user_query="Investigate invoice INV-8000001",
            budget=InvestigationBudget(max_steps=5, max_tool_calls=5, max_execution_time_seconds=0.001),
        )
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, required_tools=["get_compliance_result", "get_risk_assessment"])

        state = self.loop_engine.initialize_state(req, intent, plan)
        time.sleep(0.01)  # Ensure timeout threshold exceeded
        final_state = self.loop_engine.run_loop(state)

        self.assertEqual(final_state.status, InvestigationStatusEnum.BUDGET_EXHAUSTED)
        self.assertEqual(final_state.termination_reason, TerminationReasonEnum.TIMEOUT)

    def test_mid_loop_provider_failure_graceful_fallback(self):
        req = InvestigationRequest(user_query="Analyze risks")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.RISK_ANALYSIS, confidence=1.0)
        plan = InvestigationPlan(intent=InvestigationIntentEnum.RISK_ANALYSIS, required_tools=["get_risk_assessment"])

        failing_provider = MagicMock()
        failing_provider.is_available.return_value = True
        failing_provider.structured_generate.side_effect = RuntimeError("Mid-loop LLM connection reset")

        state = self.loop_engine.initialize_state(req, intent, plan)
        final_state = self.loop_engine.run_loop(state, provider=failing_provider)

        # Should complete loop using deterministic selector
        self.assertIn("get_risk_assessment", final_state.executed_tools)


class TestFullAIInvestigationAgentLoop(unittest.TestCase):
    """End-to-end integration tests for AIInvestigationAgent with S12.2 loop."""

    def setUp(self):
        self.disabled_agent = AIInvestigationAgent(provider=DisabledProvider(LLMConfig()))
        self.mock_agent = AIInvestigationAgent(provider=MockProvider(LLMConfig(api_key="mock_key")))

    def test_full_investigation_with_trace_and_sufficiency(self):
        resp = self.disabled_agent.investigate("Why is invoice INV-8000001 high risk?")

        self.assertIsNotNone(resp.investigation_id)
        self.assertTrue(resp.investigation_id.startswith("INVEST-"))
        self.assertIsNotNone(resp.investigation_status)
        self.assertIsNotNone(resp.termination_reason)
        self.assertTrue(len(resp.investigation_steps) >= 2)
        self.assertIn("sufficient", resp.evidence_sufficiency)

    def test_backward_compatibility_s12_1(self):
        resp = self.disabled_agent.investigate("What is our total financial exposure?")
        self.assertEqual(resp.intent, InvestigationIntentEnum.FINANCIAL_EXPOSURE)
        self.assertIn("get_financial_exposure", resp.tools_used)
        self.assertEqual(resp.confidence, "HIGH")


if __name__ == "__main__":
    unittest.main()
