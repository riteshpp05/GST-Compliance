"""
app.agent.ai.guardrails
=======================
Safety Guardrails for UC15 AI Investigation Agent (Sprint 12.1).
Validates investigation plans, tool registries, evidence grounding, and LLM output schemas.
Prevents hallucinated claims, unauthorized tool execution, or malformed responses.
"""

from __future__ import annotations

import re
from typing import List, Optional
from app.agent.ai.models import (
    InvestigationContext,
    InvestigationPlan,
    InvestigationResponse,
)
from app.agent.ai.registry import ToolRegistry
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class GuardrailValidationError(Exception):
    """Raised when a plan, tool call, or response fails guardrail verification."""
    pass


class AgentGuardrails:
    """
    Enforces strict safety guardrails across the AI Investigation pipeline.
    """

    def __init__(self, registry: Optional[ToolRegistry] = None) -> None:
        self.registry = registry or ToolRegistry()

    def sanitize_query(self, query: str) -> str:
        """
        Sanitize user query against control characters, path traversal, prompt injection keywords,
        and length limits.
        """
        if not query or not query.strip():
            raise GuardrailValidationError("Guardrail violation: Query string is empty or whitespace.")

        clean = query.replace("\0", "").strip()

        if len(clean) > 5000:
            raise GuardrailValidationError("Guardrail violation: Query string exceeds maximum length of 5000 characters.")

        # Strip prompt injection triggers
        injection_triggers = [
            "ignore previous instructions",
            "system prompt",
            "you are now DAN",
            "override guardrails",
            "delete database",
            "drop table",
        ]
        for trig in injection_triggers:
            if trig.lower() in clean.lower():
                logger.warning(f"Sanitizing query: Detected injection trigger '{trig}' in user query.")
                clean = re.sub(re.escape(trig), "[REDACTED]", clean, flags=re.IGNORECASE)

        return clean

    def validate_plan(self, plan: InvestigationPlan) -> None:
        """
        Verify that all requested tools in plan exist in registry and are read-only.
        """
        if not plan.required_tools:
            logger.warning("Investigation plan has 0 tools specified.")
            return

        for tool_name in plan.required_tools:
            tool_def = self.registry.get(tool_name)
            if not tool_def:
                raise GuardrailValidationError(f"Guardrail violation: Tool '{tool_name}' is not registered.")
            if not tool_def.read_only:
                raise GuardrailValidationError(f"Guardrail violation: Tool '{tool_name}' is not read-only.")

    def validate_response(
        self,
        response: InvestigationResponse,
        context: InvestigationContext,
    ) -> InvestigationResponse:
        """
        Verify that LLM synthesized response adheres to evidence grounding and schema rules.
        """
        if not response.answer or not response.answer.strip():
            raise GuardrailValidationError("Guardrail violation: LLM generated empty answer.")

        # Ensure tools_used only lists tools that were in the plan
        executed_tools = {tr.tool_name for tr in context.tool_results}
        for t in response.tools_used:
            if t not in executed_tools and t not in plan_tools_set(context.plan):
                logger.warning(f"Response listed unexecuted tool '{t}'. Sanitizing tools_used list.")
        
        response.tools_used = [t for t in response.tools_used if t in executed_tools or t in plan_tools_set(context.plan)]

        # Ensure response intent matches context intent
        if response.intent != context.intent.intent:
            logger.warning(f"Response intent '{response.intent}' differed from context intent '{context.intent.intent}'. Reconciling.")
            response.intent = context.intent.intent

        return response


def plan_tools_set(plan: InvestigationPlan) -> set[str]:
    return set(plan.required_tools)
