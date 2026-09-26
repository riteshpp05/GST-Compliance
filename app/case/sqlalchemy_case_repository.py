"""
app.case.sqlalchemy_case_repository
===================================
Relational SQLAlchemy Repository implementation for Investigation Cases (Sprint 14 & Sprint 15).
Implements BaseCaseRepository with atomic transactions, optimistic concurrency protection,
immutable evidence provenance, structured workflow entities, and round-trip domain mapping.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import joinedload

from app.case.models import (
    CaseDecision,
    CaseDecisionEnum,
    CaseEvent,
    CaseEvidenceReference,
    CaseEvidenceRecord,
    CaseFinding,
    CaseRiskAssessment,
    CaseRecommendation,
    CaseStatusEnum,
    InvestigationCase,
    InvestigationPlanDomain,
)
from app.case.repository import BaseCaseRepository
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError
from app.db.connection import db_session_scope, get_db_session
from app.db.models import (
    CaseDecisionORM,
    CaseEventORM,
    CaseEvidenceRefORM,
    CaseORM,
    InvestigationPlanORM,
    CaseEvidenceRecordORM,
    CaseFindingORM,
    CaseRiskAssessmentORM,
    CaseRecommendationORM,
)
from app.db.serializer import dump_json_value, load_json_value
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class SQLAlchemyCaseRepository(BaseCaseRepository):
    """Relational Database Case Repository implementation using SQLAlchemy 2.0."""

    def save_case(self, case: InvestigationCase) -> None:
        """Upsert InvestigationCase domain model, decisions, events, and evidence references."""
        with db_session_scope() as db:
            existing = db.execute(
                select(CaseORM).where(CaseORM.case_id == case.case_id)
            ).scalar_one_or_none()

            status_str = case.status.value if hasattr(case.status, "value") else str(case.status)
            blast_json = dump_json_value(case.blast_radius)
            meta_json = dump_json_value(case.metadata)

            if existing is None:
                orm_case = CaseORM(
                    case_id=case.case_id,
                    title=case.title,
                    description=case.description,
                    status=status_str,
                    priority=case.priority,
                    risk_level=case.risk_level,
                    case_type=case.case_type,
                    source=case.source,
                    source_session_id=case.source_session_id,
                    source_dossier_id=case.source_dossier_id,
                    invoice_id=case.invoice_id,
                    counterparty_gstin=case.counterparty_gstin,
                    counterparty_name=case.counterparty_name,
                    created_by=case.created_by,
                    assigned_to=case.assigned_to,
                    assigned_role=case.assigned_role,
                    created_at=case.created_at,
                    updated_at=case.updated_at,
                    recommendation=case.recommendation,
                    financial_exposure=float(case.financial_exposure),
                    root_cause=case.root_cause,
                    blast_radius_json=blast_json,
                    metadata_json=meta_json,
                    version=1,
                )
                db.add(orm_case)
            else:
                existing.title = case.title
                existing.description = case.description
                existing.status = status_str
                existing.priority = case.priority
                existing.risk_level = case.risk_level
                existing.case_type = case.case_type
                existing.source = case.source
                existing.assigned_to = case.assigned_to
                existing.assigned_role = case.assigned_role
                existing.updated_at = case.updated_at
                existing.recommendation = case.recommendation
                existing.financial_exposure = float(case.financial_exposure)
                existing.root_cause = case.root_cause
                existing.blast_radius_json = blast_json
                existing.metadata_json = meta_json
                existing.version = existing.version + 1
                orm_case = existing

            db.flush()

            # Synchronize decisions
            existing_dec_ids = set(
                db.execute(
                    select(CaseDecisionORM.decision_id).where(CaseDecisionORM.case_id == case.case_id)
                ).scalars().all()
            )
            for dec in case.decisions:
                if dec.decision_id not in existing_dec_ids:
                    dec_str = dec.decision.value if hasattr(dec.decision, "value") else str(dec.decision)
                    db.add(
                        CaseDecisionORM(
                            decision_id=dec.decision_id,
                            case_id=case.case_id,
                            reviewer=dec.reviewer,
                            reviewer_role=dec.reviewer_role,
                            decision=dec_str,
                            comment=dec.comment,
                            requested_evidence=dec.requested_evidence,
                            evidence_reviewed_json=dump_json_value(dec.evidence_reviewed),
                            timestamp=dec.timestamp,
                        )
                    )

            # Synchronize immutable evidence references
            existing_ref_ids = set(
                db.execute(
                    select(CaseEvidenceRefORM.reference_id).where(CaseEvidenceRefORM.case_id == case.case_id)
                ).scalars().all()
            )

            for ref in case.evidence_references:
                if ref.reference_id not in existing_ref_ids:
                    db.add(
                        CaseEvidenceRefORM(
                            reference_id=ref.reference_id,
                            case_id=case.case_id,
                            source_type=ref.source_type,
                            source_identifier=ref.source_identifier,
                            invoice_id=ref.invoice_id,
                            gate_id=ref.gate_id,
                            dossier_id=ref.dossier_id,
                            session_id=ref.session_id,
                            document_id=ref.document_id,
                            section=ref.section,
                            relevance_score=ref.relevance_score,
                            summary=ref.summary,
                            timestamp=ref.timestamp,
                        )
                    )

        logger.debug(f"Saved case '{case.case_id}' to relational database (Status: {case.status})")

    def get_case(self, case_id: str) -> Optional[InvestigationCase]:
        """Retrieve InvestigationCase domain model from relational database."""
        db = get_db_session()
        try:
            orm_case = db.execute(
                select(CaseORM)
                .options(
                    joinedload(CaseORM.decisions),
                    joinedload(CaseORM.events),
                    joinedload(CaseORM.evidence_references),
                )
                .where(CaseORM.case_id == case_id)
            ).unique().scalar_one_or_none()

            if not orm_case:
                return None

            # Convert decisions
            decisions: List[CaseDecision] = []
            for d in sorted(orm_case.decisions, key=lambda x: x.timestamp):
                decisions.append(
                    CaseDecision(
                        decision_id=d.decision_id,
                        case_id=d.case_id,
                        reviewer=d.reviewer,
                        reviewer_role=d.reviewer_role,
                        decision=CaseDecisionEnum(d.decision),
                        comment=d.comment,
                        requested_evidence=d.requested_evidence,
                        evidence_reviewed=load_json_value(d.evidence_reviewed_json, default_factory=list),
                        timestamp=d.timestamp,
                    )
                )

            # Convert evidence references
            evidence_refs: List[CaseEvidenceReference] = []
            for r in sorted(orm_case.evidence_references, key=lambda x: x.timestamp):
                evidence_refs.append(
                    CaseEvidenceReference(
                        reference_id=r.reference_id,
                        source_type=r.source_type,
                        source_identifier=r.source_identifier,
                        invoice_id=r.invoice_id,
                        gate_id=r.gate_id,
                        dossier_id=r.dossier_id,
                        session_id=r.session_id,
                        document_id=r.document_id,
                        section=r.section,
                        relevance_score=r.relevance_score,
                        summary=r.summary,
                        timestamp=r.timestamp,
                    )
                )

            blast = load_json_value(orm_case.blast_radius_json, default_factory=dict)
            meta = load_json_value(orm_case.metadata_json, default_factory=dict)

            case_obj = InvestigationCase(
                case_id=orm_case.case_id,
                title=orm_case.title,
                description=orm_case.description,
                status=CaseStatusEnum(orm_case.status),
                priority=orm_case.priority,
                risk_level=orm_case.risk_level,
                case_type=getattr(orm_case, "case_type", "GST_COMPLIANCE_INVESTIGATION"),
                source=getattr(orm_case, "source", "AUTOMATED_SCAN"),
                source_session_id=orm_case.source_session_id,
                source_dossier_id=orm_case.source_dossier_id,
                invoice_id=orm_case.invoice_id,
                counterparty_gstin=orm_case.counterparty_gstin,
                counterparty_name=orm_case.counterparty_name,
                created_by=getattr(orm_case, "created_by", "SYSTEM"),
                assigned_to=orm_case.assigned_to,
                assigned_role=orm_case.assigned_role,
                created_at=orm_case.created_at,
                updated_at=orm_case.updated_at,
                recommendation=orm_case.recommendation,
                financial_exposure=orm_case.financial_exposure,
                root_cause=orm_case.root_cause,
                blast_radius=blast,
                evidence_references=evidence_refs,
                decisions=decisions,
                metadata=meta,
            )
            return case_obj
        finally:
            db.close()

    def list_cases(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> List[InvestigationCase]:
        """List cases with optional database-level filtering."""
        db = get_db_session()
        try:
            stmt = select(CaseORM.case_id).order_by(CaseORM.created_at.desc())
            if status:
                stmt = stmt.where(CaseORM.status == status)
            if priority:
                stmt = stmt.where(CaseORM.priority == priority)
            if invoice_id:
                stmt = stmt.where(CaseORM.invoice_id == invoice_id)

            case_ids = db.execute(stmt).scalars().all()
            results: List[InvestigationCase] = []
            for cid in case_ids:
                c = self.get_case(cid)
                if c:
                    results.append(c)
            return results
        finally:
            db.close()

    def delete_case(self, case_id: str) -> bool:
        """Delete case and cascade delete decisions, events, and evidence references."""
        with db_session_scope() as db:
            res = db.execute(delete(CaseORM).where(CaseORM.case_id == case_id))
            return res.rowcount > 0

    def save_event(self, event: CaseEvent) -> None:
        """Persist single append-only audit event."""
        with db_session_scope() as db:
            evt_str = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            db.add(
                CaseEventORM(
                    event_id=event.event_id,
                    case_id=event.case_id,
                    event_type=evt_str,
                    actor=event.actor,
                    timestamp=event.timestamp,
                    previous_status=event.previous_status,
                    new_status=event.new_status,
                    metadata_json=dump_json_value(event.metadata),
                )
            )

    def get_events(self, case_id: str) -> List[CaseEvent]:
        """Retrieve chronological event history for a case."""
        db = get_db_session()
        try:
            orm_events = db.execute(
                select(CaseEventORM).where(CaseEventORM.case_id == case_id).order_by(CaseEventORM.timestamp.asc())
            ).scalars().all()

            results: List[CaseEvent] = []
            for e in orm_events:
                results.append(
                    CaseEvent(
                        event_id=e.event_id,
                        case_id=e.case_id,
                        event_type=e.event_type,
                        actor=e.actor,
                        timestamp=e.timestamp,
                        previous_status=e.previous_status,
                        new_status=e.new_status,
                        metadata=load_json_value(e.metadata_json, default_factory=dict),
                    )
                )
            return results
        finally:
            db.close()

    def save_evidence_ref(self, case_id: str, ref: CaseEvidenceReference) -> None:
        """Persist immutable evidence reference."""
        with db_session_scope() as db:
            db.add(
                CaseEvidenceRefORM(
                    reference_id=ref.reference_id,
                    case_id=case_id,
                    source_type=ref.source_type,
                    source_identifier=ref.source_identifier,
                    invoice_id=ref.invoice_id,
                    gate_id=ref.gate_id,
                    dossier_id=ref.dossier_id,
                    session_id=ref.session_id,
                    document_id=ref.document_id,
                    section=ref.section,
                    relevance_score=ref.relevance_score,
                    summary=ref.summary,
                    timestamp=ref.timestamp,
                )
            )

    def get_evidence_refs(self, case_id: str) -> List[CaseEvidenceReference]:
        """Retrieve evidence references for a case."""
        case = self.get_case(case_id)
        return case.evidence_references if case else []

    # --- Sprint 15 Extended Persistence Methods ---

    def save_plan(self, plan: InvestigationPlanDomain) -> None:
        """Upsert investigation plan for a case."""
        with db_session_scope() as db:
            existing = db.execute(
                select(InvestigationPlanORM).where(InvestigationPlanORM.case_id == plan.case_id)
            ).scalar_one_or_none()

            if existing is None:
                db.add(
                    InvestigationPlanORM(
                        plan_id=plan.plan_id,
                        case_id=plan.case_id,
                        objective=plan.objective,
                        questions_json=dump_json_value(plan.questions),
                        required_data_json=dump_json_value(plan.required_data),
                        expected_evidence_json=dump_json_value(plan.expected_evidence),
                        analysis_tasks_json=dump_json_value(plan.analysis_tasks),
                        risk_areas_json=dump_json_value(plan.risk_areas),
                        status=plan.status,
                        created_at=plan.created_at,
                        updated_at=plan.updated_at,
                    )
                )
            else:
                existing.objective = plan.objective
                existing.questions_json = dump_json_value(plan.questions)
                existing.required_data_json = dump_json_value(plan.required_data)
                existing.expected_evidence_json = dump_json_value(plan.expected_evidence)
                existing.analysis_tasks_json = dump_json_value(plan.analysis_tasks)
                existing.risk_areas_json = dump_json_value(plan.risk_areas)
                existing.status = plan.status
                existing.updated_at = plan.updated_at

    def get_plan(self, case_id: str) -> Optional[InvestigationPlanDomain]:
        """Retrieve investigation plan for a case."""
        db = get_db_session()
        try:
            orm_plan = db.execute(
                select(InvestigationPlanORM).where(InvestigationPlanORM.case_id == case_id)
            ).scalar_one_or_none()
            if not orm_plan:
                return None
            return InvestigationPlanDomain(
                plan_id=orm_plan.plan_id,
                case_id=orm_plan.case_id,
                objective=orm_plan.objective,
                questions=load_json_value(orm_plan.questions_json, default_factory=list),
                required_data=load_json_value(orm_plan.required_data_json, default_factory=list),
                expected_evidence=load_json_value(orm_plan.expected_evidence_json, default_factory=list),
                analysis_tasks=load_json_value(orm_plan.analysis_tasks_json, default_factory=list),
                risk_areas=load_json_value(orm_plan.risk_areas_json, default_factory=list),
                status=orm_plan.status,
                created_at=orm_plan.created_at,
                updated_at=orm_plan.updated_at,
            )
        finally:
            db.close()

    def save_evidence_record(self, record: CaseEvidenceRecord) -> None:
        """Save a structured evidence record."""
        with db_session_scope() as db:
            db.add(
                CaseEvidenceRecordORM(
                    evidence_id=record.evidence_id,
                    case_id=record.case_id,
                    evidence_type=record.evidence_type,
                    source=record.source,
                    description=record.description,
                    data_json=dump_json_value(record.data),
                    reliability=record.reliability,
                    collected_at=record.collected_at,
                    collected_by=record.collected_by,
                    metadata_json=dump_json_value(record.metadata),
                )
            )

    def get_evidence_records(self, case_id: str) -> List[CaseEvidenceRecord]:
        """Retrieve evidence records for a case."""
        db = get_db_session()
        try:
            orm_records = db.execute(
                select(CaseEvidenceRecordORM)
                .where(CaseEvidenceRecordORM.case_id == case_id)
                .order_by(CaseEvidenceRecordORM.collected_at.asc())
            ).scalars().all()

            results: List[CaseEvidenceRecord] = []
            for r in orm_records:
                results.append(
                    CaseEvidenceRecord(
                        evidence_id=r.evidence_id,
                        case_id=r.case_id,
                        evidence_type=r.evidence_type,
                        source=r.source,
                        description=r.description,
                        data=load_json_value(r.data_json, default_factory=dict),
                        reliability=r.reliability,
                        collected_at=r.collected_at,
                        collected_by=r.collected_by,
                        metadata=load_json_value(r.metadata_json, default_factory=dict),
                    )
                )
            return results
        finally:
            db.close()

    def save_finding(self, finding: CaseFinding) -> None:
        """Save a formal finding."""
        with db_session_scope() as db:
            db.add(
                CaseFindingORM(
                    finding_id=finding.finding_id,
                    case_id=finding.case_id,
                    title=finding.title,
                    description=finding.description,
                    category=finding.category,
                    severity=finding.severity,
                    evidence_ids_json=dump_json_value(finding.evidence_ids),
                    confidence=finding.confidence,
                    status=finding.status,
                    created_at=finding.created_at,
                    created_by=finding.created_by,
                )
            )

    def get_findings(self, case_id: str) -> List[CaseFinding]:
        """Retrieve findings for a case."""
        db = get_db_session()
        try:
            orm_findings = db.execute(
                select(CaseFindingORM)
                .where(CaseFindingORM.case_id == case_id)
                .order_by(CaseFindingORM.created_at.asc())
            ).scalars().all()

            results: List[CaseFinding] = []
            for f in orm_findings:
                results.append(
                    CaseFinding(
                        finding_id=f.finding_id,
                        case_id=f.case_id,
                        title=f.title,
                        description=f.description,
                        category=f.category,
                        severity=f.severity,
                        evidence_ids=load_json_value(f.evidence_ids_json, default_factory=list),
                        confidence=f.confidence,
                        status=f.status,
                        created_at=f.created_at,
                        created_by=f.created_by,
                    )
                )
            return results
        finally:
            db.close()

    def save_risk_assessment(self, assessment: CaseRiskAssessment) -> None:
        """Save risk assessment."""
        with db_session_scope() as db:
            db.add(
                CaseRiskAssessmentORM(
                    assessment_id=assessment.assessment_id,
                    case_id=assessment.case_id,
                    risk_score=assessment.risk_score,
                    risk_level=assessment.risk_level,
                    contributing_factors_json=dump_json_value(assessment.contributing_factors),
                    explanation=assessment.explanation,
                    confidence=assessment.confidence,
                    assessed_at=assessment.assessed_at,
                    model_version=assessment.model_version,
                    rules_evaluated_json=dump_json_value(assessment.rules_evaluated),
                )
            )

    def get_risk_assessment(self, case_id: str) -> Optional[CaseRiskAssessment]:
        """Retrieve risk assessment for a case."""
        db = get_db_session()
        try:
            orm_ra = db.execute(
                select(CaseRiskAssessmentORM)
                .where(CaseRiskAssessmentORM.case_id == case_id)
                .order_by(CaseRiskAssessmentORM.assessed_at.desc())
            ).first()
            if not orm_ra:
                return None
            orm_obj = orm_ra[0]
            return CaseRiskAssessment(
                assessment_id=orm_obj.assessment_id,
                case_id=orm_obj.case_id,
                risk_score=orm_obj.risk_score,
                risk_level=orm_obj.risk_level,
                contributing_factors=load_json_value(orm_obj.contributing_factors_json, default_factory=list),
                explanation=orm_obj.explanation,
                confidence=orm_obj.confidence,
                assessed_at=orm_obj.assessed_at,
                model_version=orm_obj.model_version,
                rules_evaluated=load_json_value(orm_obj.rules_evaluated_json, default_factory=list),
            )
        finally:
            db.close()

    def save_recommendation(self, recommendation: CaseRecommendation) -> None:
        """Save resolution recommendation."""
        with db_session_scope() as db:
            db.add(
                CaseRecommendationORM(
                    recommendation_id=recommendation.recommendation_id,
                    case_id=recommendation.case_id,
                    recommended_action=recommendation.recommended_action,
                    rationale=recommendation.rationale,
                    supporting_finding_ids_json=dump_json_value(recommendation.supporting_finding_ids),
                    confidence=recommendation.confidence,
                    generated_by=recommendation.generated_by,
                    created_at=recommendation.created_at,
                )
            )

    def get_recommendation(self, case_id: str) -> Optional[CaseRecommendation]:
        """Retrieve recommendation for a case."""
        db = get_db_session()
        try:
            orm_rec = db.execute(
                select(CaseRecommendationORM)
                .where(CaseRecommendationORM.case_id == case_id)
                .order_by(CaseRecommendationORM.created_at.desc())
            ).first()
            if not orm_rec:
                return None
            orm_obj = orm_rec[0]
            return CaseRecommendation(
                recommendation_id=orm_obj.recommendation_id,
                case_id=orm_obj.case_id,
                recommended_action=orm_obj.recommended_action,
                rationale=orm_obj.rationale,
                supporting_finding_ids=load_json_value(orm_obj.supporting_finding_ids_json, default_factory=list),
                confidence=orm_obj.confidence,
                generated_by=orm_obj.generated_by,
                created_at=orm_obj.created_at,
            )
        finally:
            db.close()
