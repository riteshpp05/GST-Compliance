"""
app.case.service
================
Case Management & Workflow Service Orchestrator for UC15 (Sprint 13 & Sprint 15).
Manages case creation, triage, investigation planning, structured evidence collection, findings,
risk assessment, resolution recommendations, human review approvals, resolution, and closure.
Consumes outputs from existing S1–S14 engines without duplicating compliance, risk, or AI logic.
Reuses existing AIInvestigationAgent & SessionManager for re-investigation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.agent.ai.dossier import DossierBuilder, InvestigationDossier
from app.agent.ai.models import InvestigationRequest
from app.agent.ai.orchestrator import AIInvestigationAgent
from app.agent.ai.session import SessionManager, get_session_manager
from app.case.models import (
    CaseAssignment,
    CaseAssignRequest,
    CaseCreateRequest,
    CaseDecision,
    CaseDecisionEnum,
    CaseEvent,
    CaseEvidenceRecord,
    CaseEvidenceReference,
    CaseEventTypeEnum,
    CaseFinding,
    CaseRecommendation,
    CaseReviewRequest,
    CaseRiskAssessment,
    CaseStatusEnum,
    CaseTriageRequest,
    CaseTriageResult,
    EvidenceCreateRequest,
    FindingCreateRequest,
    InvestigationCase,
    InvestigationPlanCreateRequest,
    InvestigationPlanDomain,
    RecommendationCreateRequest,
    RiskAssessmentCreateRequest,
)
from app.case.repository import BaseCaseRepository, get_case_repository
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError
from app.domain.enums.risk_priority import RiskPriority
from app.infrastructure.logging import get_logger
from app.security import (
    AuthenticatedPrincipal,
    CaseAccessControl,
    PermissionEnum,
    PermissionEvaluator,
    get_internal_compatibility_principal,
)

logger = get_logger(__name__)


class CaseService:
    """
    Case Management Service orchestrating enterprise workflow, human reviews, case events,
    evidence, findings, risk assessment, recommendations, resolution, and audit trail.
    """

    def __init__(
        self,
        repository: Optional[BaseCaseRepository] = None,
        session_manager: Optional[SessionManager] = None,
        agent: Optional[AIInvestigationAgent] = None,
    ) -> None:
        self.repository = repository or get_case_repository()
        self.session_manager = session_manager or get_session_manager()
        self.agent = agent or AIInvestigationAgent(session_manager=self.session_manager)

    def _derive_priority_from_risk(self, risk_level: str, risk_score: float) -> str:
        """Derive case priority directly from existing RiskEngine levels without re-calculating risk."""
        rl_upper = (risk_level or "").upper()
        if rl_upper == "CRITICAL" or risk_score >= 80.0:
            return RiskPriority.P1.value
        elif rl_upper == "HIGH" or risk_score >= 50.0:
            return RiskPriority.P2.value
        elif rl_upper == "MEDIUM" or risk_score >= 25.0:
            return RiskPriority.P3.value
        return RiskPriority.P4.value

    def create_case(
        self,
        title: Any,
        description: str = "",
        invoice_id: Optional[str] = None,
        counterparty_gstin: Optional[str] = None,
        case_type: str = "GST_COMPLIANCE_INVESTIGATION",
        source: str = "MANUAL_ENTRY",
        assigned_to: Optional[str] = None,
        assigned_role: Optional[str] = None,
        created_by: str = "SYSTEM",
        session_id: Optional[str] = None,
        dossier_id: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """
        Create a new enterprise InvestigationCase.
        Safe against duplicates and initializes in CREATED status.
        """
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.CASE_CREATE)

        if isinstance(title, CaseCreateRequest):
            req = title
            invoice_id = req.invoice_id or invoice_id
            counterparty_gstin = req.counterparty_gstin or counterparty_gstin
            case_type = req.case_type or case_type
            source = req.source or source
            assigned_to = req.assigned_to or assigned_to
            assigned_role = req.assigned_role or assigned_role
            created_by = req.created_by or created_by
            session_id = req.session_id or session_id
            dossier_id = req.dossier_id or dossier_id
            description = req.description or description
            title = req.title or (f"GST Compliance Review: {invoice_id}" if invoice_id else "GST Compliance Investigation")

        case = InvestigationCase(
            title=title,
            description=description,
            status=CaseStatusEnum.CREATED,
            priority="P3",
            risk_level="LOW",
            case_type=case_type,
            source=source,
            tenant_id=eff_principal.tenant_id,
            invoice_id=invoice_id,
            counterparty_gstin=counterparty_gstin,
            source_session_id=session_id,
            source_dossier_id=dossier_id,
            assigned_to=assigned_to,
            assigned_role=assigned_role or "Tax Analyst",
            created_by=created_by,
        )

        self.repository.save_case(case)

        event = CaseEvent(
            case_id=case.case_id,
            event_type=CaseEventTypeEnum.CASE_CREATED,
            actor=created_by,
            new_status=CaseStatusEnum.CREATED.value,
            metadata={
                "case_type": case_type,
                "source": source,
                "invoice_id": invoice_id,
                "counterparty_gstin": counterparty_gstin,
            },
        )
        self.repository.save_event(event)
        logger.info(f"Created InvestigationCase '{case.case_id}' (Status: CREATED)")
        return case

    def create_case_from_dossier(
        self,
        dossier: InvestigationDossier,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[str] = None,
        assigned_role: Optional[str] = None,
        created_by: str = "SYSTEM",
    ) -> InvestigationCase:
        """
        Create a new operational InvestigationCase consuming an existing InvestigationDossier.
        Extracts gate breakdown, risk assessment, financial exposure, root cause, blast radius,
        and regulatory evidence references.
        """
        invoice_id = dossier.entity_focus.invoice_id
        gstin = dossier.entity_focus.counterparty_gstin
        party_name = dossier.entity_focus.counterparty_name

        risk_data = dossier.risk_assessment or {}
        risk_level = risk_data.get("risk_level") or dossier.entity_focus.risk_level or "LOW"
        risk_score = float(risk_data.get("risk_score") or 0.0)
        priority = risk_data.get("risk_priority") or self._derive_priority_from_risk(risk_level, risk_score)

        fin_data = dossier.financial_exposure or {}
        exposure_amt = float(fin_data.get("total_potential_exposure") or fin_data.get("itc_at_risk") or 0.0)

        rc_data = dossier.root_cause_analysis or {}
        root_cause = rc_data.get("primary_root_cause") or "UNDETERMINED"
        blast_radius = dossier.blast_radius_analysis or {}

        case_title = title or f"GST Compliance Review: {invoice_id or party_name or 'Portfolio Investigation'}"
        case_desc = description or dossier.executive_summary

        # Build evidence references from dossier
        evidence_refs: List[CaseEvidenceReference] = []

        # Gate evidence
        for gate in dossier.gate_breakdown:
            g_no = gate.get('gate') if isinstance(gate, dict) else getattr(gate, 'gate_no', getattr(gate, 'gate', 1))
            g_no = g_no or (gate.get('gate_no') if isinstance(gate, dict) else 1)
            g_name = (gate.get('name') if isinstance(gate, dict) else getattr(gate, 'name', f"Gate {g_no}")) or f"Gate {g_no}"
            g_st = (gate.get('status') or gate.get('result') if isinstance(gate, dict) else getattr(gate, 'status', 'UNKNOWN')) or 'UNKNOWN'
            g_msg = (gate.get('detail') or gate.get('details') or gate.get('message') if isinstance(gate, dict) else getattr(gate, 'message', getattr(gate, 'detail', ''))) or 'Validated against statutory rules.'
            evidence_refs.append(
                CaseEvidenceReference(
                    source_type="GATE_DETERMINATION",
                    source_identifier=f"Gate-{g_no}",
                    invoice_id=invoice_id,
                    gate_id=str(g_no),
                    dossier_id=dossier.dossier_id,
                    session_id=dossier.session_id,
                    summary=f"Gate {g_no} [{g_st}] {g_name}: {g_msg}",
                )
            )

        # Regulatory knowledge evidence
        for reg in dossier.regulatory_evidence:
            provenance = reg.get("provenance") or {}
            chunk = reg.get("chunk") or {}
            doc_id = provenance.get("document_id") or reg.get("document_id")
            sec = provenance.get("section") or reg.get("section")
            evidence_refs.append(
                CaseEvidenceReference(
                    source_type="REGULATORY_KNOWLEDGE",
                    source_identifier=doc_id or "REGULATORY_DOC",
                    invoice_id=invoice_id,
                    dossier_id=dossier.dossier_id,
                    session_id=dossier.session_id,
                    document_id=doc_id,
                    section=sec,
                    relevance_score=reg.get("relevance_score"),
                    summary=f"Regulatory Citation: {provenance.get('document_name') or doc_id} - Section {sec}: {chunk.get('content') or str(reg)}",
                )
            )

        if not evidence_refs:
            evidence_refs.append(
                CaseEvidenceReference(
                    source_type="SESSION_DOSSIER",
                    source_identifier=dossier.dossier_id,
                    invoice_id=invoice_id,
                    dossier_id=dossier.dossier_id,
                    session_id=dossier.session_id,
                    summary=f"Dossier investigation snapshot created for session {dossier.session_id}",
                )
            )

        # AI Recommendation formatting with mandatory advisory banner
        rec_lines = dossier.advisory_recommendations or []
        rec_text = "\n".join(rec_lines) if rec_lines else "[ADVISORY SAP / FINANCE ACTION]\nReview compliance findings and hold invoice from filing pending clarification."
        if "[ADVISORY SAP / FINANCE ACTION]" not in rec_text:
            rec_text = f"[ADVISORY SAP / FINANCE ACTION]\n{rec_text}"

        # Build compliance context snapshot for historical reproducibility
        context_snapshot = {
            "evaluation_timestamp": dossier.generated_at,
            "gate_breakdown": dossier.gate_breakdown,
            "regulatory_evidence": dossier.regulatory_evidence,
            "entity_focus": dossier.entity_focus.model_dump() if hasattr(dossier.entity_focus, "model_dump") else str(dossier.entity_focus),
            "engine_version": "2.0",
        }

        case = InvestigationCase(
            title=case_title,
            description=case_desc,
            status=CaseStatusEnum.REVIEW_REQUIRED,
            priority=priority,
            risk_level=risk_level,
            source_session_id=dossier.session_id,
            source_dossier_id=dossier.dossier_id,
            invoice_id=invoice_id,
            counterparty_gstin=gstin,
            counterparty_name=party_name,
            assigned_to=assigned_to,
            assigned_role=assigned_role or "Tax Analyst",
            created_by=created_by,
            recommendation=rec_text,
            financial_exposure=exposure_amt,
            root_cause=root_cause,
            blast_radius=blast_radius,
            evidence_references=evidence_refs,
            compliance_context_snapshot=context_snapshot,
        )

        self.repository.save_case(case)

        # Record CASE_CREATED event
        event = CaseEvent(
            case_id=case.case_id,
            event_type=CaseEventTypeEnum.CASE_CREATED,
            actor=created_by,
            new_status=CaseStatusEnum.REVIEW_REQUIRED.value,
            metadata={
                "source_session_id": dossier.session_id,
                "source_dossier_id": dossier.dossier_id,
                "invoice_id": invoice_id,
                "risk_level": risk_level,
                "priority": priority,
            },
        )
        self.repository.save_event(event)
        logger.info(f"Created InvestigationCase '{case.case_id}' from dossier '{dossier.dossier_id}' (Status: REVIEW_REQUIRED)")
        return case

    def create_case_from_session(
        self,
        session_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        assigned_to: Optional[str] = None,
        assigned_role: Optional[str] = None,
        created_by: str = "SYSTEM",
    ) -> InvestigationCase:
        """
        Create an InvestigationCase from an investigation session by first building its Dossier.
        """
        sess = self.session_manager.get_session(session_id)
        if not sess:
            raise ValueError(f"Investigation session '{session_id}' not found.")
        dossier = DossierBuilder.build_dossier(sess)
        return self.create_case_from_dossier(
            dossier=dossier,
            title=title,
            description=description,
            assigned_to=assigned_to,
            assigned_role=assigned_role,
            created_by=created_by,
        )

    def triage_case(
        self,
        case_id: str,
        category: Any = "INPUT_TAX_CREDIT_ANOMALY",
        priority: Optional[str] = None,
        risk_level: Optional[str] = None,
        investigation_scope: str = "FULL_AUDIT",
        assigned_to: Optional[str] = None,
        requires_escalation: bool = False,
        actor: str = "SYSTEM_TRIAGE",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> CaseTriageResult:
        """
        Perform case triage stage.
        Determines priority, risk level, category, and investigation scope.
        Transitions case status to TRIAGED (or ESCALATED if required).
        """
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(category, CaseTriageRequest):
            req = category
            priority = req.priority or priority
            risk_level = req.risk_level or risk_level
            category_val = req.category or "INPUT_TAX_CREDIT_ANOMALY"
            investigation_scope = req.investigation_scope or investigation_scope
            assigned_to = req.assigned_to or assigned_to
            requires_escalation = req.requires_escalation if req.requires_escalation is not None else requires_escalation
            actor = req.actor or actor
            category = category_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.CASE_TRIAGE)

        target_status = CaseStatusEnum.ESCALATED if requires_escalation else CaseStatusEnum.TRIAGED

        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=target_status,
            actor_is_ai=False,
        )

        prev_status = case.status.value

        if priority:
            case.priority = priority
        if risk_level:
            case.risk_level = risk_level
        if assigned_to:
            case.assigned_to = assigned_to

        case.status = target_status
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        triage_result = CaseTriageResult(
            case_id=case_id,
            priority=case.priority,
            risk_level=case.risk_level,
            category=str(category),
            investigation_scope=investigation_scope,
            assigned_to=case.assigned_to,
            requires_escalation=requires_escalation,
            triaged_by=actor,
        )

        event = CaseEvent(
            case_id=case_id,
            event_type=CaseEventTypeEnum.CASE_TRIAGED,
            actor=actor,
            previous_status=prev_status,
            new_status=target_status.value,
            metadata=triage_result.model_dump(),
        )
        self.repository.save_event(event)

        logger.info(f"Triaged case '{case_id}': Priority={case.priority}, Risk={case.risk_level}, Status={target_status.value}")
        return triage_result

    def create_investigation_plan(
        self,
        case_id: str,
        objective: Any,
        questions: Optional[List[str]] = None,
        required_data: Optional[List[str]] = None,
        expected_evidence: Optional[List[str]] = None,
        analysis_tasks: Optional[List[str]] = None,
        risk_areas: Optional[List[str]] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationPlanDomain:
        """Create and persist a structured investigation plan for a case."""
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(objective, InvestigationPlanCreateRequest):
            req = objective
            objective_val = req.objective
            questions = req.questions or questions
            required_data = req.required_data or required_data
            expected_evidence = req.expected_evidence or expected_evidence
            analysis_tasks = req.analysis_tasks or analysis_tasks
            risk_areas = req.risk_areas or risk_areas
            objective = objective_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.INVESTIGATION_PLAN_CREATE)

        plan = InvestigationPlanDomain(
            case_id=case_id,
            objective=objective,
            questions=questions or [],
            required_data=required_data or [],
            expected_evidence=expected_evidence or [],
            analysis_tasks=analysis_tasks or [],
            risk_areas=risk_areas or [],
        )

        self.repository.save_plan(plan)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.PLAN_CREATED,
                actor="INVESTIGATION_PLANNER",
                metadata={"plan_id": plan.plan_id, "objective": objective},
            )
        )
        logger.info(f"Created investigation plan '{plan.plan_id}' for case '{case_id}'")
        return plan

    def get_investigation_plan(self, case_id: str) -> Optional[InvestigationPlanDomain]:
        """Retrieve investigation plan for a case."""
        return self.repository.get_plan(case_id)

    def start_investigation(
        self,
        case_id: str,
        actor: str = "SYSTEM_WORKFLOW",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """Transition case status to INVESTIGATING."""
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.INVESTIGATION_START)

        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=CaseStatusEnum.INVESTIGATING,
            actor_is_ai=False,
        )

        prev_status = case.status.value
        case.status = CaseStatusEnum.INVESTIGATING
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.INVESTIGATION_STARTED,
                actor=actor,
                previous_status=prev_status,
                new_status=CaseStatusEnum.INVESTIGATING.value,
            )
        )
        logger.info(f"Started investigation for case '{case_id}'")
        return case

    def update_case_status(
        self,
        case_id: str,
        target_status: Union[CaseStatusEnum, str],
        actor: str = "SYSTEM_WORKFLOW",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """Update investigation case status directly with state machine validation."""
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        new_status = CaseStatusEnum(target_status) if isinstance(target_status, str) else target_status
        if case.status == new_status:
            return case

        prev_status = case.status.value if isinstance(case.status, CaseStatusEnum) else str(case.status)
        actor_is_ai = eff_principal.has_role("AI_AGENT") and not eff_principal.has_role("ADMIN") and not eff_principal.has_role("REVIEWER")

        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=new_status,
            actor_is_ai=actor_is_ai,
        )

        case.status = new_status
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.STATUS_CHANGED,
                actor=actor,
                previous_status=prev_status,
                new_status=new_status.value,
            )
        )
        logger.info(f"Updated status for case '{case_id}': {prev_status} -> {new_status.value}")
        return case

    def add_evidence(
        self,
        case_id: str,
        evidence_type: Any,
        source: str = "",
        description: str = "",
        data: Optional[Dict[str, Any]] = None,
        reliability: float = 1.0,
        collected_by: str = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> CaseEvidenceRecord:
        """Add structured evidence record to a case and advance status to EVIDENCE_COLLECTED if investigating."""
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(evidence_type, EvidenceCreateRequest):
            req = evidence_type
            evidence_type_val = req.evidence_type
            source = req.source or source
            description = req.description or description
            data = req.data or data
            reliability = req.reliability if req.reliability is not None else reliability
            collected_by = req.collected_by or collected_by
            metadata = req.metadata or metadata
            evidence_type = evidence_type_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.EVIDENCE_CREATE)

        record = CaseEvidenceRecord(
            case_id=case_id,
            evidence_type=str(evidence_type),
            source=source,
            description=description,
            data=data or {},
            reliability=reliability,
            collected_by=collected_by,
            metadata=metadata or {},
        )
        self.repository.save_evidence_record(record)

        # Transition status to EVIDENCE_COLLECTED if currently in INVESTIGATING
        if case.status == CaseStatusEnum.INVESTIGATING:
            CaseStateMachine.validate_transition(
                current_status=case.status,
                target_status=CaseStatusEnum.EVIDENCE_COLLECTED,
                actor_is_ai=False,
            )
            case.status = CaseStatusEnum.EVIDENCE_COLLECTED
            case.updated_at = datetime.now(timezone.utc).isoformat()
            self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.EVIDENCE_ADDED,
                actor=collected_by,
                new_status=case.status.value,
                metadata={"evidence_id": record.evidence_id, "evidence_type": str(evidence_type), "source": source},
            )
        )
        logger.info(f"Added evidence '{record.evidence_id}' to case '{case_id}'")
        return record

    def get_evidence_records(self, case_id: str) -> List[CaseEvidenceRecord]:
        """Retrieve all structured evidence records for a case."""
        return self.repository.get_evidence_records(case_id)

    def add_finding(
        self,
        case_id: str,
        title: Any,
        description: str = "",
        category: str = "COMPLIANCE_MISMATCH",
        severity: str = "HIGH",
        evidence_ids: Optional[List[str]] = None,
        confidence: float = 1.0,
        created_by: str = "SYSTEM",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> CaseFinding:
        """Record formal finding and advance status to FINDINGS_READY."""
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(title, FindingCreateRequest):
            req = title
            title_val = req.title
            description = req.description or description
            category = req.category or category
            severity = req.severity or severity
            evidence_ids = req.evidence_ids or evidence_ids
            confidence = req.confidence if req.confidence is not None else confidence
            created_by = req.created_by or created_by
            title = title_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.FINDING_CREATE)

        finding = CaseFinding(
            case_id=case_id,
            title=str(title),
            description=description,
            category=category,
            severity=severity,
            evidence_ids=evidence_ids or [],
            confidence=confidence,
            created_by=created_by,
        )
        self.repository.save_finding(finding)

        if case.status in {CaseStatusEnum.EVIDENCE_COLLECTED, CaseStatusEnum.INVESTIGATING}:
            CaseStateMachine.validate_transition(
                current_status=case.status,
                target_status=CaseStatusEnum.FINDINGS_READY,
                actor_is_ai=False,
            )
            case.status = CaseStatusEnum.FINDINGS_READY
            case.updated_at = datetime.now(timezone.utc).isoformat()
            self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.FINDING_CREATED,
                actor=created_by,
                new_status=case.status.value,
                metadata={"finding_id": finding.finding_id, "severity": severity, "title": str(title)},
            )
        )
        logger.info(f"Recorded finding '{finding.finding_id}' for case '{case_id}'")
        return finding

    def get_findings(self, case_id: str) -> List[CaseFinding]:
        """Retrieve formal findings for a case."""
        return self.repository.get_findings(case_id)

    def assess_risk(
        self,
        case_id: str,
        risk_score: Any,
        risk_level: str = "LOW",
        contributing_factors: Optional[List[str]] = None,
        explanation: str = "",
        confidence: float = 1.0,
        model_version: str = "1.0",
        rules_evaluated: Optional[List[str]] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> CaseRiskAssessment:
        """Record risk assessment for a case."""
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(risk_score, RiskAssessmentCreateRequest):
            req = risk_score
            risk_score_val = req.risk_score
            risk_level = req.risk_level or risk_level
            contributing_factors = req.contributing_factors or contributing_factors
            explanation = req.explanation or explanation
            confidence = req.confidence if req.confidence is not None else confidence
            model_version = req.model_version or model_version
            rules_evaluated = req.rules_evaluated or rules_evaluated
            risk_score = risk_score_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.RISK_ASSESS)

        assessment = CaseRiskAssessment(
            case_id=case_id,
            risk_score=float(risk_score),
            risk_level=risk_level,
            contributing_factors=contributing_factors or [],
            explanation=explanation,
            confidence=confidence,
            model_version=model_version,
            rules_evaluated=rules_evaluated or [],
        )
        self.repository.save_risk_assessment(assessment)

        case.risk_level = risk_level
        case.priority = self._derive_priority_from_risk(risk_level, float(risk_score))
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.RISK_ASSESSED,
                actor="RISK_ENGINE",
                metadata={"assessment_id": assessment.assessment_id, "risk_score": float(risk_score), "risk_level": risk_level},
            )
        )
        logger.info(f"Assessed risk for case '{case_id}': Level={risk_level}, Score={risk_score}")
        return assessment

    def get_risk_assessment(self, case_id: str) -> Optional[CaseRiskAssessment]:
        """Retrieve risk assessment for a case."""
        return self.repository.get_risk_assessment(case_id)

    def propose_recommendation(
        self,
        case_id: str,
        recommended_action: Any,
        rationale: str = "",
        supporting_finding_ids: Optional[List[str]] = None,
        confidence: float = 1.0,
        generated_by: str = "AI_AGENT",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> CaseRecommendation:
        """Propose resolution recommendation and advance status to RESOLUTION_PROPOSED or PENDING_REVIEW."""
        eff_principal = principal or get_internal_compatibility_principal()

        if isinstance(recommended_action, RecommendationCreateRequest):
            req = recommended_action
            recommended_action_val = req.recommended_action
            rationale = req.rationale or rationale
            supporting_finding_ids = req.supporting_finding_ids or supporting_finding_ids
            confidence = req.confidence if req.confidence is not None else confidence
            generated_by = req.generated_by or generated_by
            recommended_action = recommended_action_val

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.RECOMMENDATION_CREATE)

        rec = CaseRecommendation(
            case_id=case_id,
            recommended_action=str(recommended_action),
            rationale=rationale,
            supporting_finding_ids=supporting_finding_ids or [],
            confidence=confidence,
            generated_by=generated_by,
        )
        self.repository.save_recommendation(rec)

        case.recommendation = f"[ADVISORY RECOMMENDATION: {recommended_action}]\n{rationale}"

        if case.status in {CaseStatusEnum.FINDINGS_READY, CaseStatusEnum.EVIDENCE_COLLECTED, CaseStatusEnum.INVESTIGATING}:
            CaseStateMachine.validate_transition(
                current_status=case.status,
                target_status=CaseStatusEnum.RESOLUTION_PROPOSED,
                actor_is_ai=False,
            )
            case.status = CaseStatusEnum.RESOLUTION_PROPOSED
            case.updated_at = datetime.now(timezone.utc).isoformat()
            self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.RECOMMENDATION_CREATED,
                actor=generated_by,
                new_status=case.status.value,
                metadata={"recommendation_id": rec.recommendation_id, "action": str(recommended_action)},
            )
        )
        logger.info(f"Proposed recommendation '{rec.recommendation_id}' for case '{case_id}' (Action: {recommended_action})")
        return rec

    def get_recommendation(self, case_id: str) -> Optional[CaseRecommendation]:
        """Retrieve recommendation for a case."""
        return self.repository.get_recommendation(case_id)

    def get_case(self, case_id: str, principal: Optional[AuthenticatedPrincipal] = None) -> Optional[InvestigationCase]:
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.repository.get_case(case_id)
        if case:
            CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.CASE_READ)
        return case

    def list_cases(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        invoice_id: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> List[InvestigationCase]:
        eff_principal = principal or get_internal_compatibility_principal()
        cases = self.repository.list_cases(status=status, priority=priority, invoice_id=invoice_id)
        return [c for c in cases if CaseAccessControl.can_access_case(eff_principal, c, PermissionEnum.CASE_LIST)]

    def assign_case(
        self,
        case_id: str,
        assigned_to: str,
        assigned_role: Optional[str] = "Tax Analyst",
        assigned_by: str = "SYSTEM",
        reason: str = "",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """Assign or reassign an InvestigationCase to a human reviewer/analyst."""
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.CASE_ASSIGN)

        prev_assignee = case.assigned_to
        case.assigned_to = assigned_to
        case.assigned_role = assigned_role or "Tax Analyst"
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        event = CaseEvent(
            case_id=case_id,
            event_type=CaseEventTypeEnum.ASSIGNED,
            actor=assigned_by,
            metadata={
                "previous_assignee": prev_assignee,
                "new_assignee": assigned_to,
                "role": assigned_role,
                "reason": reason,
            },
        )
        self.repository.save_event(event)
        logger.info(f"Assigned case '{case_id}' to '{assigned_to}' ({assigned_role})")
        return case

    def submit_human_review(
        self,
        case_id: str,
        reviewer: str,
        decision: CaseDecisionEnum,
        comment: str,
        reviewer_role: Optional[str] = "Finance Manager",
        requested_evidence: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """
        Process explicit human review decision.
        Validates state machine transitions, records CaseDecision, logs audit events,
        and advances case lifecycle state.
        """
        eff_principal = principal or get_internal_compatibility_principal()

        if decision == CaseDecisionEnum.APPROVE:
            req_perm = PermissionEnum.APPROVE_CASE
        elif decision == CaseDecisionEnum.REJECT:
            req_perm = PermissionEnum.REJECT_CASE
        elif decision in (CaseDecisionEnum.REQUEST_MORE_EVIDENCE, CaseDecisionEnum.RETURN_FOR_INVESTIGATION):
            req_perm = PermissionEnum.REQUEST_MORE_EVIDENCE
        else:
            req_perm = PermissionEnum.REVIEW_SUBMIT

        PermissionEvaluator.check_permission(eff_principal, req_perm)

        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, req_perm)

        if not reviewer or not reviewer.strip():
            raise CaseStateTransitionError("Reviewer identity must be explicitly provided.")
        if not comment or not comment.strip():
            raise CaseStateTransitionError("Review decision requires a non-empty comment / rationale.")

        # Determine target status from decision
        if decision == CaseDecisionEnum.APPROVE:
            target_status = CaseStatusEnum.APPROVED
        elif decision == CaseDecisionEnum.REJECT:
            target_status = CaseStatusEnum.REJECTED
        elif decision == CaseDecisionEnum.REQUEST_MORE_EVIDENCE:
            target_status = CaseStatusEnum.MORE_EVIDENCE_REQUIRED
        elif decision == CaseDecisionEnum.RETURN_FOR_INVESTIGATION:
            target_status = CaseStatusEnum.RETURNED_FOR_INVESTIGATION
        else:
            raise CaseStateTransitionError(f"Unsupported decision enum '{decision}'.")

        # Validate state transition
        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=target_status,
            decision=decision,
            reviewer=reviewer,
            actor_is_ai=False,
        )

        prev_status = case.status.value

        # Record CaseDecision
        decision_obj = CaseDecision(
            case_id=case_id,
            reviewer=reviewer,
            reviewer_role=reviewer_role or "Finance Manager",
            decision=decision,
            comment=comment,
            requested_evidence=requested_evidence,
            evidence_reviewed=[r.reference_id for r in case.evidence_references],
        )
        case.decisions.append(decision_obj)

        # Update case status
        case.status = target_status
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        # Record Decision Event
        if decision == CaseDecisionEnum.APPROVE:
            evt_type = CaseEventTypeEnum.APPROVED
        elif decision == CaseDecisionEnum.REJECT:
            evt_type = CaseEventTypeEnum.REJECTED
        elif decision == CaseDecisionEnum.REQUEST_MORE_EVIDENCE:
            evt_type = CaseEventTypeEnum.MORE_EVIDENCE_REQUESTED
        else:
            evt_type = CaseEventTypeEnum.RETURNED_FOR_INVESTIGATION

        event = CaseEvent(
            case_id=case_id,
            event_type=evt_type,
            actor=reviewer,
            previous_status=prev_status,
            new_status=target_status.value,
            metadata={
                "reviewer_role": reviewer_role,
                "comment": comment,
                "requested_evidence": requested_evidence,
            },
        )
        self.repository.save_event(event)

        # If APPROVED, automatically follow-through transition to READY_FOR_RESOLUTION
        if target_status == CaseStatusEnum.APPROVED:
            CaseStateMachine.validate_transition(
                current_status=case.status,
                target_status=CaseStatusEnum.READY_FOR_RESOLUTION,
                actor_is_ai=False,
            )
            case.status = CaseStatusEnum.READY_FOR_RESOLUTION
            case.updated_at = datetime.now(timezone.utc).isoformat()
            self.repository.save_case(case)

            resolution_event = CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.STATUS_CHANGED,
                actor="SYSTEM_WORKFLOW",
                previous_status=CaseStatusEnum.APPROVED.value,
                new_status=CaseStatusEnum.READY_FOR_RESOLUTION.value,
                metadata={"reason": "Automatic lifecycle progression post human approval."},
            )
            self.repository.save_event(resolution_event)

        logger.info(f"Human review submitted for case '{case_id}': Decision={decision.value}, New Status={case.status.value}")
        return case

    def request_more_evidence_workflow(
        self,
        case_id: str,
        reviewer: str,
        comment: str,
        requested_evidence_details: str,
        reviewer_role: Optional[str] = "Finance Manager",
    ) -> InvestigationCase:
        """
        Controlled More-Evidence Workflow:
          1. Validates human decision -> MORE_EVIDENCE_REQUIRED
          2. Moves status to INVESTIGATING
          3. Invokes S12.4 AIInvestigationAgent on source_session_id for additional evidence
          4. Accumulates new evidence references on case
          5. Re-evaluates case summary / recommendation
          6. Returns status to REVIEW_REQUIRED for human review
        """
        # Step 1: Submit human review decision to set MORE_EVIDENCE_REQUIRED
        case = self.submit_human_review(
            case_id=case_id,
            reviewer=reviewer,
            decision=CaseDecisionEnum.REQUEST_MORE_EVIDENCE,
            comment=comment,
            reviewer_role=reviewer_role,
            requested_evidence=requested_evidence_details,
        )

        # Step 2: Transition status to INVESTIGATING
        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=CaseStatusEnum.INVESTIGATING,
            actor_is_ai=False,
        )
        case.status = CaseStatusEnum.INVESTIGATING
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.STATUS_CHANGED,
                actor="SYSTEM_WORKFLOW",
                previous_status=CaseStatusEnum.MORE_EVIDENCE_REQUIRED.value,
                new_status=CaseStatusEnum.INVESTIGATING.value,
                metadata={"requested_evidence": requested_evidence_details},
            )
        )

        # Step 3: Reuse S12.4 AIInvestigationAgent & SessionManager to perform additional investigation
        if case.source_session_id:
            query = f"Investigate additional requested evidence: {requested_evidence_details}"
            req = InvestigationRequest(user_query=query, session_id=case.source_session_id)
            resp = self.agent.investigate(req)

            # Step 4: Extract new evidence from response & updated session
            updated_sess = self.session_manager.get_session(case.source_session_id)
            if updated_sess:
                # Add newly retrieved knowledge evidence items as CaseEvidenceReference
                for item in resp.knowledge_evidence:
                    doc_id = item.get("document_id") or item.get("provenance", {}).get("document_id")
                    sec = item.get("section") or item.get("provenance", {}).get("section")
                    ref = CaseEvidenceReference(
                        source_type="ADDITIONAL_REGULATORY_EVIDENCE",
                        source_identifier=doc_id or "ADDITIONAL_DOC",
                        invoice_id=case.invoice_id,
                        dossier_id=case.source_dossier_id,
                        session_id=case.source_session_id,
                        document_id=doc_id,
                        section=sec,
                        summary=f"Additional Evidence: {item.get('content') or item.get('chunk', {}).get('content') or str(item)}",
                    )
                    case.evidence_references.append(ref)

                # Update dossier and recommendation
                updated_dossier = DossierBuilder.build_dossier(updated_sess)
                case.source_dossier_id = updated_dossier.dossier_id
                rec_lines = updated_dossier.advisory_recommendations or []
                rec_text = "\n".join(rec_lines) if rec_lines else case.recommendation
                if "[ADVISORY SAP / FINANCE ACTION]" not in rec_text:
                    rec_text = f"[ADVISORY SAP / FINANCE ACTION]\n{rec_text}"
                case.recommendation = rec_text

            self.repository.save_event(
                CaseEvent(
                    case_id=case_id,
                    event_type=CaseEventTypeEnum.EVIDENCE_ADDED,
                    actor="AI_INVESTIGATION_AGENT",
                    metadata={"query": query, "tools_used": resp.tools_used},
                )
            )

        # Step 5: Transition status back to REVIEW_REQUIRED / PENDING_REVIEW
        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=CaseStatusEnum.REVIEW_REQUIRED,
            actor_is_ai=False,
        )
        case.status = CaseStatusEnum.REVIEW_REQUIRED
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.STATUS_CHANGED,
                actor="SYSTEM_WORKFLOW",
                previous_status=CaseStatusEnum.INVESTIGATING.value,
                new_status=CaseStatusEnum.REVIEW_REQUIRED.value,
                metadata={"reason": "Additional evidence investigation complete. Ready for re-review."},
            )
        )

        logger.info(f"Completed More-Evidence Workflow for case '{case_id}'. New Status: REVIEW_REQUIRED")
        return case

    def resolve_case(
        self,
        case_id: str,
        actor: str = "FINANCE_LEAD",
        resolution_comment: str = "Case resolved following human review approval.",
        resolution_summary: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """Resolve an approved case and transition status to RESOLVED."""
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.RESOLVE_CASE)

        comment_text = resolution_summary or resolution_comment

        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=CaseStatusEnum.RESOLVED,
            actor_is_ai=False,
        )

        prev_status = case.status.value
        case.status = CaseStatusEnum.RESOLVED
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.CASE_RESOLVED,
                actor=actor,
                previous_status=prev_status,
                new_status=CaseStatusEnum.RESOLVED.value,
                metadata={"comment": comment_text},
            )
        )
        logger.info(f"Resolved case '{case_id}'")
        return case

    def close_case(
        self,
        case_id: str,
        actor: str = "SYSTEM_ADMIN",
        close_reason: str = "Case closed.",
        closure_notes: Optional[str] = None,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationCase:
        """Close a case in terminal status CLOSED."""
        eff_principal = principal or get_internal_compatibility_principal()
        case = self.get_case(case_id, principal=eff_principal)
        if not case:
            raise ValueError(f"InvestigationCase '{case_id}' not found.")

        CaseAccessControl.check_case_access(eff_principal, case, PermissionEnum.CLOSE_CASE)

        reason_text = closure_notes or close_reason

        CaseStateMachine.validate_transition(
            current_status=case.status,
            target_status=CaseStatusEnum.CLOSED,
            actor_is_ai=False,
        )

        prev_status = case.status.value
        case.status = CaseStatusEnum.CLOSED
        case.updated_at = datetime.now(timezone.utc).isoformat()
        self.repository.save_case(case)

        self.repository.save_event(
            CaseEvent(
                case_id=case_id,
                event_type=CaseEventTypeEnum.CASE_CLOSED,
                actor=actor,
                previous_status=prev_status,
                new_status=CaseStatusEnum.CLOSED.value,
                metadata={"reason": reason_text},
            )
        )
        logger.info(f"Closed case '{case_id}'")
        return case

    def get_timeline(self, case_id: str) -> List[CaseEvent]:
        """Retrieve chronological event history for a case."""
        return self.repository.get_events(case_id)

    def get_case_timeline(self, case_id: str) -> List[CaseEvent]:
        """Alias for get_timeline."""
        return self.get_timeline(case_id)

    def get_evidence(self, case_id: str) -> List[CaseEvidenceReference]:
        """Retrieve linked evidence references for a case."""
        case = self.get_case(case_id)
        return case.evidence_references if case else []


# Global singleton instance
_case_service: Optional[CaseService] = None


def get_case_service() -> CaseService:
    global _case_service
    if _case_service is None:
        _case_service = CaseService()
    return _case_service


def reset_case_service() -> None:
    global _case_service
    _case_service = None
