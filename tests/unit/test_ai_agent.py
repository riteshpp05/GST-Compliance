"""
tests.unit.test_ai_agent
========================
Unit tests for Sprint 12.1 Controlled AI Investigation Agent.
Verifies:
  1. AI Models & Data Schemas
  2. Provider Abstraction (DisabledProvider, MockProvider, factory)
  3. Tool Registry & Read-Only Safety Enforcement
  4. Deterministic Intent Detection & Keyword Matching
  5. Investigation Planner & Tool Subset Selection
  6. Agent Guardrails & Safety Auditing
  7. Deterministic Fallback Synthesis
  8. AI Investigation Agent Orchestration
"""

import unittest
from typing import Dict, Any

from app.agent.ai.models import (
    InvestigationRequest,
    InvestigationIntentEnum,
    InvestigationIntent,
    InvestigationPlan,
    ToolResult,
    InvestigationContext,
    InvestigationResponse,
)
from app.agent.ai.provider import (
    LLMConfig,
    DisabledProvider,
    MockProvider,
    create_llm_provider,
)
from app.agent.ai.registry import ToolRegistry, ToolDefinition
from app.agent.ai.intent import DeterministicIntentDetector
from app.agent.ai.planner import InvestigationPlanner
from app.agent.ai.executor import ToolExecutor
from app.agent.ai.context import InvestigationContextBuilder
from app.agent.ai.guardrails import AgentGuardrails, GuardrailValidationError
from app.agent.ai.synthesizer import LLMSynthesizer
from app.agent.ai.orchestrator import AIInvestigationAgent


class TestAIAgentModels(unittest.TestCase):
    """Test AI Pydantic models & validation schemas."""

    def test_investigation_request_default(self):
        req = InvestigationRequest(user_query="Why is INV-100 high risk?")
        self.assertEqual(req.user_query, "Why is INV-100 high risk?")
        self.assertIsNone(req.invoice_no)

    def test_tool_result_schema(self):
        tr = ToolResult(
            tool_name="get_risk_assessment",
            success=True,
            structured_data={"score": 85.0, "risk_level": "HIGH"},
            execution_time_ms=12.5,
        )
        self.assertEqual(tr.tool_name, "get_risk_assessment")
        self.assertTrue(tr.success)
        self.assertEqual(tr.structured_data["score"], 85.0)

    def test_investigation_response_schema(self):
        resp = InvestigationResponse(
            answer="Financial exposure is Rs. 50,000.",
            intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE,
            findings=[{"tool_name": "get_financial_exposure", "exposure": 50000.0}],
            provider_status={"available": False, "provider_type": "disabled", "model": "none"},
            confidence="HIGH",
            tools_used=["get_financial_exposure"],
        )
        self.assertEqual(resp.confidence, "HIGH")
        self.assertEqual(resp.intent, InvestigationIntentEnum.FINANCIAL_EXPOSURE)


class TestLLMProviders(unittest.TestCase):
    """Test LLM Provider implementations."""

    def test_disabled_provider(self):
        provider = DisabledProvider(LLMConfig(api_key=None))
        self.assertFalse(provider.is_available())

    def test_mock_provider(self):
        provider = MockProvider(LLMConfig(api_key="mock_key", model="mock-model"))
        self.assertTrue(provider.is_available())
        self.assertEqual(provider.generate("test prompt"), "Mock LLM synthesized response.")

    def test_create_llm_provider_fallback(self):
        # Without key -> DisabledProvider
        provider = create_llm_provider(LLMConfig(api_key=None, provider_name="openai"))
        self.assertIsInstance(provider, DisabledProvider)

        # With mock provider name
        provider_mock = create_llm_provider(LLMConfig(provider_name="mock"))
        self.assertIsInstance(provider_mock, MockProvider)


class TestToolRegistry(unittest.TestCase):
    """Test read-only ToolRegistry and tool safety enforcement."""

    def setUp(self):
        self.registry = ToolRegistry()

    def test_register_read_only_tool(self):
        def sample_tool(param: str = "") -> Dict[str, Any]:
            return {"result": f"hello {param}"}

        tool_def = ToolDefinition(
            name="sample_read_tool",
            description="Sample read tool",
            handler=sample_tool,
            read_only=True,
        )
        self.registry.register(tool_def)
        tool = self.registry.get("sample_read_tool")
        self.assertIsNotNone(tool)
        self.assertTrue(tool.read_only)

    def test_reject_mutating_tool(self):
        def mutating_tool() -> Dict[str, Any]:
            return {"status": "mutated"}

        tool_def = ToolDefinition(
            name="mutating_tool",
            description="Mutates database",
            handler=mutating_tool,
            read_only=False,  # MUST FAIL
        )
        with self.assertRaises(ValueError):
            self.registry.register(tool_def)

    def test_execute_tool(self):
        def echo_tool(val: int = 1) -> Dict[str, Any]:
            return {"echo": val}

        tool_def = ToolDefinition(name="echo", description="Echo", handler=echo_tool, read_only=True)
        self.registry.register(tool_def)
        res = self.registry.execute("echo", val=42)
        self.assertTrue(res.success)
        self.assertEqual(res.structured_data, {"echo": 42})

    def test_execute_unknown_tool(self):
        res = self.registry.execute("non_existent_tool")
        self.assertFalse(res.success)
        self.assertIn("not registered", res.errors[0])


