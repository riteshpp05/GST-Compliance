"""
app.agent.ai.orchestrator
========================
Main Facade Orchestrator for UC15 Controlled AI Investigation Agent (Sprint 12.1).
Coordinates Intent Detection -> Planning -> Guardrails -> Read-Only Tool Execution -> Evidence Context -> LLM Synthesis.
"""

from __future__ import annotations

from typing import Optional, Union
from app.agent.ai.context import InvestigationContextBuilder
from app.agent.ai.dossier import DossierBuilder, InvestigationDossier
from app.agent.ai.executor import ToolExecutor
from app.agent.ai.guardrails import AgentGuardrails
from app.agent.ai.intent import DeterministicIntentDetector
from app.agent.ai.loop import InvestigationLoopEngine
from app.agent.ai.models import InvestigationRequest, InvestigationResponse
from app.agent.ai.planner import InvestigationPlanner
from app.agent.ai.provider import LLMProvider, create_llm_provider
from app.agent.ai.registry import ToolRegistry
from app.agent.ai.session import SessionManager, get_session_manager
from app.agent.ai.synthesizer import LLMSynthesizer
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class AIInvestigationAgent:
    """
    Controlled AI Investigation Agent Facade for UC15 (Sprint 12.1 – 12.4).
    Performs evidence-first multi-turn investigations using bounded agentic loops,
    session context retention, and automated dossier building.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        compliance_agent: Optional[Any] = None,
        registry: Optional[ToolRegistry] = None,
        loop_engine: Optional[InvestigationLoopEngine] = None,
        session_manager: Optional[SessionManager] = None,
    ) -> None:
        if compliance_agent is None:
            from app.agent.compliance_agent import GSTComplianceAgent
            compliance_agent = GSTComplianceAgent()

        self.provider = provider or create_llm_provider()
        self.compliance_agent = compliance_agent
        self.registry = registry or ToolRegistry(agent=self.compliance_agent)
        self.intent_detector = DeterministicIntentDetector()
        self.planner = InvestigationPlanner()
        self.executor = ToolExecutor(registry=self.registry)
        self.context_builder = InvestigationContextBuilder()
        self.guardrails = AgentGuardrails(registry=self.registry)
        self.synthesizer = LLMSynthesizer(provider=self.provider, guardrails=self.guardrails)
        self.loop_engine = loop_engine or InvestigationLoopEngine(
            registry=self.registry,
            executor=self.executor,
            guardrails=self.guardrails,
        )
        self.session_manager = session_manager or get_session_manager()

    def investigate(
        self,
        request: Union[InvestigationRequest, str, dict],
        session_id: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationResponse:
        """
        Execute an end-to-end controlled investigation request.
        Supports single queries and multi-turn investigation session context retention.
        """
        if isinstance(request, str):
            req = InvestigationRequest(user_query=request)
        elif isinstance(request, dict):
            req = InvestigationRequest.model_validate(request)
        else:
            req = request

        # 0. Query Input Hardening & Sanitization
        sanitized_query = self.guardrails.sanitize_query(req.user_query)
        req.user_query = sanitized_query

        # 1. Multi-Turn Session & Context Resolution
        target_session_id = session_id or req.session_id
        session = None
        resolved_query = sanitized_query
        if target_session_id:
            session = self.session_manager.get_session(target_session_id)

        if session:
            resolved_query, extracted_params = self.session_manager.resolve_query_context(
                session, sanitized_query, explicit_invoice_id=req.invoice_no
            )
            req.user_query = resolved_query
            if "invoice_id" in extracted_params and not req.invoice_no:
                req.invoice_no = extracted_params["invoice_id"]
        else:
            # Auto-create session if requested or start standalone
            session = self.session_manager.create_session()
            if req.invoice_no:
                session.entity_focus.update(invoice_id=req.invoice_no)

        logger.info(f"Starting AI Investigation for query: '{req.user_query}' (Session: {session.session_id})")

        # 2. Intent Detection
        intent_res = self.intent_detector.detect_intent(req, provider=self.provider)

        # 3. Investigation Planning
        plan = self.planner.create_plan(intent_res)

        # 4. Plan Guardrail Verification
        self.guardrails.validate_plan(plan)

        # 5. Initialize State & Run Bounded Investigation Loop
        state = self.loop_engine.initialize_state(req, intent_res, plan)
        final_state = self.loop_engine.run_loop(state, provider=self.provider, principal=principal)

        # 6. Evidence Context Assembly
        context = self.context_builder.build_context(
            req, intent_res, plan, final_state.tool_results, state=final_state
        )

        # 7. LLM Synthesis or Deterministic Fallback
        response = self.synthesizer.synthesize(context)

        # 8. Record Turn in Multi-Turn Session State
        know_items = [ev.model_dump() if hasattr(ev, "model_dump") else ev for ev in response.knowledge_evidence]
        self.session_manager.record_turn(
            session_id=session.session_id,
            user_query=sanitized_query,
            resolved_query=resolved_query,
            intent=response.intent.value if hasattr(response.intent, "value") else str(response.intent),
            tools_used=response.tools_used,
            findings=response.findings,
            regulatory_knowledge=know_items,
            synthesized_answer=response.answer,
            confidence=response.confidence,
        )

        # Attach session and focus details to response
        response.session_id = session.session_id
        response.entity_focus = session.entity_focus.model_dump()

        logger.info(
            f"Completed investigation response for intent {response.intent.value} with status {response.investigation_status} (Session: {session.session_id})"
        )
        return response

    def generate_dossier(self, session_id: str) -> InvestigationDossier:
        """
        Generate a complete evidence-backed audit dossier for an investigation session.
        """
        sess = self.session_manager.get_session(session_id)
        if not sess:
            raise ValueError(f"Investigation session '{session_id}' not found.")

        return DossierBuilder.build_dossier(sess)
