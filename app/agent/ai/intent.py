"""
app.agent.ai.intent
===================
Deterministic-First Intent Classifier for UC15 AI Investigation Agent (Sprint 12.1).
Classifies structured user investigation requests into controlled InvestigationIntentEnum values.
Uses regex pattern matching and keyword heuristics first, with optional structured LLM fallback.
"""

from __future__ import annotations

import re
from typing import Optional
from app.agent.ai.models import (
    InvestigationIntent,
    InvestigationIntentEnum,
    InvestigationRequest,
)
from app.agent.ai.provider import LLMProvider
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Pattern for standard invoice numbers
INVOICE_ID_PATTERN = re.compile(r"\b(INV-[A-Z0-9-]+|INV-?\d{4,8})\b", re.IGNORECASE)


class DeterministicIntentDetector:
    """
    Classifies user investigation intent using deterministic rules first.
    Ensures fast, predictable execution without relying on an LLM for simple queries.
    """

    def detect_intent(
        self,
        request: InvestigationRequest,
        provider: Optional[LLMProvider] = None,
    ) -> InvestigationIntent:
        query_raw = request.user_query.strip()
        query_lower = query_raw.lower()

        # Extract target invoice ID from request or query
        target_inv = request.invoice_no
        if not target_inv:
            match = INVOICE_ID_PATTERN.search(query_raw)
            if match:
                target_inv = match.group(1).upper()

        target_cp = request.counterparty

        # 1. Invoice Specific Investigation
        if target_inv and ("why" in query_lower or "investigate" in query_lower or "non-compliant" in query_lower or "status" in query_lower):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.INVOICE_INVESTIGATION,
                confidence=1.0,
                explanation=f"Invoice ID '{target_inv}' explicitly identified in request.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 2. Counterparty Investigation
        if ("vendor" in query_lower or "supplier" in query_lower or "counterparty" in query_lower or target_cp) and not target_inv:
            return InvestigationIntent(
                intent=InvestigationIntentEnum.COUNTERPARTY_INVESTIGATION,
                confidence=0.95,
                explanation="Counterparty focus detected in user query.",
                target_invoice_id=None,
                target_counterparty=target_cp or "DETECTED_VENDOR",
            )

        # 3. Financial Exposure Analysis
        if any(k in query_lower for k in ("exposure", "financial", "monetary", "tax difference", "itc exposure", "amount at risk", "biggest loss")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.FINANCIAL_EXPOSURE,
                confidence=0.95,
                explanation="Financial exposure analysis keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 4. Duplicate Analysis
        if any(k in query_lower for k in ("duplicate", "identical", "double bill", "copy", "levenshtein")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.DUPLICATE_ANALYSIS,
                confidence=0.95,
                explanation="Duplicate analysis keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 5. Anomaly Analysis
        if any(k in query_lower for k in ("anomaly", "anomalies", "outlier", "unusual", "spike", "z-score", "mad", "iqr")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.ANOMALY_ANALYSIS,
                confidence=0.95,
                explanation="Statistical anomaly keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 6. Root Cause Analysis
        if any(k in query_lower for k in ("root cause", "systemic reason", "underlying cause", "why are invoices failing")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.ROOT_CAUSE_ANALYSIS,
                confidence=0.95,
                explanation="Root cause analysis keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 7. Blast Radius Analysis
        if any(k in query_lower for k in ("blast radius", "affected invoices", "scope of impact", "how widespread")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.BLAST_RADIUS_ANALYSIS,
                confidence=0.95,
                explanation="Blast radius analysis keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 8. Historical & Trend Analysis
        if any(k in query_lower for k in ("history", "historical", "trend", "recurring", "monthly pattern")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.HISTORICAL_ANALYSIS,
                confidence=0.95,
                explanation="Historical time-series keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 9. Regulatory Knowledge Query
        if any(k in query_lower for k in ("rule", "notification", "circular", "section", "policy", "law", "provision", "exemption", "gst rule", "what gst rule", "what rule")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.REGULATORY_KNOWLEDGE,
                confidence=0.95,
                explanation="Regulatory and GST knowledge query detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 10. Risk Analysis
        if any(k in query_lower for k in ("risk", "risky", "priority", "score", "p1", "p2", "critical risk")):
            return InvestigationIntent(
                intent=InvestigationIntentEnum.RISK_ANALYSIS,
                confidence=0.90,
                explanation="Risk scoring keywords detected.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 10. Fallback with invoice ID
        if target_inv:
            return InvestigationIntent(
                intent=InvestigationIntentEnum.INVOICE_INVESTIGATION,
                confidence=0.90,
                explanation=f"Target invoice ID '{target_inv}' identified in query.",
                target_invoice_id=target_inv,
                target_counterparty=target_cp,
            )

        # 11. Optional LLM fallback if provider is available
        if provider and provider.is_available():
            try:
                sys_prompt = "You are an intent classifier for a GST compliance system. Classify the user query into one of: " + ", ".join([e.value for e in InvestigationIntentEnum])
                res = provider.structured_generate(query_raw, InvestigationIntent, system_prompt=sys_prompt)
                res.target_invoice_id = target_inv
                res.target_counterparty = target_cp
                return res
            except Exception as e:
                logger.warning(f"LLM intent classification fallback failed: {e}")

        # Default fallback
        return InvestigationIntent(
            intent=InvestigationIntentEnum.GENERAL_COMPLIANCE,
            confidence=0.70,
            explanation="General GST compliance query.",
            target_invoice_id=target_inv,
            target_counterparty=target_cp,
        )
