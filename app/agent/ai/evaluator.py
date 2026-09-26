"""
app.agent.ai.evaluator
======================
Evidence Evaluator Engine for UC15 Controlled AI Agent (Sprint 12.2).
Evaluates accumulated investigation state to determine evidence sufficiency,
missing evidence dimensions, evidence contradictions, and recommended next tools.
Does NOT rely solely on LLM judgment; uses deterministic rules for sufficiency.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from app.agent.ai.models import (
    EvaluationStatusEnum,
    EvidenceEvaluation,
    InvestigationIntentEnum,
    InvestigationState,
    ToolResult,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Essential tool sets per intent for deterministic sufficiency
INTENT_REQUIRED_MINIMUM_TOOLS: Dict[InvestigationIntentEnum, List[str]] = {
    InvestigationIntentEnum.INVOICE_INVESTIGATION: ["get_compliance_result", "get_risk_assessment"],
    InvestigationIntentEnum.COUNTERPARTY_INVESTIGATION: ["get_historical_patterns"],
    InvestigationIntentEnum.RISK_ANALYSIS: ["get_risk_assessment"],
    InvestigationIntentEnum.FINANCIAL_EXPOSURE: ["get_financial_exposure"],
    InvestigationIntentEnum.HISTORICAL_ANALYSIS: ["get_historical_patterns"],
    InvestigationIntentEnum.DUPLICATE_ANALYSIS: ["find_duplicates"],
    InvestigationIntentEnum.ANOMALY_ANALYSIS: ["find_anomalies"],
    InvestigationIntentEnum.ROOT_CAUSE_ANALYSIS: ["investigate_root_cause"],
    InvestigationIntentEnum.BLAST_RADIUS_ANALYSIS: ["get_blast_radius"],
    InvestigationIntentEnum.GENERAL_COMPLIANCE: ["get_compliance_result"],
    InvestigationIntentEnum.REGULATORY_KNOWLEDGE: ["retrieve_gst_knowledge"],
}


class EvidenceEvaluator:
    """
    Evaluates evidence completeness and contradiction status during the investigation loop.
    Enforces deterministic completeness criteria.
    """

    def evaluate(self, state: InvestigationState) -> EvidenceEvaluation:
        intent = state.intent.intent
        executed = set(state.executed_tools)
        results_by_tool: Dict[str, ToolResult] = {tr.tool_name: tr for tr in state.tool_results if tr.success}

        missing_evidence: List[str] = []
        contradictions: List[str] = []
        recommended_next: List[str] = []

        # 1. Check essential minimum tools for intent
        min_tools = INTENT_REQUIRED_MINIMUM_TOOLS.get(intent, ["get_compliance_result"])
        for tool in min_tools:
            if tool not in executed:
                missing_evidence.append(f"Missing essential tool evidence: '{tool}'")
                if tool in state.initial_plan.required_tools:
                    recommended_next.append(tool)

        # 2. Intent-specific progressive evidence depth checks
        if intent == InvestigationIntentEnum.INVOICE_INVESTIGATION:
            # If compliance failure exists, check financial exposure
            risk_tr = results_by_tool.get("get_risk_assessment")
            comp_tr = results_by_tool.get("get_compliance_result") or results_by_tool.get("validate_invoice")
            
            if comp_tr and risk_tr:
                data_risk = risk_tr.structured_data
                data_comp = comp_tr.structured_data
                
                status_str = str(data_comp.get("status", "")).upper()
                score = float(data_risk.get("score", 0.0)) if isinstance(data_risk, dict) else 0.0
                
                if (status_str in ("NON_COMPLIANT", "NEEDS_REVIEW") or score >= 50.0) and "get_financial_exposure" not in executed:
                    missing_evidence.append("Invoice has compliance risk; financial exposure math is uncollected.")
                    if "get_financial_exposure" in state.initial_plan.required_tools:
                        recommended_next.append("get_financial_exposure")

                if (status_str in ("NON_COMPLIANT", "NEEDS_REVIEW") or score >= 50.0) and "retrieve_gst_knowledge" not in executed:
                    if "retrieve_gst_knowledge" in state.initial_plan.required_tools:
                        missing_evidence.append("Invoice has compliance discrepancy; statutory GST rule context is uncollected.")
                        recommended_next.append("retrieve_gst_knowledge")

                if (status_str == "NON_COMPLIANT" or score >= 70.0) and "investigate_root_cause" not in executed:
                    missing_evidence.append("Invoice has high severity non-compliance; root cause analysis is uncollected.")
                    if "investigate_root_cause" in state.initial_plan.required_tools:
                        recommended_next.append("investigate_root_cause")

        elif intent == InvestigationIntentEnum.COUNTERPARTY_INVESTIGATION:
            if "get_risk_assessment" not in executed and "get_risk_assessment" in state.initial_plan.required_tools:
                recommended_next.append("get_risk_assessment")

        elif intent == InvestigationIntentEnum.ROOT_CAUSE_ANALYSIS:
            if "get_blast_radius" not in executed and "get_blast_radius" in state.initial_plan.required_tools:
                missing_evidence.append("Root cause identified; blast radius ecosystem impact is uncollected.")
                recommended_next.append("get_blast_radius")

        # 3. Contradiction Detection
        # Check if Gate 1-6 claims COMPLIANT but Risk engine returned CRITICAL
        comp_tr = results_by_tool.get("get_compliance_result")
        risk_tr = results_by_tool.get("get_risk_assessment")
        if comp_tr and risk_tr:
            c_status = str(comp_tr.structured_data.get("status", "")).upper()
            r_level = str(risk_tr.structured_data.get("risk_level", "")).upper()
            if c_status == "COMPLIANT" and r_level in ("HIGH", "CRITICAL"):
                contradictions.append(
                    f"Contradiction detected: Statutory Gates yield COMPLIANT but Risk Score engine yields {r_level} risk level."
                )

        # 4. Determine overall sufficiency
        # Filter recommended_next to only allowed tools for intent that haven't been executed
        allowed_set = set(state.initial_plan.required_tools)
        recommended_next = [t for t in recommended_next if t in allowed_set and t not in executed]

        # Sufficiency verdict
        if contradictions:
            eval_status = EvaluationStatusEnum.CONFLICTING
            sufficient = False
            rationale = f"Contradictory evidence detected between deterministic engines ({len(contradictions)} conflicts)."
        elif missing_evidence and recommended_next:
            eval_status = EvaluationStatusEnum.INSUFFICIENT
            sufficient = False
            rationale = f"Insufficient evidence for intent '{intent.value}'. Missing: {', '.join(missing_evidence)}"
        else:
            eval_status = EvaluationStatusEnum.SUFFICIENT
            sufficient = True
            rationale = f"Sufficient deterministic evidence collected for intent '{intent.value}' across {len(executed)} tools."

        logger.info(f"Evidence evaluation for {state.investigation_id}: {eval_status.value} (Sufficient={sufficient})")

        return EvidenceEvaluation(
            status=eval_status,
            sufficient=sufficient,
            missing_evidence=missing_evidence,
            contradictions=contradictions,
            recommended_next_tools=recommended_next,
            rationale=rationale,
        )
