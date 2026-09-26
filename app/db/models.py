"""
app.db.models
=============
SQLAlchemy 2.0 Declarative ORM Models for Sprint 14 & Sprint 15 Relational Persistence.
Defines SessionORM, TurnORM, CaseORM (with concurrency versioning), CaseDecisionORM,
CaseEventORM, CaseEvidenceRefORM, InvestigationPlanORM, CaseEvidenceRecordORM,
CaseFindingORM, CaseRiskAssessmentORM, and CaseRecommendationORM.
"""

from __future__ import annotations

from typing import List, Optional
from sqlalchemy import (
    BigInteger,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Base class."""
    pass


class SessionORM(Base):
    """ORM table persisting Investigation Sessions."""

    __tablename__ = "investigation_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)
    entity_focus_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accumulated_findings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    accumulated_regulatory_evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)

    turns: Mapped[List[TurnORM]] = relationship(
        "TurnORM",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="TurnORM.turn_index",
    )

    __table_args__ = (
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_created_at", "created_at"),
    )


class TurnORM(Base):
    """ORM table persisting Investigation Turns within a Session."""

    __tablename__ = "investigation_turns"

    id: Mapped[Optional[int]] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_query: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str] = mapped_column(String(64), nullable=False)
    tools_used_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    findings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    regulatory_knowledge_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synthesized_answer: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(32), default="HIGH")
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)

    session: Mapped[SessionORM] = relationship("SessionORM", back_populates="turns")

    __table_args__ = (
        UniqueConstraint("session_id", "turn_index", name="uq_session_turn_index"),
        Index("idx_turns_session_id", "session_id"),
    )


class CaseORM(Base):
    """ORM table persisting Investigation Cases."""

    __tablename__ = "investigation_cases"

    case_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="P3", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    case_type: Mapped[str] = mapped_column(String(64), default="GST_COMPLIANCE_INVESTIGATION", nullable=False)
    source: Mapped[str] = mapped_column(String(64), default="AUTOMATED_SCAN", nullable=False)
    source_session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_dossier_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    counterparty_gstin: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    counterparty_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    assigned_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    financial_exposure: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    root_cause: Mapped[str] = mapped_column(String(128), default="UNDETERMINED", nullable=False)
    blast_radius_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Version column for optimistic locking / concurrency control
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    decisions: Mapped[List[CaseDecisionORM]] = relationship(
        "CaseDecisionORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseDecisionORM.timestamp",
    )

    events: Mapped[List[CaseEventORM]] = relationship(
        "CaseEventORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseEventORM.timestamp",
    )

    evidence_references: Mapped[List[CaseEvidenceRefORM]] = relationship(
        "CaseEvidenceRefORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseEvidenceRefORM.timestamp",
    )

    plans: Mapped[List[InvestigationPlanORM]] = relationship(
        "InvestigationPlanORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="InvestigationPlanORM.created_at",
    )

    evidence_records: Mapped[List[CaseEvidenceRecordORM]] = relationship(
        "CaseEvidenceRecordORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseEvidenceRecordORM.collected_at",
    )

    findings: Mapped[List[CaseFindingORM]] = relationship(
        "CaseFindingORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseFindingORM.created_at",
    )

    risk_assessments: Mapped[List[CaseRiskAssessmentORM]] = relationship(
        "CaseRiskAssessmentORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseRiskAssessmentORM.assessed_at",
    )

    recommendations: Mapped[List[CaseRecommendationORM]] = relationship(
        "CaseRecommendationORM",
        back_populates="case",
        cascade="all, delete-orphan",
        order_by="CaseRecommendationORM.created_at",
    )

    __table_args__ = (
        Index("idx_cases_status", "status"),
        Index("idx_cases_priority", "priority"),
        Index("idx_cases_risk_level", "risk_level"),
        Index("idx_cases_assigned_to", "assigned_to"),
        Index("idx_cases_invoice_id", "invoice_id"),
        Index("idx_cases_source_session_id", "source_session_id"),
    )


class CaseDecisionORM(Base):
    """ORM table persisting Human Review Decisions."""

    __tablename__ = "case_decisions"

    decision_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    reviewer: Mapped[str] = mapped_column(String(128), nullable=False)
    reviewer_role: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decision: Mapped[str] = mapped_column(String(64), nullable=False)
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    requested_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_reviewed_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="decisions")

    __table_args__ = (
        Index("idx_decisions_case_id", "case_id"),
        Index("idx_decisions_reviewer", "reviewer"),
    )


class CaseEventORM(Base):
    """ORM table persisting Append-Only Audit Timeline Events."""

    __tablename__ = "case_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    new_status: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="events")

    __table_args__ = (
        Index("idx_events_case_id", "case_id"),
        Index("idx_events_event_type", "event_type"),
    )


class CaseEvidenceRefORM(Base):
    """ORM table persisting Immutable Evidence Provenance References."""

    __tablename__ = "case_evidence_references"

    reference_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_identifier: Mapped[str] = mapped_column(String(128), nullable=False)
    invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gate_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dossier_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    document_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    section: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="evidence_references")

    __table_args__ = (
        Index("idx_evidence_case_id", "case_id"),
        Index("idx_evidence_invoice_id", "invoice_id"),
        Index("idx_evidence_source_type", "source_type"),
    )


class InvestigationPlanORM(Base):
    """ORM table persisting Investigation Plans."""

    __tablename__ = "investigation_plans"

    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    subject_invoice_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_default", nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="P3", nullable=False)
    questions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_evidence_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analysis_tasks_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_areas_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    budget_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    limit_reached_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PLANNED", nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(64), default="", nullable=False)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="plans")
    steps: Mapped[List[InvestigationStepORM]] = relationship(
        "InvestigationStepORM",
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_plans_case_id", "case_id"),
        Index("idx_plans_tenant_id", "tenant_id"),
        Index("idx_plans_status", "status"),
    )


class CaseEvidenceRecordORM(Base):
    """ORM table persisting Structured Evidence Records."""

    __tablename__ = "case_evidence_records"

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reliability: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    collected_at: Mapped[str] = mapped_column(String(64), nullable=False)
    collected_by: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="evidence_records")

    __table_args__ = (
        Index("idx_evd_records_case_id", "case_id"),
        Index("idx_evd_records_type", "evidence_type"),
    )


class CaseFindingORM(Base):
    """ORM table persisting Case Findings."""

    __tablename__ = "case_findings"

    finding_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="COMPLIANCE_MISMATCH", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="HIGH", nullable=False)
    evidence_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="VERIFIED", nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="findings")

    __table_args__ = (
        Index("idx_findings_case_id", "case_id"),
        Index("idx_findings_severity", "severity"),
    )


class CaseRiskAssessmentORM(Base):
    """ORM table persisting Structured Risk Assessments."""

    __tablename__ = "case_risk_assessments"

    assessment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW", nullable=False)
    contributing_factors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    assessed_at: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    rules_evaluated_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="risk_assessments")

    __table_args__ = (
        Index("idx_risk_assess_case_id", "case_id"),
    )


class CaseRecommendationORM(Base):
    """ORM table persisting Formal Resolution Recommendations."""

    __tablename__ = "case_recommendations"

    recommendation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    case_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_finding_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(128), default="AI_AGENT", nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    case: Mapped[CaseORM] = relationship("CaseORM", back_populates="recommendations")

    __table_args__ = (
        Index("idx_recommendations_case_id", "case_id"),
        Index("idx_recommendations_action", "recommended_action"),
    )


# --- Sprint 17 Data Quality & Ingestion ORM Models ---

class IngestionJobORM(Base):
    """ORM table persisting Ingestion Jobs."""

    __tablename__ = "ingestion_jobs"

    ingestion_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_default", nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(64), default="INVOICES", nullable=False)
    started_at: Mapped[str] = mapped_column(String(64), nullable=False)
    completed_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    accepted_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_records: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(128), default="SYSTEM", nullable=False)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    records: Mapped[List[IngestionRecordORM]] = relationship(
        "IngestionRecordORM",
        back_populates="ingestion_job",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_ingestion_jobs_tenant_id", "tenant_id"),
        Index("idx_ingestion_jobs_status", "status"),
        Index("idx_ingestion_jobs_source_id", "source_id"),
    )


class IngestionRecordORM(Base):
    """ORM table persisting Record-Level Ingestion and Quality Results."""

    __tablename__ = "ingestion_records"

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ingestion_jobs.ingestion_id", ondelete="CASCADE"),
        nullable=False,
    )
    record_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_default", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACCEPTED", nullable=False)
    raw_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_data_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duplicate_status: Mapped[str] = mapped_column(String(32), default="UNIQUE", nullable=False)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    validation_errors_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_warnings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transformation_log_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    ingestion_job: Mapped[IngestionJobORM] = relationship("IngestionJobORM", back_populates="records")

    __table_args__ = (
        Index("idx_ingestion_records_ingestion_id", "ingestion_id"),
        Index("idx_ingestion_records_fingerprint", "fingerprint"),
        Index("idx_ingestion_records_status", "status"),
    )


class DataQualityReportORM(Base):
    """ORM table persisting Aggregated Batch Data Quality Reports."""

    __tablename__ = "data_quality_reports"

    report_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("ingestion_jobs.ingestion_id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False)
    dimension_scores_json: Mapped[Text] = mapped_column(Text, nullable=False)
    total_records: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_records: Mapped[int] = mapped_column(Integer, nullable=False)
    rejected_records: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_records: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_records: Mapped[int] = mapped_column(Integer, nullable=False)
    issues_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    warnings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("idx_quality_reports_ingestion_id", "ingestion_id"),
    )


class DataLineageRecordORM(Base):
    """ORM table persisting Enterprise Data Lineage records."""

    __tablename__ = "data_lineage_records"

    lineage_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ingestion_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_record_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), default="tenant_default", nullable=False)
    transformations_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    downstream_evidence_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    downstream_finding_ids_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    downstream_case_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("idx_lineage_canonical_id", "canonical_record_id"),
        Index("idx_lineage_ingestion_id", "ingestion_id"),
        Index("idx_lineage_case_id", "downstream_case_id"),
    )


# --- Sprint 18 Investigation Intelligence & AI Evaluation ORM Models ---



class InvestigationStepORM(Base):
    """ORM table persisting Investigation Steps."""

    __tablename__ = "investigation_steps"

    step_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plan_id: Mapped[str] = mapped_column(String(64), ForeignKey("investigation_plans.plan_id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    input_params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    result_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    execution_time_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped[InvestigationPlanORM] = relationship("InvestigationPlanORM", back_populates="steps")

    __table_args__ = (
        Index("idx_investigation_steps_plan_id", "plan_id"),
        Index("idx_investigation_steps_status", "status"),
    )


class InvestigationTraceORM(Base):
    """ORM table persisting Investigation Trace Events."""

    __tablename__ = "investigation_traces"

    trace_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    step_id: Mapped[str] = mapped_column(String(64), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS", nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("idx_traces_investigation_id", "investigation_id"),
        Index("idx_traces_case_id", "case_id"),
    )


class EvaluationRunORM(Base):
    """ORM table persisting Evaluation Runs."""

    __tablename__ = "evaluation_runs"

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    passed_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    metric_averages_json: Mapped[Text] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_eval_runs_timestamp", "timestamp"),
    )


class EvaluationResultORM(Base):
    """ORM table persisting Evaluation Case Results."""

    __tablename__ = "evaluation_results"

    result_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("evaluation_runs.run_id", ondelete="CASCADE"), nullable=False)
    test_case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    test_case_name: Mapped[str] = mapped_column(String(128), nullable=False)
    passed: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 for True, 0 for False
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    metric_scores_json: Mapped[Text] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_eval_results_run_id", "run_id"),
        Index("idx_eval_results_test_case_id", "test_case_id"),
    )


# --- Sprint 19 Operations, Observability & Performance Models ---

class OperationsAlertORM(Base):
    """ORM table persisting Operational Alerts."""

    __tablename__ = "operations_alerts"

    alert_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="tenant_default", nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    action_required: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    acknowledged: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    created_at: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("idx_op_alerts_tenant_id", "tenant_id"),
        Index("idx_op_alerts_category", "category"),
        Index("idx_op_alerts_severity", "severity"),
    )


class PerformanceBenchmarkORM(Base):
    """ORM table persisting Performance Benchmarks."""

    __tablename__ = "performance_benchmarks"

    benchmark_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(32), nullable=False)
    scenarios_json: Mapped[Text] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_perf_benchmarks_timestamp", "timestamp"),
    )


class ApplicationMetricORM(Base):
    """ORM table persisting Application Metrics Snapshots."""

    __tablename__ = "application_metrics"

    metric_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(64), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(64), server_default="tenant_default", nullable=False)
    metric_type: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_data_json: Mapped[Text] = mapped_column(Text, nullable=False)

    __table_args__ = (
        Index("idx_app_metrics_tenant_id", "tenant_id"),
        Index("idx_app_metrics_timestamp", "timestamp"),
    )



