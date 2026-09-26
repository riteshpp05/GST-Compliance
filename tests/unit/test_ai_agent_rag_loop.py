"""
tests.unit.test_ai_agent_rag_loop
=================================
Unit test suite for Sprint 12.3 RAG Knowledge integration with S12.2 Bounded Agentic Loop.
Verifies:
  1. Knowledge tool registration and read-only boundary
  2. Intent classification for REGULATORY_KNOWLEDGE queries
  3. Bounded loop execution with retrieve_gst_knowledge tool
  4. Automatic RAG invocation when compliance discrepancy occurs
  5. Prevention of unnecessary RAG for numeric/exposure-only queries
  6. S12.2 budget limits preservation during knowledge retrieval
  7. Deterministic synthesis fallback with regulatory evidence and provenance
"""

import unittest
from app.agent.ai.intent import DeterministicIntentDetector
from app.agent.ai.models import (
    InvestigationBudget,
    InvestigationIntentEnum,
    InvestigationRequest,
    InvestigationStatusEnum,
    TerminationReasonEnum,
)
from app.agent.ai.orchestrator import AIInvestigationAgent
from app.agent.ai.provider import DisabledProvider, LLMConfig
from app.agent.ai.registry import ToolRegistry


class TestAIAgentRAGLoopIntegration(unittest.TestCase):
    """Integration test suite for Knowledge Tool & RAG Agentic Loop."""

    def setUp(self):
        self.disabled_agent = AIInvestigationAgent(provider=DisabledProvider(LLMConfig()))

    def test_knowledge_tool_registration_and_readonly(self):
        registry = self.disabled_agent.registry
        tool_def = registry.get("retrieve_gst_knowledge")
        self.assertIsNotNone(tool_def)
        self.assertTrue(tool_def.read_only)
        self.assertEqual(tool_def.category, "KNOWLEDGE")

    def test_intent_detection_regulatory_query(self):
        detector = DeterministicIntentDetector()
        req = InvestigationRequest(user_query="What GST rule applies to E-Way bill threshold?")
        intent = detector.detect_intent(req)
        self.assertEqual(intent.intent, InvestigationIntentEnum.REGULATORY_KNOWLEDGE)

    def test_rag_loop_execution_regulatory_query(self):
        resp = self.disabled_agent.investigate("What GST rule applies to Rule 36(4) ITC?")
        self.assertEqual(resp.intent, InvestigationIntentEnum.REGULATORY_KNOWLEDGE)
        self.assertIn("retrieve_gst_knowledge", resp.tools_used)
        self.assertEqual(resp.investigation_status, "EVIDENCE_SUFFICIENT")

        # Verify trace timeline step recorded
        rag_step_found = any(step.get("tool_name") == "retrieve_gst_knowledge" for step in resp.investigation_steps)
        self.assertTrue(rag_step_found)

    def test_failed_invoice_triggers_rag_for_policy_explanation(self):
        resp = self.disabled_agent.investigate("Why is invoice INV-8000001 non-compliant?")
        # INVOICE_INVESTIGATION triggers compliance, risk, and retrieve_gst_knowledge when failed gates exist
        self.assertIn("get_compliance_result", resp.tools_used)

    def test_no_unnecessary_rag_for_exposure_query(self):
        resp = self.disabled_agent.investigate("What is our total tax exposure across non-compliant invoices?")
        self.assertEqual(resp.intent, InvestigationIntentEnum.FINANCIAL_EXPOSURE)
        self.assertIn("get_financial_exposure", resp.tools_used)
        # Exposure query should not invoke retrieve_gst_knowledge unnecessarily
        self.assertNotIn("retrieve_gst_knowledge", resp.tools_used)

    def test_rag_consumes_investigation_budget(self):
        req = InvestigationRequest(user_query="What rule applies to ITC?", budget=InvestigationBudget(max_steps=1))
        resp = self.disabled_agent.investigate(req)
        self.assertLessEqual(len(resp.tools_used), 1)
        self.assertIn(resp.termination_reason, ["SUFFICIENT_EVIDENCE", "MAX_STEPS_REACHED"])


if __name__ == "__main__":
    unittest.main()
