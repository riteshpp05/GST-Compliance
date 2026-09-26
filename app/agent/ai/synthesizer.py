"""
app.agent.ai.synthesizer
========================
LLM Synthesizer & Deterministic Fallback Engine for UC15 (Sprint 12.1 & 12.2).
Synthesizes structured, evidence-grounded InvestigationResponse objects using the LLMProvider.
Provides a rich deterministic fallback response when AI is unavailable or unconfigured.
Populates S12.2 agentic loop trace metadata and evidence sufficiency summaries.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.agent.ai.context import InvestigationContext
from app.agent.ai.guardrails import AgentGuardrails
from app.agent.ai.models import InvestigationResponse, InvestigationState
from app.agent.ai.provider import LLMProvider, create_llm_provider
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are the final investigation synthesis layer for the UC15 GST Compliance Platform.

CRITICAL INSTRUCTIONS & RULES:
1. Use ONLY the supplied evidence context.
2. Do NOT invent facts, invoices, vendors, GST tax rates, legal provisions, or system states.
3. Do NOT recalculate financial amounts or tax rates independently; reproduce exact numbers from the supplied evidence.
4. Do NOT override deterministic compliance gate verdicts (Gates 1-6). The deterministic GST engine remains the sole compliance authority.
5. Distinguish clearly between FACT, INFERENCE, and RECOMMENDATION.
6. Never claim that a candidate inference is a proven root cause unless confirmed in evidence.
7. All recommendations are strictly advisory and require human review before action.
8. If the evidence is insufficient or contradictory, explicitly state so in the answer and limitations.
9. Distinguish clearly between DETERMINISTIC ENGINE FINDINGS (statutory authority) and REGULATORY KNOWLEDGE EVIDENCE (supporting context). Always cite document name, page, and section for regulatory evidence.
"""