class TestIntentDetection(unittest.TestCase):
    """Test Deterministic Intent Detection."""

    def setUp(self):
        self.detector = DeterministicIntentDetector()

    def test_single_invoice_risk_intent(self):
        req = InvestigationRequest(user_query="Why is invoice INV-8000001 non-compliant?")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.INVOICE_INVESTIGATION)
        self.assertEqual(intent.target_invoice_id, "INV-8000001")

    def test_financial_exposure_intent(self):
        req = InvestigationRequest(user_query="What is our total financial tax rate exposure?")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.FINANCIAL_EXPOSURE)

    def test_duplicate_detection_intent(self):
        req = InvestigationRequest(user_query="Find near duplicate invoices in the system")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.DUPLICATE_ANALYSIS)

    def test_anomaly_detection_intent(self):
        req = InvestigationRequest(user_query="Identify value and tax rate statistical anomalies")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.ANOMALY_ANALYSIS)

    def test_root_cause_intent(self):
        req = InvestigationRequest(user_query="Investigate the root cause for failed invoices")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.ROOT_CAUSE_ANALYSIS)

    def test_blast_radius_intent(self):
        req = InvestigationRequest(user_query="Calculate blast radius for rule R-POS-01")
        intent = self.detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.BLAST_RADIUS_ANALYSIS)


class TestInvestigationPlanner(unittest.TestCase):
    """Test Investigation Planner mappings."""

    def setUp(self):
        self.planner = InvestigationPlanner()

    def test_plan_financial_exposure(self):
        intent = InvestigationIntent(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, confidence=1.0, explanation="Test")
        plan = self.planner.create_plan(intent)
        self.assertIn("get_financial_exposure", plan.required_tools)

    def test_plan_single_invoice_risk(self):
        intent = InvestigationIntent(intent=InvestigationIntentEnum.INVOICE_INVESTIGATION, confidence=1.0, explanation="Test", target_invoice_id="INV-001")
        plan = self.planner.create_plan(intent)
        self.assertIn("get_risk_assessment", plan.required_tools)
        self.assertIn("get_compliance_result", plan.required_tools)


class TestAgentGuardrails(unittest.TestCase):
    """Test Safety Guardrails & Validation."""

    def setUp(self):
        self.registry = ToolRegistry()
        self.guardrails = AgentGuardrails(self.registry)

    def test_audit_plan_approved_tools(self):
        self.registry.register(ToolDefinition(name="valid_tool", description="desc", handler=lambda: {}, read_only=True))
        plan = InvestigationPlan(intent=InvestigationIntentEnum.GENERAL_COMPLIANCE, required_tools=["valid_tool"], reasoning_steps=["Test"])
        # Should not raise exception
        self.guardrails.validate_plan(plan)

    def test_audit_plan_unapproved_tool(self):
        plan = InvestigationPlan(intent=InvestigationIntentEnum.GENERAL_COMPLIANCE, required_tools=["unregistered_mutating_tool"], reasoning_steps=["Test"])
        with self.assertRaises(GuardrailValidationError):
            self.guardrails.validate_plan(plan)


class TestLLMSynthesizer(unittest.TestCase):
    """Test Deterministic Fallback & LLM Synthesizer."""

    def setUp(self):
        self.provider = DisabledProvider(LLMConfig())
        self.synthesizer = LLMSynthesizer(provider=self.provider)

    def test_fallback_synthesis(self):
        req = InvestigationRequest(user_query="What is financial exposure?")
        intent = InvestigationIntent(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, confidence=1.0, explanation="Exposure check")
        plan = InvestigationPlan(intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE, required_tools=["get_financial_exposure"])
        results = [
            ToolResult(
                tool_name="get_financial_exposure",
                success=True,
                structured_data={"summary": {"total_ineligible_itc_exposure": 125000.0, "high_risk_invoice_count": 3}},
                execution_time_ms=5.0,
            )
        ]
        context = InvestigationContext(request=req, intent=intent, plan=plan, tool_results=results)
        response = self.synthesizer.synthesize(context)
        self.assertIn("Deterministic GST Engine Determination", response.answer)
        self.assertEqual(response.confidence, "HIGH")


class TestAIInvestigationAgentOrchestration(unittest.TestCase):
    """Test end-to-end AIInvestigationAgent facade."""

    def setUp(self):
        disabled_provider = DisabledProvider(LLMConfig())
        self.agent = AIInvestigationAgent(provider=disabled_provider)

    def test_investigate_fallback_mode(self):
        req = InvestigationRequest(user_query="What is total financial exposure?")
        resp = self.agent.investigate(req)
        self.assertEqual(resp.intent, InvestigationIntentEnum.FINANCIAL_EXPOSURE)
        self.assertIn("Deterministic GST Engine Determination", resp.answer)

    def test_investigate_mock_mode(self):
        mock_provider = MockProvider(LLMConfig(api_key="mock_key"))
        mock_agent = AIInvestigationAgent(provider=mock_provider)
        req = InvestigationRequest(user_query="Find duplicate invoices")
        resp = mock_agent.investigate(req)
        self.assertEqual(resp.intent, InvestigationIntentEnum.DUPLICATE_ANALYSIS)


if __name__ == "__main__":
    unittest.main()
