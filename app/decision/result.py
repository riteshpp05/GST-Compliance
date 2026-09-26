"""
UC15 GST Compliance Agent — Standardized Decision Result & Trace Models
Standardized contract for rule execution results, decision paths, and evidence outputs.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity


class DecisionStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    EXEMPT = "EXEMPT"
    UNKNOWN = "UNKNOWN"


class DecisionStepTrace(BaseModel):
    """
    Step-by-step trace of condition evaluations within a decision tree.
    """
    step_no: int
    condition: str
    evaluated_value: Any
    result: bool
    description: str


class ComplianceDecisionPath(BaseModel):
    """
    Exhaustive decision path output for a single statutory or SAP control execution.
    """
    rule_id: str
    rule_name: str
    category: RuleCategory
    severity: Severity
    status: DecisionStatus

    applicability_condition: str
    is_applicable: bool = True

    actual_value: Any = None
    expected_value: Any = None
    difference: Optional[Decimal] = None
    financial_exposure: float = 0.0

    evidence: Dict[str, Any] = Field(default_factory=dict)
    legal_basis: Optional[str] = None
    policy_version: str = "2.0"
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None

    source_system: str = "CANONICAL"
    source_fields: List[str] = Field(default_factory=list)
    remediation: Optional[str] = None
    confidence: float = 1.0

    decision_trace: List[DecisionStepTrace] = Field(default_factory=list)