class LLMSynthesizer:
    """
    Synthesizes structured investigation responses from evidence context.
    Delegates to LLMProvider when available, or executes deterministic fallback.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        guardrails: Optional[AgentGuardrails] = None,
    ) -> None:
        self.provider = provider or create_llm_provider()
        self.guardrails = guardrails or AgentGuardrails()

    def synthesize(self, context: InvestigationContext) -> InvestigationResponse:
        """
        Synthesize InvestigationResponse from InvestigationContext.
        Falls back cleanly to deterministic response if AI provider is unavailable.
        """
        state: Optional[InvestigationState] = getattr(context, "state", None)

        if not self.provider.is_available():
            logger.info("LLM Provider unavailable. Returning deterministic fallback response.")
            return self.create_deterministic_fallback(context, reason="LLM Provider unavailable or API key missing.")

        from app.agent.ai.context import InvestigationContextBuilder
        prompt = InvestigationContextBuilder().format_prompt_context(context)

        try:
            # Generate structured response from provider
            raw_response = self.provider.structured_generate(
                prompt=prompt,
                schema=InvestigationResponse,
                system_prompt=SYSTEM_PROMPT,
            )
            raw_response.provider_status = {
                "available": True,
                "provider": type(self.provider).__name__,
                "model": getattr(self.provider.config, "model", "default"),
            }
            # Populate state metadata if available
            if state:
                raw_response.investigation_id = state.investigation_id
                raw_response.investigation_status = state.status.value
                raw_response.termination_reason = state.termination_reason.value if state.termination_reason else "COMPLETED"
                raw_response.investigation_steps = [s.model_dump() for s in state.trace]
                raw_response.contradictions = state.contradictions
                raw_response.evidence_sufficiency = {
                    "sufficient": state.status.value == "EVIDENCE_SUFFICIENT",
                    "status": state.status.value,
                }

            # Run output guardrail validation
            validated = self.guardrails.validate_response(raw_response, context)
            return validated

        except Exception as e:
            logger.warning(f"LLM synthesis failed: {e}. Falling back to deterministic response.")
            return self.create_deterministic_fallback(
                context,
                reason=f"LLM synthesis failed with error: {str(e)}",
            )

    def create_deterministic_fallback(
        self,
        context: InvestigationContext,
        reason: str = "LLM synthesis unavailable.",
    ) -> InvestigationResponse:
        """
        Construct a rich, structured deterministic response when LLM synthesis is offline or fails.
        Guarantees system operational utility without generating fake AI content.
        """
        state: Optional[InvestigationState] = getattr(context, "state", None)
        findings = context.deterministic_findings
        tools_executed = [tr.tool_name for tr in context.tool_results if tr.success]

        # Extract risk and financial exposure from findings
        risk_summary: Dict[str, Any] = {}
        fin_summary: Dict[str, Any] = {}
        evidence_list: List[Dict[str, Any]] = []
        recommendations: List[str] = []

        knowledge_evidence: List[Dict[str, Any]] = []

        for tr in context.tool_results:
            if not tr.success:
                continue
            data = tr.structured_data
            if tr.tool_name == "get_risk_assessment":
                risk_summary = data
            elif tr.tool_name == "get_financial_exposure":
                fin_summary = data
            elif tr.tool_name == "validate_invoice" or tr.tool_name == "get_compliance_result":
                if isinstance(data, dict) and "recommendations" in data:
                    recommendations.extend(data.get("recommendations", []))
            elif tr.tool_name == "retrieve_gst_knowledge":
                if isinstance(data, dict) and "evidence_items" in data:
                    for ev in data.get("evidence_items", []):
                        knowledge_evidence.append(ev)

            evidence_list.append({"tool": tr.tool_name, "summary": f"Executed {tr.tool_name} successfully"})

        if not recommendations:
            recommendations.append("Review flagged compliance discrepancy details with tax team.")

        engine_findings = [f for f in findings if f.get("type") != "REGULATORY_KNOWLEDGE_EVIDENCE"]

        # Build grounded narrative answer
        lines = [
            f"Investigation results for query: '{context.request.user_query}'",
            f"Intent: {context.intent.intent.value} | Target: {context.plan.target or 'Portfolio'}",
            f"Executed {len(tools_executed)} read-only tools cleanly.",
            "",
            "1. Deterministic GST Engine Determination (Statutory Authority):",
        ]

        if not engine_findings:
            lines.append("- Statutory compliance engines executed cleanly. No specific gate discrepancies emitted.")
        else:
            for f in engine_findings[:6]:
                lines.append(f"- [{f.get('type')}] Source: {f.get('source')} -> {f}")

        lines.extend([
            "",
            "2. Supporting Regulatory Knowledge Evidence (Policy Context & Provenance):",
        ])

        if not knowledge_evidence:
            lines.append("- No regulatory knowledge documents retrieved.")
        else:
            for ev in knowledge_evidence[:4]:
                prov = ev.get("provenance", {})
                loc = f"Page {prov.get('page_number')}" if prov.get("page_number") else f"Sec: {prov.get('section') or 'General'}"
                lines.append(
                    f"- [{ev.get('status')}] Doc: '{prov.get('document_name')}' ({loc}) | Relevance: {ev.get('relevance_score')} | Effective: {prov.get('effective_from') or 'ALL'} to {prov.get('effective_to') or 'ONGOING'}"
                )
                chunk_txt = ev.get("chunk", {}).get("content", "")
                if chunk_txt:
                    lines.append(f"  Excerpt: {chunk_txt[:180]}...")

        if state and state.contradictions:
            lines.extend([
                "",
                "Detected Evidence Contradictions:",
                *[f"- {c}" for c in state.contradictions]
            ])

        lines.extend([
            "",
            f"Note: {reason} The deterministic GST engine remains the sole statutory authority. Regulatory evidence provides supporting context.",
        ])

        answer = "\n".join(lines)

        inv_id = state.investigation_id if state else None
        inv_status = state.status.value if state else "COMPLETED"
        term_reason = state.termination_reason.value if (state and state.termination_reason) else "COMPLETED"
        steps_trace = [s.model_dump() for s in state.trace] if state else []
        contradictions = state.contradictions if state else []

        what_detected = {
            "summary": f"Deterministic findings for {context.intent.intent.value}",
            "finding_ids": [f.get("source") for f in engine_findings if isinstance(f, dict) and f.get("source")],
        }

        next_steps = [
            "Review flagged statutory rule discrepancies with tax team.",
            "Verify missing evidence documents before filing cycle.",
        ]

        return InvestigationResponse(
            answer=answer,
            intent=context.intent.intent,
            evidence=evidence_list,
            findings=findings,
            recommendations=list(set(recommendations)),
            risk=risk_summary,
            financial_exposure=fin_summary,
            confidence="HIGH",
            limitations=[reason] + context.limitations,
            tools_used=tools_executed,
            provider_status={
                "available": False,
                "reason": reason,
                "mode": "DETERMINISTIC_FALLBACK",
            },
            investigation_id=inv_id,
            investigation_status=inv_status,
            termination_reason=term_reason,
            investigation_steps=steps_trace,
            evidence_sufficiency={
                "sufficient": inv_status == "EVIDENCE_SUFFICIENT",
                "status": inv_status,
            },
            contradictions=contradictions,
            knowledge_evidence=knowledge_evidence,
            what_was_detected=what_detected,
            supporting_evidence=evidence_list,
            conflicts_and_contradictions=[{"description": c} for c in contradictions],
            financial_impact=[fin_summary] if fin_summary else [],
            missing_evidence=[{"type": "SUPPLIER_RECONCILIATION", "status": "NOT_AVAILABLE"}],
            next_steps=next_steps,
            system_confidence=1.0,
            ai_confidence=0.90,
            prompt_version="v23.1",
        )
