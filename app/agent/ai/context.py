"""
app.agent.ai.context
====================
Evidence-First Context Builder for UC15 AI Investigation Agent (Sprint 12.1).
Synthesizes structured outputs from executed read-only tools into a grounded InvestigationContext.
Ensures the LLM prompt receives deterministic facts (tax rates, exposure amounts, gate statuses, risk scores)
without relying on LLM recalculation.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from app.agent.ai.models import (
    InvestigationContext,
    InvestigationIntent,
    InvestigationPlan,
    InvestigationRequest,
    InvestigationState,
    ToolResult,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class InvestigationContextBuilder:
    """
    Assembles structured, evidence-grounded context payloads.
    Formats deterministic tool results for prompt synthesis without altering underlying facts.
    """

    def build_context(
        self,
        request: InvestigationRequest,
        intent: InvestigationIntent,
        plan: InvestigationPlan,
        tool_results: List[ToolResult],
        state: Optional[InvestigationState] = None,
    ) -> InvestigationContext:
        evidence: Dict[str, Any] = {}
        deterministic_findings: List[Dict[str, Any]] = []
        limitations: List[str] = []

        for tr in tool_results:
            if not tr.success:
                limitations.append(f"Tool '{tr.tool_name}' failed or produced no output: {', '.join(tr.errors)}")
                continue

            data = tr.structured_data
            evidence[tr.tool_name] = data

            # Extract key findings per tool
            if tr.tool_name == "validate_invoice" or tr.tool_name == "get_compliance_result":
                if isinstance(data, dict) and "status" in data:
                    deterministic_findings.append({
                        "source": tr.tool_name,
                        "type": "COMPLIANCE_STATUS",
                        "invoice_no": data.get("invoice_no"),
                        "status": data.get("status"),
                        "failed_gates": data.get("failed_gate_count", 0),
                        "justification": data.get("justification"),
                    })
                elif isinstance(data, list):
                    for item in data[:5]:
                        if isinstance(item, dict):
                            deterministic_findings.append({
                                "source": tr.tool_name,
                                "type": "COMPLIANCE_STATUS",
                                "invoice_no": item.get("invoice_no"),
                                "status": item.get("status"),
                            })

            elif tr.tool_name == "get_risk_assessment":
                if isinstance(data, dict):
                    deterministic_findings.append({
                        "source": tr.tool_name,
                        "type": "RISK_PROFILE",
                        "score": data.get("risk_score") or data.get("average_risk_score"),
                        "level": data.get("risk_level") or data.get("by_level"),
                        "priority": data.get("priority") or data.get("by_priority"),
                    })

            elif tr.tool_name == "get_financial_exposure":
                if isinstance(data, dict):
                    deterministic_findings.append({
                        "source": tr.tool_name,
                        "type": "FINANCIAL_EXPOSURE",
                        "total_exposure": data.get("total_potential_exposure") or data.get("potential_exposure"),
                        "impact_type": data.get("impact_type"),
                    })

            elif tr.tool_name == "find_duplicates":
                if isinstance(data, dict) and "duplicate_candidates" in data:
                    cands = data.get("duplicate_candidates", [])
                    if cands:
                        deterministic_findings.append({
                            "source": tr.tool_name,
                            "type": "DUPLICATE_CANDIDATES",
                            "candidate_count": len(cands),
                            "top_candidate": cands[0] if isinstance(cands[0], dict) else str(cands[0]),
                        })

            elif tr.tool_name == "find_anomalies":
                if isinstance(data, dict) and "anomaly_findings" in data:
                    anom = data.get("anomaly_findings", [])
                    if anom:
                        deterministic_findings.append({
                            "source": tr.tool_name,
                            "type": "ANOMALY_FINDINGS",
                            "finding_count": len(anom),
                            "top_anomaly": anom[0] if isinstance(anom[0], dict) else str(anom[0]),
                        })

            elif tr.tool_name == "investigate_root_cause":
                if isinstance(data, dict) and "root_cause_candidates" in data:
                    rcs = data.get("root_cause_candidates", [])
                    if rcs:
                        deterministic_findings.append({
                            "source": tr.tool_name,
                            "type": "ROOT_CAUSE_CANDIDATE",
                            "primary_rc": rcs[0] if isinstance(rcs[0], dict) else str(rcs[0]),
                        })

            elif tr.tool_name == "retrieve_gst_knowledge":
                if isinstance(data, dict):
                    items = data.get("evidence_items", [])
                    for item in items:
                        prov = item.get("provenance", {})
                        deterministic_findings.append({
                            "source": "retrieve_gst_knowledge",
                            "type": "REGULATORY_KNOWLEDGE_EVIDENCE",
                            "document_name": prov.get("document_name"),
                            "page_number": prov.get("page_number"),
                            "section": prov.get("section"),
                            "status": item.get("status"),
                            "relevance_score": item.get("relevance_score"),
                            "effective_from": prov.get("effective_from"),
                            "effective_to": prov.get("effective_to"),
                        })

        return InvestigationContext(
            request=request,
            intent=intent,
            plan=plan,
            tool_results=tool_results,
            evidence=evidence,
            deterministic_findings=deterministic_findings,
            limitations=limitations,
            state=state,
        )

    def format_prompt_context(self, ctx: InvestigationContext) -> str:
        """Format the InvestigationContext into a clean markdown evidence document for the LLM."""
        lines = [
            f"# INVESTIGATION EVIDENCE CONTEXT",
            f"User Query: {ctx.request.user_query}",
            f"Classified Intent: {ctx.intent.intent.value} (Confidence: {ctx.intent.confidence:.2f})",
            f"Target Entity: {ctx.plan.target or 'Portfolio/General'}",
            "",
            "## DETERMINISTIC ENGINE EVIDENCE (STATUTORY SOURCE OF TRUTH)",
        ]

        engine_findings = [f for f in ctx.deterministic_findings if f.get("type") != "REGULATORY_KNOWLEDGE_EVIDENCE"]
        knowledge_findings = [f for f in ctx.deterministic_findings if f.get("type") == "REGULATORY_KNOWLEDGE_EVIDENCE"]

        if not engine_findings:
            lines.append("No specific deterministic statutory findings emitted by tools.")
        else:
            for idx, f in enumerate(engine_findings, 1):
                lines.append(f"{idx}. [{f.get('type')}] Source: {f.get('source')} | Details: {f}")

        lines.extend(["", "## REGULATORY KNOWLEDGE EVIDENCE (SUPPORTING EXPLANATION & CONTEXT)"])
        if not knowledge_findings:
            lines.append("No statutory knowledge documents retrieved for query.")
        else:
            for idx, k in enumerate(knowledge_findings, 1):
                lines.append(
                    f"{idx}. [{k.get('status')}] Doc: '{k.get('document_name')}' | Loc: Page {k.get('page_number') or 'N/A'}, Sec: {k.get('section') or 'General'} | Relevance: {k.get('relevance_score')} | Effective: {k.get('effective_from')} to {k.get('effective_to') or 'ONGOING'}"
                )

        lines.extend(["", "## RAW TOOL EVIDENCE PAYLOADS"])
        for tr in ctx.tool_results:
            status_str = "SUCCESS" if tr.success else "FAILED"
            lines.append(f"### Tool: {tr.tool_name} [{status_str}]")
            if tr.success:
                lines.append(f"Data: {tr.structured_data}")
            else:
                lines.append(f"Errors: {', '.join(tr.errors)}")

        if ctx.limitations:
            lines.extend(["", "## ANALYSIS LIMITATIONS"])
            for lim in ctx.limitations:
                lines.append(f"- {lim}")

        return "\n".join(lines)
