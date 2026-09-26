"""
app.agent.ai.selector
=====================
Controlled Tool Selector for UC15 Agentic Investigation Loop (Sprint 12.2).
Selects the next investigation action using deterministic-first rules,
with optional schema-validated LLM guidance.
Strictly enforces intent allow-lists, read-only guarantees, and budget constraints.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from app.agent.ai.evaluator import EvidenceEvaluator
from app.agent.ai.guardrails import AgentGuardrails, GuardrailValidationError
from app.agent.ai.models import (
    EvidenceEvaluation,
    InvestigationState,
    NextInvestigationAction,
)
from app.agent.ai.provider import LLMProvider
from app.agent.ai.registry import ToolRegistry
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

SELECTOR_SYSTEM_PROMPT = """You are an AI Investigation Selector for the UC15 GST Compliance Platform.
Given the current investigation state and available allowed tools, determine the NEXT SINGLE read-only action.

RULES:
1. Select ONLY from the provided allowed_tools list.
2. Do NOT invent new tool names.
3. If evidence is sufficient or no more relevant tools are needed, return action='FINISH'.
4. Do NOT request mutating, filing, or posting actions.
"""


class ControlledToolSelector:
    """
    Selects the next action during an investigation loop.
    Enforces deterministic-first selection with schema-validated LLM fallback.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        guardrails: Optional[AgentGuardrails] = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.guardrails = guardrails or AgentGuardrails(self.registry)
        self.evaluator = EvidenceEvaluator()

    def select_next_action(
        self,
        state: InvestigationState,
        evaluation: EvidenceEvaluation,
        provider: Optional[LLMProvider] = None,
    ) -> NextInvestigationAction:
        """
        Determine the next investigation action.
        Returns NextInvestigationAction(action="CALL_TOOL" | "FINISH", ...).
        """
        executed = set(state.executed_tools)
        allowed_tools = [t for t in state.initial_plan.required_tools if t not in executed]

        # 1. Termination checks
        if evaluation.sufficient or not allowed_tools or state.current_step >= state.budget.max_steps:
            reason = (
                "Evidence is sufficient."
                if evaluation.sufficient
                else ("No further unexecuted allowed tools remain." if not allowed_tools else "Maximum step budget reached.")
            )
            return NextInvestigationAction(
                action="FINISH",
                reason=reason,
                confidence=1.0,
            )

        # 2. Deterministic-First Selection
        if evaluation.recommended_next_tools:
            for rec_tool in evaluation.recommended_next_tools:
                if rec_tool in allowed_tools:
                    # Construct appropriate target arguments
                    args: Dict[str, Any] = {}
                    if state.target and state.target.startswith("INV-"):
                        args["invoice_no"] = state.target
                    
                    logger.info(f"Deterministic selector picked tool '{rec_tool}' for state {state.investigation_id}")
                    return NextInvestigationAction(
                        action="CALL_TOOL",
                        tool_name=rec_tool,
                        arguments=args,
                        reason=f"Deterministic rule recommended '{rec_tool}' to satisfy missing evidence.",
                        confidence=1.0,
                    )

        # 3. Fallback: Select first unexecuted tool from allowed_tools deterministically
        if allowed_tools:
            next_tool = allowed_tools[0]
            args = {}
            if state.target and state.target.startswith("INV-"):
                args["invoice_no"] = state.target

            # 4. If LLM provider is available, request LLM guidance, but validate strictly
            if provider and provider.is_available():
                try:
                    prompt = (
                        f"Query: '{state.request.user_query}'\n"
                        f"Intent: {state.intent.intent.value}\n"
                        f"Target: {state.target or 'Portfolio'}\n"
                        f"Executed Tools: {list(executed)}\n"
                        f"Allowed Unexecuted Tools: {allowed_tools}\n"
                        f"Missing Evidence: {evaluation.missing_evidence}\n"
                        f"Select the single best next tool from {allowed_tools} or FINISH."
                    )
                    llm_action = provider.structured_generate(
                        prompt=prompt,
                        schema=NextInvestigationAction,
                        system_prompt=SELECTOR_SYSTEM_PROMPT,
                    )
                    # Validate LLM action
                    if llm_action.action == "CALL_TOOL" and llm_action.tool_name:
                        valid_tool = self._validate_tool_action(llm_action.tool_name, state)
                        if valid_tool:
                            if not llm_action.arguments and state.target and state.target.startswith("INV-"):
                                llm_action.arguments = {"invoice_no": state.target}
                            logger.info(f"LLM selector suggested valid tool '{llm_action.tool_name}' for state {state.investigation_id}")
                            return llm_action
                        logger.warning(f"LLM suggested invalid tool '{llm_action.tool_name}'. Falling back to deterministic tool '{next_tool}'.")
                    elif llm_action.action == "FINISH":
                        return llm_action
                except Exception as e:
                    logger.warning(f"LLM next-action selection failed: {e}. Falling back to deterministic tool selection.")

            # Return deterministic next tool
            logger.info(f"Selector fallback picked tool '{next_tool}' for state {state.investigation_id}")
            return NextInvestigationAction(
                action="CALL_TOOL",
                tool_name=next_tool,
                arguments=args,
                reason=f"Deterministic fallback selected next allowed tool '{next_tool}'.",
                confidence=0.90,
            )

        return NextInvestigationAction(action="FINISH", reason="No further tools available.", confidence=1.0)

    def _validate_tool_action(self, tool_name: str, state: InvestigationState) -> bool:
        """Verify tool exists, is read-only, is allowed for intent, and not executed."""
        tool_def = self.registry.get(tool_name)
        if not tool_def or not tool_def.read_only:
            return False
        if tool_name not in state.initial_plan.required_tools:
            return False
        if tool_name in state.executed_tools:
            return False
        return True
