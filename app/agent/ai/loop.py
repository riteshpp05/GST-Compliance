"""
app.agent.ai.loop
=================
Bounded Agentic Investigation Loop Engine for UC15 (Sprint 12.2).
Orchestrates step-by-step investigation loop across Intent -> Initial Plan -> Tool Execution ->
Evidence Evaluation -> Next Tool Selection -> Synthesis.
Strictly enforces execution budget limits (max steps, max tool calls, execution timeout).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.agent.ai.evaluator import EvidenceEvaluator
from app.agent.ai.executor import ToolExecutor
from app.agent.ai.guardrails import AgentGuardrails
from app.agent.ai.models import (
    EvaluationStatusEnum,
    EvidenceEvaluation,
    InvestigationBudget,
    InvestigationIntent,
    InvestigationPlan,
    InvestigationRequest,
    InvestigationState,
    InvestigationStatusEnum,
    NextInvestigationAction,
    TerminationReasonEnum,
    ToolResult,
    TraceStep,
)
from app.agent.ai.provider import LLMProvider
from app.agent.ai.registry import ToolRegistry
from app.agent.ai.selector import ControlledToolSelector
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class InvestigationLoopEngine:
    """
    Orchestrates bounded investigation loop execution.
    Appends trace steps, accumulates evidence, and checks termination criteria.
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        executor: Optional[ToolExecutor] = None,
        evaluator: Optional[EvidenceEvaluator] = None,
        selector: Optional[ControlledToolSelector] = None,
        guardrails: Optional[AgentGuardrails] = None,
    ) -> None:
        self.registry = registry or ToolRegistry()
        self.executor = executor or ToolExecutor(registry=self.registry)
        self.evaluator = evaluator or EvidenceEvaluator()
        self.selector = selector or ControlledToolSelector(registry=self.registry, guardrails=guardrails)
        self.guardrails = guardrails or AgentGuardrails(registry=self.registry)

    def initialize_state(
        self,
        request: InvestigationRequest,
        intent: InvestigationIntent,
        plan: InvestigationPlan,
    ) -> InvestigationState:
        """Construct initial InvestigationState and record step 1 trace."""
        target = intent.target_invoice_id or intent.target_counterparty or request.invoice_no or request.counterparty
        budget = request.budget or InvestigationBudget()

        state = InvestigationState(
            request=request,
            intent=intent,
            target=target,
            initial_plan=plan,
            budget=budget,
            status=InvestigationStatusEnum.INITIALIZED,
        )

        # Initial trace step 1: Intent & Planning
        state.trace.append(
            TraceStep(
                step_number=1,
                action_type="INTENT_AND_PLANNING",
                tool_name=None,
                arguments={},
                result_summary=(
                    f"Classified intent '{intent.intent.value}' (Confidence: {intent.confidence:.2f}). "
                    f"Target: '{target or 'Portfolio'}'. Approved tools: {plan.required_tools}."
                ),
                status="SUCCESS",
                execution_time_ms=5.0,
            )
        )

        logger.info(f"Initialized investigation state {state.investigation_id} for intent '{intent.intent.value}'")
        return state

    def run_loop(
        self,
        state: InvestigationState,
        provider: Optional[LLMProvider] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationState:
        """
        Execute bounded agentic loop iterations over InvestigationState.
        """
        state.status = InvestigationStatusEnum.INVESTIGATING
        start_time = time.perf_counter()

        logger.info(f"Starting investigation loop {state.investigation_id} with budget {state.budget}")

        while state.current_step < state.budget.max_steps and len(state.executed_tools) < state.budget.max_tool_calls:
            # 1. Timeout Check
            elapsed_sec = time.perf_counter() - start_time
            if elapsed_sec >= state.budget.max_execution_time_seconds:
                logger.warning(f"Investigation {state.investigation_id} timed out after {elapsed_sec:.2f}s")
                state.status = InvestigationStatusEnum.BUDGET_EXHAUSTED
                state.termination_reason = TerminationReasonEnum.TIMEOUT
                state.trace.append(
                    TraceStep(
                        step_number=len(state.trace) + 1,
                        action_type="TIMEOUT_TERMINATION",
                        result_summary=f"Investigation timed out after {elapsed_sec:.2f} seconds (Max: {state.budget.max_execution_time_seconds}s).",
                        status="TIMEOUT",
                    )
                )
                break

            state.current_step += 1
            step_start = time.perf_counter()

            # 2. Evidence Evaluation
            evaluation = self.evaluator.evaluate(state)
            if evaluation.contradictions:
                for c in evaluation.contradictions:
                    if c not in state.contradictions:
                        state.contradictions.append(c)

            if evaluation.sufficient:
                logger.info(f"Evidence sufficient at step {state.current_step} for {state.investigation_id}")
                state.status = InvestigationStatusEnum.EVIDENCE_SUFFICIENT
                state.termination_reason = TerminationReasonEnum.SUFFICIENT_EVIDENCE
                state.trace.append(
                    TraceStep(
                        step_number=len(state.trace) + 1,
                        action_type="EVIDENCE_EVALUATION",
                        result_summary=f"Evidence evaluated as SUFFICIENT. {evaluation.rationale}",
                        status="SUCCESS",
                        execution_time_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
                    )
                )
                break

            # 3. Next Tool Selection
            next_action = self.selector.select_next_action(state, evaluation, provider)

            if next_action.action == "FINISH":
                logger.info(f"Selector ordered FINISH at step {state.current_step} for {state.investigation_id}")
                if state.current_step >= state.budget.max_steps and not evaluation.sufficient:
                    state.status = InvestigationStatusEnum.BUDGET_EXHAUSTED
                    state.termination_reason = TerminationReasonEnum.MAX_STEPS_REACHED
                else:
                    state.status = (
                        InvestigationStatusEnum.EVIDENCE_SUFFICIENT
                        if evaluation.sufficient
                        else InvestigationStatusEnum.EVIDENCE_INSUFFICIENT
                    )
                    state.termination_reason = (
                        TerminationReasonEnum.SUFFICIENT_EVIDENCE
                        if evaluation.sufficient
                        else TerminationReasonEnum.NO_MORE_ALLOWED_TOOLS
                    )
                state.trace.append(
                    TraceStep(
                        step_number=len(state.trace) + 1,
                        action_type="LOOP_TERMINATION",
                        result_summary=f"Selector ordered termination: {next_action.reason}",
                        status="SUCCESS",
                        execution_time_ms=round((time.perf_counter() - step_start) * 1000.0, 2),
                    )
                )
                break

            # 4. Tool Execution
            tool_name = next_action.tool_name
            if not tool_name:
                break

            logger.info(f"Step {state.current_step}: Executing tool '{tool_name}' args={next_action.arguments}")
            tool_res = self.executor.execute_tool(tool_name, principal=principal, **next_action.arguments)
            step_elapsed_ms = round((time.perf_counter() - step_start) * 1000.0, 2)

            state.executed_tools.append(tool_name)
            state.tool_results.append(tool_res)

            # Accumulate findings and structured evidence
            if tool_res.success:
                s_data = tool_res.structured_data
                state.accumulated_evidence[tool_name] = s_data
                state.findings.append({
                    "tool_name": tool_name,
                    "type": "DETERMINISTIC_FINDING",
                    "data": s_data,
                })
                summary_text = f"Tool '{tool_name}' executed cleanly in {tool_res.execution_time_ms:.1f}ms."
            else:
                summary_text = f"Tool '{tool_name}' execution failed: {tool_res.errors}"

            state.trace.append(
                TraceStep(
                    step_number=len(state.trace) + 1,
                    action_type="TOOL_EXECUTION",
                    tool_name=tool_name,
                    arguments=next_action.arguments,
                    result_summary=summary_text,
                    status="SUCCESS" if tool_res.success else "ERROR",
                    execution_time_ms=step_elapsed_ms,
                )
            )

        # 5. Final Budget Exhaustion Check
        if state.status == InvestigationStatusEnum.INVESTIGATING:
            if len(state.executed_tools) >= state.budget.max_tool_calls:
                state.status = InvestigationStatusEnum.BUDGET_EXHAUSTED
                state.termination_reason = TerminationReasonEnum.MAX_TOOL_CALLS_REACHED
            else:
                state.status = InvestigationStatusEnum.BUDGET_EXHAUSTED
                state.termination_reason = TerminationReasonEnum.MAX_STEPS_REACHED

            state.trace.append(
                TraceStep(
                    step_number=len(state.trace) + 1,
                    action_type="BUDGET_EXHAUSTED",
                    result_summary=f"Investigation reached budget limit ({state.termination_reason.value}).",
                    status="WARNING",
                )
            )

        state.completed_at = datetime.now(timezone.utc).isoformat()
        logger.info(f"Investigation loop {state.investigation_id} finished: Status={state.status.value}, Reason={state.termination_reason.value if state.termination_reason else 'NONE'}")
        return state
