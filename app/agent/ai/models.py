"""
app.agent.ai.models
===================
Pydantic domain models for the Controlled AI Investigation Agent (Sprint 12.1 & 12.2).
Provides strictly typed, serializable structures across requests, intents, plans,
tool execution results, investigation state, budget limits, trace steps,
evidence evaluations, next actions, and synthesized investigation responses.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class InvestigationIntentEnum(str, Enum):
    """Controlled taxonomy of supported investigation intents."""
    INVOICE_INVESTIGATION = "INVOICE_INVESTIGATION"
    COUNTERPARTY_INVESTIGATION = "COUNTERPARTY_INVESTIGATION"
    RISK_ANALYSIS = "RISK_ANALYSIS"
    FINANCIAL_EXPOSURE = "FINANCIAL_EXPOSURE"
    HISTORICAL_ANALYSIS = "HISTORICAL_ANALYSIS"
    DUPLICATE_ANALYSIS = "DUPLICATE_ANALYSIS"
    ANOMALY_ANALYSIS = "ANOMALY_ANALYSIS"
    ROOT_CAUSE_ANALYSIS = "ROOT_CAUSE_ANALYSIS"
    BLAST_RADIUS_ANALYSIS = "BLAST_RADIUS_ANALYSIS"
    GENERAL_COMPLIANCE = "GENERAL_COMPLIANCE"
    REGULATORY_KNOWLEDGE = "REGULATORY_KNOWLEDGE"


class InvestigationStatusEnum(str, Enum):
    """Lifecycle statuses for bounded agentic investigation."""
    INITIALIZED = "INITIALIZED"
    INVESTIGATING = "INVESTIGATING"
    EVIDENCE_SUFFICIENT = "EVIDENCE_SUFFICIENT"
    EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"
    EVIDENCE_CONFLICTING = "EVIDENCE_CONFLICTING"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


class TerminationReasonEnum(str, Enum):
    """Explicit termination criteria for investigation loop."""
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    NO_MORE_ALLOWED_TOOLS = "NO_MORE_ALLOWED_TOOLS"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"
    MAX_TOOL_CALLS_REACHED = "MAX_TOOL_CALLS_REACHED"
    TIMEOUT = "TIMEOUT"
    TOOL_FAILURE = "TOOL_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EvaluationStatusEnum(str, Enum):
    """Result status from EvidenceEvaluator."""
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT = "INSUFFICIENT"
    CONFLICTING = "CONFLICTING"
    UNAVAILABLE = "UNAVAILABLE"


class InvestigationBudget(BaseModel):
    """Configurable execution budget limits for an investigation loop."""
    max_steps: int = Field(5, ge=1, le=20, description="Maximum loop iterations.")
    max_tool_calls: int = Field(7, ge=1, le=30, description="Maximum total tool executions.")
    max_execution_time_seconds: float = Field(20.0, ge=0.001, le=120.0, description="Execution timeout budget in seconds.")


class InvestigationRequest(BaseModel):
    """Structured user investigation request."""
    user_query: str = Field("", description="Natural language investigation query from user.")
    query: Optional[str] = Field(None, description="Alias query parameter.")
    invoice_no: Optional[str] = Field(None, description="Optional target invoice number (e.g. INV-8000001).")
    invoice_id: Optional[str] = Field(None, description="Optional target invoice ID alias.")
    counterparty: Optional[str] = Field(None, description="Optional target counterparty name or GSTIN.")
    scope: Optional[str] = Field(None, description="Optional scope filter (e.g. 'all', 'high_risk').")
    requested_focus: Optional[str] = Field(None, description="Optional focus area (e.g. 'tax_rate', 'blocked_itc').")
    force_fallback: bool = Field(False, description="Force deterministic fallback synthesis.")
    session_id: Optional[str] = Field(None, description="Optional multi-turn investigation session ID.")
    budget: Optional[InvestigationBudget] = Field(None, description="Optional custom investigation budget override.")

    def model_post_init(self, __context: Any) -> None:
        if not self.user_query and self.query:
            self.user_query = self.query
        if not self.invoice_no and self.invoice_id:
            self.invoice_no = self.invoice_id


class InvestigationIntent(BaseModel):
    """Result of intent detection."""
    intent: InvestigationIntentEnum = Field(..., description="Primary classified intent.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Classification confidence score.")
    explanation: str = Field("", description="Reasoning for intent classification.")
    target_invoice_id: Optional[str] = Field(None, description="Extracted target invoice ID if present.")
    target_counterparty: Optional[str] = Field(None, description="Extracted target counterparty if present.")


class InvestigationPlan(BaseModel):
    """Controlled execution plan mapping intent to read-only tools."""
    intent: InvestigationIntentEnum = Field(..., description="Target investigation intent.")
    required_tools: List[str] = Field(default_factory=list, description="Approved read-only tools to execute.")
    target: Optional[str] = Field(None, description="Target entity identifier.")
    reasoning_steps: List[str] = Field(default_factory=list, description="Step-by-step investigation rationale.")
    constraints: List[str] = Field(
        default_factory=lambda: ["READ_ONLY_EXECUTION", "STRICT_EVIDENCE_GROUNDING"],
        description="Safety and execution constraints.",
    )


class ToolResult(BaseModel):
    """Structured output from executing a read-only deterministic tool."""
    tool_name: str = Field(..., description="Name of executed tool.")
    success: bool = Field(True, description="Whether tool execution succeeded.")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Primary output payload from tool.")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Supporting evidence items.")
    errors: List[str] = Field(default_factory=list, description="Error messages if execution failed.")
    execution_time_ms: float = Field(0.0, ge=0.0, description="Execution time in milliseconds.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Tool execution metadata.")


class TraceStep(BaseModel):
    """Audit log entry capturing a single step in the agentic investigation loop."""
    step_number: int = Field(..., description="Sequential step index (1-based).")
    action_type: str = Field(..., description="Action type (e.g. INTENT_CLASSIFICATION, PLAN_CREATED, TOOL_EXECUTED, EVALUATION, FINISH).")
    tool_name: Optional[str] = Field(None, description="Executed tool name if action is tool call.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to tool if applicable.")
    result_summary: str = Field(..., description="Human-readable summary of step result or evidence state.")
    status: str = Field("SUCCESS", description="Step execution status.")
    execution_time_ms: float = Field(0.0, ge=0.0, description="Elapsed time for this step in milliseconds.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp when step occurred.",
    )


class EvidenceEvaluation(BaseModel):
    """Structured result from EvidenceEvaluator."""
    status: EvaluationStatusEnum = Field(..., description="Sufficiency status.")
    sufficient: bool = Field(..., description="True if evidence is sufficient for synthesis.")
    missing_evidence: List[str] = Field(default_factory=list, description="Explicit missing evidence dimensions.")
    contradictions: List[str] = Field(default_factory=list, description="Detected evidence contradictions if any.")
    recommended_next_tools: List[str] = Field(default_factory=list, description="Suggested next tools to execute.")
    rationale: str = Field("", description="Rationale for evaluation decision.")


class NextInvestigationAction(BaseModel):
    """Structured next step decision from LLM or deterministic selector."""
    action: str = Field("FINISH", description="Next action type: 'CALL_TOOL' or 'FINISH'.")
    tool_name: Optional[str] = Field(None, description="Target tool name if action is CALL_TOOL.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool parameter arguments.")
    reason: str = Field("", description="Rationale for selecting this action.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Selection confidence score.")


class InvestigationState(BaseModel):
    """Mutable runtime state tracking an agentic investigation loop."""
    investigation_id: str = Field(
        default_factory=lambda: f"INVEST-{uuid.uuid4().hex[:8].upper()}",
        description="Unique tracking ID for investigation run.",
    )
    request: InvestigationRequest
    intent: InvestigationIntent
    target: Optional[str] = Field(None, description="Target invoice or vendor identifier.")
    initial_plan: InvestigationPlan
    budget: InvestigationBudget = Field(default_factory=InvestigationBudget)
    current_step: int = Field(0, ge=0, description="Current step iteration count.")
    status: InvestigationStatusEnum = Field(InvestigationStatusEnum.INITIALIZED)
    termination_reason: Optional[TerminationReasonEnum] = Field(None)
    executed_tools: List[str] = Field(default_factory=list)
    tool_results: List[ToolResult] = Field(default_factory=list)
    accumulated_evidence: Dict[str, Any] = Field(default_factory=dict)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    remaining_questions: List[str] = Field(default_factory=list)
    trace: List[TraceStep] = Field(default_factory=list)
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = Field(None)


class InvestigationContext(BaseModel):
    """Evidence-first context prepared for LLM synthesis."""
    request: InvestigationRequest
    intent: InvestigationIntent
    plan: InvestigationPlan
    tool_results: List[ToolResult] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    deterministic_findings: List[Dict[str, Any]] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    state: Optional[InvestigationState] = Field(None, description="Full investigation loop state if available.")


class InvestigationResponse(BaseModel):
    """Final structured, grounded investigation response."""
    answer: str = Field(..., description="Human-readable grounded synthesis answer.")
    intent: InvestigationIntentEnum = Field(..., description="Executed intent.")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted supporting evidence.")
    findings: List[Dict[str, Any]] = Field(default_factory=list, description="Key deterministic findings.")
    recommendations: List[str] = Field(default_factory=list, description="Advisory recommendations.")
    risk: Dict[str, Any] = Field(default_factory=dict, description="Risk profile summary.")
    financial_exposure: Dict[str, Any] = Field(default_factory=dict, description="Financial exposure summary.")
    confidence: str = Field("HIGH", description="Synthesis confidence rating (HIGH, MEDIUM, LOW).")
    limitations: List[str] = Field(default_factory=list, description="Explicit analysis limitations.")
    tools_used: List[str] = Field(default_factory=list, description="List of executed tool names.")
    provider_status: Dict[str, Any] = Field(default_factory=dict, description="LLM provider availability status.")
    investigation_id: Optional[str] = Field(None, description="Unique investigation tracking ID.")
    investigation_status: Optional[str] = Field(None, description="Final loop lifecycle status.")
    termination_reason: Optional[str] = Field(None, description="Criteria for loop termination.")
    investigation_steps: List[Dict[str, Any]] = Field(default_factory=list, description="Audit trace steps.")
    evidence_sufficiency: Dict[str, Any] = Field(default_factory=dict, description="Evidence evaluator summary.")
    contradictions: List[str] = Field(default_factory=list, description="Detected evidence contradictions.")
    knowledge_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Retrieved regulatory knowledge evidence items.")
    session_id: Optional[str] = Field(None, description="Multi-turn session ID if associated with a workspace session.")
    entity_focus: Optional[Dict[str, Any]] = Field(None, description="Active entity focus dictionary.")

    # Sprint 23 Hardened Extension Fields
    what_was_detected: Dict[str, Any] = Field(default_factory=dict, description="Part 1: Structured detection summary & finding IDs.")
    supporting_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Part 2: Evidence records & source citations.")
    conflicts_and_contradictions: List[Dict[str, Any]] = Field(default_factory=list, description="Part 3: Cross-signal contradiction items.")
    financial_impact: List[Dict[str, Any]] = Field(default_factory=list, description="Part 4: Financial exposure traces.")
    missing_evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Part 5: Itemized missing evidence items.")
    next_steps: List[str] = Field(default_factory=list, description="Part 6: Non-authoritative advisory next steps.")

    system_confidence: float = Field(1.0, ge=0.0, le=1.0, description="Deterministic statutory rule certainty.")
    ai_confidence: float = Field(0.90, ge=0.0, le=1.0, description="Synthesized explanation quality.")
    prompt_version: str = Field("v23.1", description="Hardened prompt version identifier.")

