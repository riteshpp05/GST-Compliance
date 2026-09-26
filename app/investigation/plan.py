"""
app.investigation.plan
======================
Investigation Plan, Step Definitions, Status Enums, and Budget Limits for UC15 (Sprint 18).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StepResultStatusEnum(str, Enum):
    """Execution status for an investigation step."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    RETRYING = "RETRYING"


class InvestigationBudget(BaseModel):
    """Configurable budget limits for an investigation run to prevent runaway agent loops."""
    max_steps: int = Field(20, ge=1, le=100, description="Maximum total steps allowed in plan.")
    max_tool_calls: int = Field(25, ge=1, le=150, description="Maximum total tool executions allowed.")
    max_runtime_seconds: int = Field(60, ge=5, le=600, description="Maximum total runtime in seconds.")
    max_retries: int = Field(3, ge=0, le=10, description="Maximum retry count per step.")
    max_depth: int = Field(5, ge=1, le=10, description="Maximum adaptive expansion depth.")


class StepDependency(BaseModel):
    """Prerequisite dependency for a step."""
    prerequisite_step_id: str = Field(..., description="Prerequisite step ID.")
    required_status: StepResultStatusEnum = Field(
        StepResultStatusEnum.SUCCESS,
        description="Required status of prerequisite step.",
    )


class InvestigationStep(BaseModel):
    """Individual action step within an investigation plan."""
    step_id: str = Field(
        default_factory=lambda: f"STEP-{uuid.uuid4().hex[:8].upper()}",
        description="Unique step identifier.",
    )
    tool_name: str = Field(..., description="Name of the tool/service to execute.")
    purpose: str = Field(..., description="Objective of executing this step.")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="Tool input arguments.")
    expected_output: str = Field("", description="Expected output summary.")
    dependencies: List[StepDependency] = Field(default_factory=list, description="Prerequisite step dependencies.")
    status: StepResultStatusEnum = Field(StepResultStatusEnum.PENDING, description="Current step execution status.")
    result_reference: Optional[Dict[str, Any]] = Field(None, description="Output payload reference/data.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score associated with step result.")
    error_message: Optional[str] = Field(None, description="Failure reason if step failed or timed out.")
    retries_taken: int = Field(0, ge=0, description="Number of retries executed for this step.")
    execution_time_seconds: float = Field(0.0, ge=0.0, description="Step execution latency.")


class InvestigationPlan(BaseModel):
    """
    Structured, dependency-aware Investigation Plan.
    Enforces explicit budget controls and tracks execution lifecycle.
    """
    plan_id: str = Field(
        default_factory=lambda: f"PLAN-{uuid.uuid4().hex[:8].upper()}",
        description="Unique investigation plan identifier.",
    )
    case_id: str = Field(..., description="Target investigation case ID.")
    objective: str = Field(..., description="Primary investigation objective.")
    subject_invoice_id: Optional[str] = Field(None, description="Subject invoice ID under investigation.")
    tenant_id: str = Field("tenant_default", description="Tenant scope.")
    steps: List[InvestigationStep] = Field(default_factory=list, description="Ordered investigation steps.")
    budget: InvestigationBudget = Field(default_factory=InvestigationBudget, description="Budget limits.")
    priority: str = Field("P3", description="Investigation priority.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )
    created_by: str = Field("SYSTEM", description="Actor creating the plan.")
    status: str = Field("PLANNED", description="Plan status: PLANNED, IN_PROGRESS, COMPLETED, LIMIT_REACHED, FAILED.")
    limit_reached_reason: Optional[str] = Field(None, description="Reason if INVESTIGATION_LIMIT_REACHED triggered.")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
