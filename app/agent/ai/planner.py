"""
app.agent.ai.planner
====================
Controlled Investigation Planner for UC15 AI Investigation Agent (Sprint 12.1).
Maps classified InvestigationIntent into a safe, bounded InvestigationPlan containing only approved read-only tools.
Prevents execution of unauthorized or arbitrary tool calls.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from app.agent.ai.models import (
    InvestigationIntent,
    InvestigationIntentEnum,
    InvestigationPlan,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Controlled Mapping: Intent -> Allowed Tool Set
INTENT_TOOL_MAPPINGS: Dict[InvestigationIntentEnum, List[str]] = {
    InvestigationIntentEnum.INVOICE_INVESTIGATION: [
        "get_compliance_result",
        "get_risk_assessment",
        "validate_invoice",
        "get_financial_exposure",
        "retrieve_gst_knowledge",
        "find_duplicates",
        "find_anomalies",
        "investigate_root_cause",
        "get_blast_radius",
    ],
    InvestigationIntentEnum.COUNTERPARTY_INVESTIGATION: [
        "get_historical_patterns",
        "get_risk_assessment",
        "get_compliance_result",
        "get_financial_exposure",
        "retrieve_gst_knowledge",
        "find_duplicates",
        "find_anomalies",
        "investigate_root_cause",
        "get_blast_radius",
    ],
    InvestigationIntentEnum.RISK_ANALYSIS: [
        "get_risk_assessment",
        "get_compliance_result",
        "get_financial_exposure",
        "retrieve_gst_knowledge",
        "get_historical_patterns",
    ],
    InvestigationIntentEnum.FINANCIAL_EXPOSURE: [
        "get_financial_exposure",
        "get_risk_assessment",
        "get_historical_patterns",
        "get_compliance_result",
    ],
    InvestigationIntentEnum.HISTORICAL_ANALYSIS: [
        "get_historical_patterns",
        "get_compliance_result",
        "get_risk_assessment",
        "retrieve_gst_knowledge",
    ],
    InvestigationIntentEnum.DUPLICATE_ANALYSIS: [
        "find_duplicates",
        "get_compliance_result",
        "get_financial_exposure",
    ],
    InvestigationIntentEnum.ANOMALY_ANALYSIS: [
        "find_anomalies",
        "get_risk_assessment",
        "get_financial_exposure",
    ],
    InvestigationIntentEnum.ROOT_CAUSE_ANALYSIS: [
        "investigate_root_cause",
        "get_blast_radius",
        "get_compliance_result",
        "retrieve_gst_knowledge",
        "get_historical_patterns",
    ],
    InvestigationIntentEnum.BLAST_RADIUS_ANALYSIS: [
        "get_blast_radius",
        "investigate_root_cause",
        "get_financial_exposure",
        "get_risk_assessment",
    ],
    InvestigationIntentEnum.GENERAL_COMPLIANCE: [
        "get_compliance_result",
        "get_risk_assessment",
        "get_financial_exposure",
        "retrieve_gst_knowledge",
    ],
    InvestigationIntentEnum.REGULATORY_KNOWLEDGE: [
        "retrieve_gst_knowledge",
        "get_compliance_result",
        "get_risk_assessment",
    ],
}


class InvestigationPlanner:
    """
    Constructs bounded investigation plans.
    Strictly filters tool selection against pre-approved intent mappings.
    """

    def create_plan(self, intent_res: InvestigationIntent) -> InvestigationPlan:
        intent_type = intent_res.intent
        allowed_tools = INTENT_TOOL_MAPPINGS.get(intent_type, INTENT_TOOL_MAPPINGS[InvestigationIntentEnum.GENERAL_COMPLIANCE])

        target = intent_res.target_invoice_id or intent_res.target_counterparty

        reasoning = [
            f"Intent classified as {intent_type.value} with confidence {intent_res.confidence:.2f}.",
            f"Selected {len(allowed_tools)} approved read-only tools: {', '.join(allowed_tools)}.",
            f"Target entity: '{target}'." if target else "Broad portfolio search target.",
        ]

        constraints = [
            "READ_ONLY_EXECUTION",
            "STRICT_EVIDENCE_GROUNDING",
            "ZERO_ARBITRARY_TOOL_EXECUTION",
        ]

        logger.info(f"Planned {len(allowed_tools)} read-only tools for intent {intent_type.value}")

        return InvestigationPlan(
            intent=intent_type,
            required_tools=allowed_tools,
            target=target,
            reasoning_steps=reasoning,
            constraints=constraints,
        )
