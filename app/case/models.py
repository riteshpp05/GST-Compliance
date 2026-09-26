"""
app.case.models
===============
Domain Models, Enums, and Schemas for Enterprise Investigation Workflow & Case Lifecycle (Sprint 15).
Defines InvestigationCase, CaseStatusEnum, CaseDecisionEnum, CaseEventTypeEnum, CaseEvidenceReference,
CaseDecision, CaseEvent, CaseAssignment, InvestigationPlanDomain, CaseEvidenceRecord,
CaseFinding, CaseRiskAssessment, CaseRecommendation, CaseTriageResult, and API Request DTOs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CaseStatusEnum(str, Enum):
    """Lifecycle status states for an Investigation Case."""
    CREATED = "CREATED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    EVIDENCE_COLLECTED = "EVIDENCE_COLLECTED"
    FINDINGS_READY = "FINDINGS_READY"
    RESOLUTION_PROPOSED = "RESOLUTION_PROPOSED"
    PENDING_REVIEW = "PENDING_REVIEW"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    
    # Preserved backward-compatible status values from S13/S14
    OPEN = "OPEN"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MORE_EVIDENCE_REQUIRED = "MORE_EVIDENCE_REQUIRED"
    READY_FOR_RESOLUTION = "READY_FOR_RESOLUTION"
    RETURNED_FOR_INVESTIGATION = "RETURNED_FOR_INVESTIGATION"


class CaseDecisionEnum(str, Enum):
    """Supported decisions for Human Review."""
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_MORE_EVIDENCE = "REQUEST_MORE_EVIDENCE"
    RETURN_FOR_INVESTIGATION = "RETURN_FOR_INVESTIGATION"


class CaseEventTypeEnum(str, Enum):
    """Append-only audit timeline event types."""
    CASE_CREATED = "CASE_CREATED"
    CASE_ASSIGNED = "CASE_ASSIGNED"
    CASE_TRIAGED = "CASE_TRIAGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    ASSIGNED = "ASSIGNED"
    PLAN_CREATED = "PLAN_CREATED"
    INVESTIGATION_STARTED = "INVESTIGATION_STARTED"
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    FINDING_CREATED = "FINDING_CREATED"
    RISK_ASSESSED = "RISK_ASSESSED"
    RECOMMENDATION_CREATED = "RECOMMENDATION_CREATED"
    REVIEW_STARTED = "REVIEW_STARTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVIEW_APPROVED = "REVIEW_APPROVED"
    REVIEW_REJECTED = "REVIEW_REJECTED"
    MORE_EVIDENCE_REQUESTED = "MORE_EVIDENCE_REQUESTED"
    RETURNED_FOR_INVESTIGATION = "RETURNED_FOR_INVESTIGATION"
    COMMENT_ADDED = "COMMENT_ADDED"
    CASE_RESOLVED = "CASE_RESOLVED"
    CASE_CLOSED = "CASE_CLOSED"


class CaseEvidenceReference(BaseModel):
    """Evidence provenance reference linking a case back to deterministic or regulatory evidence."""
    reference_id: str = Field(
        default_factory=lambda: f"REF-{uuid.uuid4().hex[:8].upper()}",
        description="Unique reference identifier.",
    )
    source_type: str = Field(..., description="Source type: GATE_DETERMINATION, RISK_ASSESSMENT, FINANCIAL_EXPOSURE, ROOT_CAUSE, BLAST_RADIUS, REGULATORY_KNOWLEDGE.")
    source_identifier: str = Field(..., description="Unique source identifier (e.g. Gate-4, DOC-RULE-36-4).")
    invoice_id: Optional[str] = Field(None, description="Target invoice ID.")
    gate_id: Optional[int] = Field(None, description="Statutory gate ID (1-6) if applicable.")
    dossier_id: Optional[str] = Field(None, description="Source dossier ID.")
    session_id: Optional[str] = Field(None, description="Source investigation session ID.")
    document_id: Optional[str] = Field(None, description="Regulatory document ID if applicable.")
    section: Optional[str] = Field(None, description="Regulatory section citation if applicable.")
    relevance_score: Optional[float] = Field(None, description="Relevance score if applicable.")
    summary: str = Field("", description="Evidence summary description.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )


class CaseDecision(BaseModel):
    """Structured decision recorded by an authorized human reviewer."""
    decision_id: str = Field(
        default_factory=lambda: f"DEC-{uuid.uuid4().hex[:8].upper()}",
        description="Unique decision ID.",
    )
    case_id: str = Field(..., description="Target investigation case ID.")
    reviewer: str = Field(..., description="Explicit human reviewer identity.")
    reviewer_role: Optional[str] = Field("Finance Reviewer", description="Role of the reviewer.")
    decision: CaseDecisionEnum = Field(..., description="Human decision: APPROVE, REJECT, REQUEST_MORE_EVIDENCE, or RETURN_FOR_INVESTIGATION.")
    comment: str = Field(..., description="Mandatory human review comment / reasoning.")
    requested_evidence: Optional[str] = Field(None, description="Details of missing/requested evidence if decision is REQUEST_MORE_EVIDENCE.")
    evidence_reviewed: List[str] = Field(default_factory=list, description="IDs or keys of evidence references reviewed.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp of decision.",
    )


class CaseEvent(BaseModel):
    """Append-only audit timeline event entry."""
    event_id: str = Field(
        default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}",
        description="Unique event ID.",
    )
    case_id: str = Field(..., description="Target case ID.")
    event_type: CaseEventTypeEnum = Field(..., description="Event classification.")
    actor: str = Field(..., description="Human actor or subsystem name performing the action.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )
    previous_status: Optional[str] = Field(None, description="Case status prior to event.")
    new_status: Optional[str] = Field(None, description="Case status resulting from event.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event context metadata.")


class CaseAssignment(BaseModel):
    """Case assignment metadata."""
    case_id: str = Field(..., description="Target case ID.")
    assigned_to: str = Field(..., description="Assigned individual or team.")
    assigned_role: str = Field("Tax Analyst", description="Assigned functional role.")
    assigned_by: str = Field("SYSTEM", description="Actor performing assignment.")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC timestamp.",
    )
    reason: str = Field("", description="Reason for assignment.")


class InvestigationPlanDomain(BaseModel):
    """Persistent Investigation Plan for a case."""
    plan_id: str = Field(
        default_factory=lambda: f"PLAN-{uuid.uuid4().hex[:8].upper()}",
        description="Unique investigation plan ID.",
    )
    case_id: str = Field(..., description="Target investigation case ID.")
    objective: str = Field(..., description="Primary investigation objective.")
    questions: List[str] = Field(default_factory=list, description="Investigation questions to answer.")
    required_data: List[str] = Field(default_factory=list, description="Required datasets or documents.")
    expected_evidence: List[str] = Field(default_factory=list, description="Expected evidence artifacts.")
    analysis_tasks: List[str] = Field(default_factory=list, description="Planned analysis tasks.")
    risk_areas: List[str] = Field(default_factory=list, description="Identified risk areas.")
    status: str = Field("PLANNED", description="Plan status: PLANNED, IN_PROGRESS, COMPLETED.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CaseEvidenceRecord(BaseModel):
    """Structured evidence record collected during investigation."""
    evidence_id: str = Field(
        default_factory=lambda: f"EVD-{uuid.uuid4().hex[:8].upper()}",
        description="Unique evidence record ID.",
    )
    case_id: str = Field(..., description="Target case ID.")
    evidence_type: str = Field(..., description="Evidence classification: GST_RETURNS, INVOICE, TRANSACTION, FILING_MATCH, MISMATCH, ANOMALY, REGULATORY, AGENT_OUTPUT.")
    source: str = Field(..., description="Source of evidence.")
    description: str = Field(..., description="Detailed evidence description.")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured evidence payload.")
    reliability: float = Field(1.0, ge=0.0, le=1.0, description="Confidence / reliability score (0.0 - 1.0).")
    collected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    collected_by: str = Field("SYSTEM", description="Actor or subsystem collecting the evidence.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional evidence metadata.")


class CaseFinding(BaseModel):
    """Formal finding statement derived from collected evidence."""
    finding_id: str = Field(
        default_factory=lambda: f"FND-{uuid.uuid4().hex[:8].upper()}",
        description="Unique finding ID.",
    )
    case_id: str = Field(..., description="Target case ID.")
    title: str = Field(..., description="Finding title.")
    description: str = Field(..., description="Detailed finding explanation.")
    category: str = Field("COMPLIANCE_MISMATCH", description="Finding category.")
    severity: str = Field("HIGH", description="Severity: LOW, MEDIUM, HIGH, CRITICAL.")
    evidence_ids: List[str] = Field(default_factory=list, description="IDs of evidence records supporting this finding.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Finding confidence score.")
    status: str = Field("VERIFIED", description="Finding status: DRAFT, VERIFIED, DISMISSED.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_by: str = Field("SYSTEM", description="Actor creating the finding.")


class CaseRiskAssessment(BaseModel):
    """Structured risk assessment for a case."""
    assessment_id: str = Field(
        default_factory=lambda: f"RSK-{uuid.uuid4().hex[:8].upper()}",
        description="Unique risk assessment ID.",
    )
    case_id: str = Field(..., description="Target case ID.")
    risk_score: float = Field(0.0, ge=0.0, le=100.0, description="Risk score (0 - 100).")
    risk_level: str = Field("LOW", description="Risk level: LOW, MEDIUM, HIGH, CRITICAL.")
    contributing_factors: List[str] = Field(default_factory=list, description="Factors contributing to risk score.")
    explanation: str = Field("", description="Detailed risk assessment explanation.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score.")
    assessed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    model_version: str = Field("1.0", description="Model/Rule version used for assessment.")
    rules_evaluated: List[str] = Field(default_factory=list, description="Rules evaluated during assessment.")


class CaseRecommendation(BaseModel):
    """Formal resolution recommendation."""
    recommendation_id: str = Field(
        default_factory=lambda: f"REC-{uuid.uuid4().hex[:8].upper()}",
        description="Unique recommendation ID.",
    )
    case_id: str = Field(..., description="Target case ID.")
    recommended_action: str = Field(..., description="Action: NO_ACTION, REQUEST_DOCUMENTS, RECONCILIATION_REQUIRED, CORRECTION_REQUIRED, FURTHER_INVESTIGATION, ESCALATE, CLOSE_CASE.")
    rationale: str = Field(..., description="Detailed rationale for recommendation.")
    supporting_finding_ids: List[str] = Field(default_factory=list, description="IDs of supporting findings.")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Recommendation confidence.")
    generated_by: str = Field("AI_AGENT", description="System or AI actor proposing the recommendation.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CaseTriageResult(BaseModel):
    """Structured result of case triage."""
    case_id: str = Field(..., description="Target case ID.")
    priority: str = Field("P3", description="Triaged priority (P1, P2, P3, P4).")
    risk_level: str = Field("LOW", description="Triaged risk level.")
    category: str = Field("GENERAL_COMPLIANCE", description="Case category.")
    investigation_scope: str = Field("", description="Defined scope for investigation.")
    assigned_to: Optional[str] = Field(None, description="Assigned reviewer/team.")
    requires_escalation: bool = Field(False, description="Flag indicating if escalation is required.")
    triaged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    triaged_by: str = Field("SYSTEM", description="Actor executing triage.")


class InvestigationCase(BaseModel):
    """
    Domain model representing an operational Investigation Case for human review.
    Consumes outputs from Session & Dossier without duplicating compliance or risk engines.
    """
    case_id: str = Field(
        default_factory=lambda: f"CASE-{uuid.uuid4().hex[:8].upper()}",
        description="Unique case identifier (e.g. CASE-ABCD1234).",
    )
    title: str = Field(..., description="Case title summarizing the investigation target and primary defect.")
    description: str = Field("", description="Detailed case description.")
    status: CaseStatusEnum = Field(CaseStatusEnum.CREATED, description="Current lifecycle state.")
    priority: str = Field("P3", description="Case priority (P1, P2, P3, P4) derived from RiskEngine.")
    risk_level: str = Field("LOW", description="Risk level (LOW, MEDIUM, HIGH, CRITICAL) derived from RiskEngine.")
    case_type: str = Field("GST_COMPLIANCE_INVESTIGATION", description="Case classification type.")
    source: str = Field("AUTOMATED_SCAN", description="Origin source of case (AUTOMATED_SCAN, MANUAL_ENTRY, SYSTEM).")
    tenant_id: str = Field("tenant_default", description="Tenant separation identifier.")
    source_session_id: Optional[str] = Field(None, description="Originating multi-turn investigation session ID.")
    source_dossier_id: Optional[str] = Field(None, description="Originating audit dossier ID.")
    invoice_id: Optional[str] = Field(None, description="Target invoice ID (e.g. INV-8000001).")
    counterparty_gstin: Optional[str] = Field(None, description="Counterparty GSTIN.")
    counterparty_name: Optional[str] = Field(None, description="Counterparty entity name.")
    created_by: str = Field("SYSTEM", description="Creator identity.")
    assigned_to: Optional[str] = Field(None, description="Assigned reviewer/analyst.")
    assigned_role: Optional[str] = Field(None, description="Assigned functional role.")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recommendation: str = Field("", description="AI advisory recommendation text.")
    financial_exposure: float = Field(0.0, ge=0.0, description="Financial exposure amount (INR).")
    root_cause: str = Field("UNDETERMINED", description="Root cause classification.")
    blast_radius: Dict[str, Any] = Field(default_factory=dict, description="Multidimensional blast radius scope.")
    evidence_references: List[CaseEvidenceReference] = Field(default_factory=list, description="Linked evidence references.")
    decisions: List[CaseDecision] = Field(default_factory=list, description="Historical human review decisions.")
    compliance_context_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Rule, reference, and calculation trace snapshot for historical case reproducibility.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional case metadata.")

    def to_dict(self) -> Dict[str, Any]:
        """Convert case to dictionary payload."""
        return self.model_dump()


# --- Request DTOs ---

class CaseCreateRequest(BaseModel):
    """Payload for creating a new investigation case."""
    session_id: Optional[str] = Field(None, description="Source investigation session ID.")
    dossier_id: Optional[str] = Field(None, description="Source dossier ID.")
    invoice_id: Optional[str] = Field(None, description="Target invoice ID.")
    counterparty_gstin: Optional[str] = Field(None, description="Counterparty GSTIN.")
    case_type: Optional[str] = Field("GST_COMPLIANCE_INVESTIGATION", description="Case type.")
    source: Optional[str] = Field("MANUAL_ENTRY", description="Origin source.")
    title: Optional[str] = Field(None, description="Custom case title.")
    description: Optional[str] = Field(None, description="Custom case description.")
    assigned_to: Optional[str] = Field(None, description="Initial assignee.")
    assigned_role: Optional[str] = Field(None, description="Initial assignee role.")
    created_by: Optional[str] = Field("SYSTEM", description="Creator identity.")


class CaseTriageRequest(BaseModel):
    """Payload for triaging a case."""
    priority: Optional[str] = Field(None, description="Assigned priority: P1, P2, P3, P4.")
    risk_level: Optional[str] = Field(None, description="Assigned risk level: LOW, MEDIUM, HIGH, CRITICAL.")
    category: Optional[str] = Field("INPUT_TAX_CREDIT_ANOMALY", description="Case category.")
    investigation_scope: Optional[str] = Field("FULL_AUDIT", description="Investigation scope.")
    assigned_to: Optional[str] = Field(None, description="Target assignee.")
    requires_escalation: Optional[bool] = Field(False, description="Flag indicating if escalation is required.")
    actor: Optional[str] = Field("SYSTEM_TRIAGE", description="Actor performing triage.")


class CaseAssignRequest(BaseModel):
    """Payload for assigning or reassigning a case."""
    assigned_to: str = Field(..., description="Target assignee identity.")
    assigned_role: Optional[str] = Field("Tax Analyst", description="Target assignee role.")
    assigned_by: Optional[str] = Field("SYSTEM", description="Actor performing assignment.")
    reason: Optional[str] = Field("", description="Assignment reason.")


class CaseReviewRequest(BaseModel):
    """Payload for submitting a human review decision."""
    reviewer: str = Field(..., description="Explicit human reviewer identity (e.g. 'John Doe').")
    reviewer_role: Optional[str] = Field("Finance Manager", description="Role of the reviewer.")
    decision: CaseDecisionEnum = Field(..., description="Review decision: APPROVE, REJECT, REQUEST_MORE_EVIDENCE, or RETURN_FOR_INVESTIGATION.")
    comment: str = Field(..., description="Mandatory human review comment / reasoning.")
    requested_evidence: Optional[str] = Field(None, description="Details of missing/requested evidence if decision is REQUEST_MORE_EVIDENCE.")


class InvestigationPlanCreateRequest(BaseModel):
    """Payload for creating or updating an investigation plan."""
    objective: str = Field(..., description="Primary investigation objective.")
    questions: List[str] = Field(default_factory=list, description="Questions to answer.")
    required_data: List[str] = Field(default_factory=list, description="Required datasets or documents.")
    expected_evidence: List[str] = Field(default_factory=list, description="Expected evidence artifacts.")
    analysis_tasks: List[str] = Field(default_factory=list, description="Analysis tasks.")
    risk_areas: List[str] = Field(default_factory=list, description="Risk areas.")


class EvidenceCreateRequest(BaseModel):
    """Payload for adding evidence to a case."""
    evidence_type: str = Field(..., description="Evidence classification.")
    source: str = Field(..., description="Source of evidence.")
    description: str = Field(..., description="Detailed description.")
    data: Dict[str, Any] = Field(default_factory=dict, description="Payload data.")
    reliability: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Reliability score.")
    collected_by: Optional[str] = Field("SYSTEM", description="Collector identity.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata.")


class FindingCreateRequest(BaseModel):
    """Payload for adding a finding to a case."""
    title: str = Field(..., description="Finding title.")
    description: str = Field(..., description="Finding description.")
    category: Optional[str] = Field("COMPLIANCE_MISMATCH", description="Finding category.")
    severity: Optional[str] = Field("HIGH", description="Severity: LOW, MEDIUM, HIGH, CRITICAL.")
    evidence_ids: List[str] = Field(default_factory=list, description="Supporting evidence IDs.")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score.")
    created_by: Optional[str] = Field("SYSTEM", description="Creator identity.")


class RiskAssessmentCreateRequest(BaseModel):
    """Payload for recording a risk assessment."""
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score.")
    risk_level: str = Field(..., description="Risk level.")
    contributing_factors: List[str] = Field(default_factory=list, description="Contributing factors.")
    explanation: str = Field("", description="Assessment explanation.")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score.")
    model_version: Optional[str] = Field("1.0", description="Model version.")
    rules_evaluated: List[str] = Field(default_factory=list, description="Rules evaluated.")


class RecommendationCreateRequest(BaseModel):
    """Payload for proposing a resolution recommendation."""
    recommended_action: str = Field(..., description="Proposed action: NO_ACTION, REQUEST_DOCUMENTS, RECONCILIATION_REQUIRED, CORRECTION_REQUIRED, FURTHER_INVESTIGATION, ESCALATE, CLOSE_CASE.")
    rationale: str = Field(..., description="Rationale for recommendation.")
    supporting_finding_ids: List[str] = Field(default_factory=list, description="IDs of supporting findings.")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score.")
    generated_by: Optional[str] = Field("AI_AGENT", description="Actor proposing recommendation.")
