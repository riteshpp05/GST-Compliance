"""
app.agent.ai
============
Controlled AI Investigation Agent Package for UC15 (Sprint 12.1).
Exposes structured domain models, LLM provider abstraction, read-only tool registry,
intent detection, planning, tool execution, evidence context building, guardrails,
and main AIInvestigationAgent facade.
"""

from app.agent.ai.evaluator import EvidenceEvaluator
from app.agent.ai.loop import InvestigationLoopEngine
from app.agent.ai.models import (
    EvaluationStatusEnum,
    EvidenceEvaluation,
    InvestigationBudget,
    InvestigationContext,
    InvestigationIntent,
    InvestigationIntentEnum,
    InvestigationPlan,
    InvestigationRequest,
    InvestigationResponse,
    InvestigationState,
    InvestigationStatusEnum,
    NextInvestigationAction,
    TerminationReasonEnum,
    ToolResult,
    TraceStep,
)
from app.agent.ai.orchestrator import AIInvestigationAgent
from app.agent.ai.provider import (
    DisabledProvider,
    LLMConfig,
    LLMProvider,
    LLMProviderUnavailableError,
    MockProvider,
    OpenAIProvider,
    create_llm_provider,
)
from app.agent.ai.registry import ToolDefinition, ToolRegistry
from app.agent.ai.selector import ControlledToolSelector

__all__ = [
    "AIInvestigationAgent",
    "InvestigationRequest",
    "InvestigationResponse",
    "InvestigationIntent",
    "InvestigationIntentEnum",
    "InvestigationPlan",
    "InvestigationContext",
    "ToolResult",
    "InvestigationStatusEnum",
    "TerminationReasonEnum",
    "EvaluationStatusEnum",
    "InvestigationBudget",
    "TraceStep",
    "EvidenceEvaluation",
    "NextInvestigationAction",
    "InvestigationState",
    "EvidenceEvaluator",
    "ControlledToolSelector",
    "InvestigationLoopEngine",
    "ToolDefinition",
    "ToolRegistry",
    "LLMProvider",
    "LLMConfig",
    "OpenAIProvider",
    "DisabledProvider",
    "MockProvider",
    "create_llm_provider",
    "LLMProviderUnavailableError",
]
