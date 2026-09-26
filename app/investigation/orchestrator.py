"""
app.investigation.orchestrator
==============================
Enterprise Investigation Orchestrator for UC15 (Sprint 18).
Orchestrates dependency graph execution, adaptive loop expansion, secure tool invocation,
evidence collection, finding consolidation, conflict detection, confidence calculation,
and case workflow integration.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.agent.ai.executor import ToolExecutor
from app.agent.ai.registry import ToolRegistry, get_global_tool_registry
from app.case.models import CaseEvidenceRecord, CaseFinding, CaseStatusEnum, InvestigationCase
from app.case.service import CaseService, get_case_service
from app.infrastructure.logging import get_logger
from app.investigation.confidence import ConfidenceLevelEnum, InvestigationConfidenceEngine
from app.investigation.consolidation import FindingConsolidationService
from app.investigation.evidence import EvidenceManager, EvidenceStrengthEnum
from app.investigation.explainability import InvestigationExplainer, StructuredExplanation
from app.investigation.graph import InvestigationGraph
from app.investigation.plan import (
    InvestigationBudget,
    InvestigationPlan,
    InvestigationStep,
    StepResultStatusEnum,
)
from app.investigation.trace import InvestigationTraceTracker
from app.security import AuthenticatedPrincipal, get_internal_compatibility_principal

logger = get_logger(__name__)

_GLOBAL_ORCHESTRATOR: Optional[EnterpriseInvestigationOrchestrator] = None


def get_enterprise_orchestrator() -> EnterpriseInvestigationOrchestrator:
    """Singleton getter for EnterpriseInvestigationOrchestrator."""
    global _GLOBAL_ORCHESTRATOR
    if _GLOBAL_ORCHESTRATOR is None:
        _GLOBAL_ORCHESTRATOR = EnterpriseInvestigationOrchestrator()
    return _GLOBAL_ORCHESTRATOR


class EnterpriseInvestigationOrchestrator:
    """
    Primary Enterprise Orchestrator combining investigation planning, dependency execution,
    adaptive investigation, evidence provenance, finding consolidation, and review packaging.
    """

    def __init__(
        self,
        case_service: Optional[CaseService] = None,
        executor: Optional[ToolExecutor] = None,
        registry: Optional[ToolRegistry] = None,
    ) -> None:
        self.case_service = case_service or get_case_service()
        self.registry = registry or get_global_tool_registry()
        self.executor = executor or ToolExecutor(registry=self.registry)
        self.confidence_engine = InvestigationConfidenceEngine()
        self.consolidation_service = FindingConsolidationService()
        self.explainer = InvestigationExplainer()

    def create_plan(
        self,
        case_id: str,
        objective: str,
        invoice_id: Optional[str] = None,
        tenant_id: str = "tenant_default",
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> InvestigationPlan:
        """Create a new dependency-aware investigation plan."""
        plan = InvestigationGraph.build_default_plan(
            case_id=case_id,
            objective=objective,
            invoice_id=invoice_id,
            tenant_id=tenant_id,
        )
        logger.info(f"Created investigation plan '{plan.plan_id}' with {len(plan.steps)} steps for case '{case_id}'.")
        return plan

    def execute_investigation(
        self,
        plan: InvestigationPlan,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> Dict[str, Any]:
        """
        Execute an investigation plan bounded by budget and dependency graph constraints.
        """
        auth_principal = principal or get_internal_compatibility_principal()
        start_time = time.time()
        tool_results_by_name: Dict[str, Any] = {}
        collected_evidence: List[CaseEvidenceRecord] = []
        collected_evidence_ids: List[str] = []
        tool_calls_count = 0

        case_id = plan.case_id
        investigation_id = plan.plan_id
        plan.status = "IN_PROGRESS"

        logger.info(f"Starting execution of investigation plan '{investigation_id}' for case '{case_id}'.")
        self.case_service.update_case_status(case_id, CaseStatusEnum.INVESTIGATING, actor="ORCHESTRATOR", principal=auth_principal)

        while not InvestigationGraph.is_plan_complete(plan):
            # Check budget limits
            elapsed = time.time() - start_time
            if (
                len([s for s in plan.steps if s.status != StepResultStatusEnum.PENDING]) >= plan.budget.max_steps
                or tool_calls_count >= plan.budget.max_tool_calls
                or elapsed >= plan.budget.max_runtime_seconds
            ):
                plan.status = "LIMIT_REACHED"
                plan.limit_reached_reason = "INVESTIGATION_LIMIT_REACHED"
                logger.warning(f"Investigation '{investigation_id}' hit budget limits ({plan.limit_reached_reason}).")
                InvestigationTraceTracker.record_event(
                    investigation_id=investigation_id,
                    case_id=case_id,
                    step_id="BUDGET_GUARD",
                    tool_name="SYSTEM_BUDGET",
                    status="LIMIT_REACHED",
                    duration_seconds=elapsed,
                    output_summary="INVESTIGATION_LIMIT_REACHED",
                )
                break

            executable_steps = InvestigationGraph.get_executable_steps(plan)
            if not executable_steps:
                # No more steps ready to run (or remaining steps are blocked)
                break

            for step in executable_steps:
                step.status = StepResultStatusEnum.RUNNING
                step_start = time.time()
                tool_calls_count += 1

                logger.info(f"Executing step '{step.step_id}' ({step.tool_name})...")
                params = step.input_params or {}
                res = self.executor.execute_tool(
                    tool_name=step.tool_name,
                    principal=auth_principal,
                    **params,
                )

                step_duration = round(time.time() - step_start, 3)
                step.execution_time_seconds = step_duration

                if res.success:
                    step.status = StepResultStatusEnum.SUCCESS
                    raw_res = res.structured_data if hasattr(res, "structured_data") else getattr(res, "result", {})
                    step.result_reference = raw_res or {}
                    res_dict = raw_res if isinstance(raw_res, dict) else {"data": raw_res}
                    tool_results_by_name[step.tool_name] = res_dict

                    # Create first-class evidence record
                    ev = EvidenceManager.create_evidence(
                        case_id=case_id,
                        source_type=res_dict.get("source_type", step.tool_name.upper()),
                        source_id=f"{step.tool_name}-{step.step_id}",
                        description=f"Output from step '{step.step_id}' ({step.purpose})",
                        data=res_dict,
                        reliability=1.0,
                    )
                    collected_evidence.append(ev)
                    collected_evidence_ids.append(ev.evidence_id)
                    self.case_service.repository.save_evidence_record(ev)

                    InvestigationTraceTracker.record_event(
                        investigation_id=investigation_id,
                        case_id=case_id,
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status="SUCCESS",
                        duration_seconds=step_duration,
                        output_summary=str(res_dict)[:150],
                    )

                    # Adaptive Investigation Trigger
                    if step.tool_name == "find_duplicates" and res_dict.get("duplicate_status") == "EXACT_DUPLICATE":
                        # Adaptively append deeper pattern check if not present
                        if not any(s.tool_name == "get_record_lineage" for s in plan.steps):
                            logger.info("Adaptive expansion: adding lineage check step due to EXACT_DUPLICATE.")
                            new_step = InvestigationStep(
                                tool_name="get_record_lineage",
                                purpose="Adaptive lineage check for exact duplicate.",
                                input_params={"canonical_record_id": plan.subject_invoice_id or "INV-UNKNOWN"},
                                expected_output="Record provenance lineage.",
                            )
                            plan.steps.append(new_step)

                else:
                    step.status = StepResultStatusEnum.FAILED
                    err_msg = ", ".join(res.errors) if res.errors else "Tool execution failed."
                    step.error_message = err_msg
                    InvestigationTraceTracker.record_event(
                        investigation_id=investigation_id,
                        case_id=case_id,
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        status="FAILED",
                        duration_seconds=step_duration,
                        output_summary=err_msg,
                        error=err_msg,
                    )

        if plan.status != "LIMIT_REACHED":
            plan.status = "COMPLETED"

        # Update case state
        self.case_service.update_case_status(case_id, CaseStatusEnum.EVIDENCE_COLLECTED, actor="ORCHESTRATOR", principal=auth_principal)

        # Consolidate Findings & Detect Conflicts
        findings, has_contradictions = self.consolidation_service.consolidate_findings(
            case_id=case_id,
            tool_results_by_name=tool_results_by_name,
            evidence_ids=collected_evidence_ids,
        )
        for f in findings:
            self.case_service.repository.save_finding(f)

        self.case_service.update_case_status(case_id, CaseStatusEnum.FINDINGS_READY, actor="ORCHESTRATOR", principal=auth_principal)

        # Calculate Confidence
        failed_count = len([s for s in plan.steps if s.status in {StepResultStatusEnum.FAILED, StepResultStatusEnum.TIMEOUT}])
        conf_score, conf_level, conf_reasons = self.confidence_engine.calculate_confidence(
            validation_result=tool_results_by_name.get("get_compliance_result") or tool_results_by_name.get("validate_invoice"),
            risk_assessment=tool_results_by_name.get("get_risk_assessment"),
            evidence_count=len(collected_evidence),
            has_contradictions=has_contradictions,
            failed_step_count=failed_count,
        )

        # Generate Explanations for Findings
        explanations: List[StructuredExplanation] = []
        for f in findings:
            exp = self.explainer.explain_finding(
                finding=f,
                evidence_records=collected_evidence,
                confidence_level=conf_level.value,
                contradictions="Conflicting engine signals detected." if has_contradictions else None,
            )
            explanations.append(exp)

        # Update Case Artifacts
        fin_res = tool_results_by_name.get("get_financial_exposure") or {}
        rca_res = tool_results_by_name.get("investigate_root_cause") or {}
        blast_res = tool_results_by_name.get("get_blast_radius") or {}

        exp_amt = float(fin_res.get("financial_exposure", fin_res.get("potential_exposure", 0.0)))
        rc_val = str(rca_res.get("root_cause", "UNDETERMINED"))

        # Transition Case to RESOLUTION_PROPOSED and then PENDING_REVIEW
        case = self.case_service.get_case(case_id, principal=auth_principal)
        if case:
            case.financial_exposure = exp_amt
            case.root_cause = rc_val
            case.blast_radius = blast_res
            case.recommendation = f"Proposed Resolution: {findings[0].title if findings else 'Review Case'}. Confidence: {conf_level.value} ({conf_score * 100:.1f}%)."
            self.case_service.repository.save_case(case)

        self.case_service.update_case_status(case_id, CaseStatusEnum.RESOLUTION_PROPOSED, actor="ORCHESTRATOR", principal=auth_principal)
        self.case_service.update_case_status(case_id, CaseStatusEnum.PENDING_REVIEW, actor="ORCHESTRATOR", principal=auth_principal)

        trace = InvestigationTraceTracker.get_trace(investigation_id)

        return {
            "investigation_id": investigation_id,
            "case_id": case_id,
            "status": plan.status,
            "limit_reached_reason": plan.limit_reached_reason,
            "total_steps": len(plan.steps),
            "completed_steps": len([s for s in plan.steps if s.status == StepResultStatusEnum.SUCCESS]),
            "failed_steps": failed_count,
            "confidence_score": conf_score,
            "confidence_level": conf_level.value,
            "confidence_reasons": conf_reasons,
            "has_contradictions": has_contradictions,
            "findings": [f.model_dump() for f in findings],
            "explanations": [e.model_dump() for e in explanations],
            "evidence_count": len(collected_evidence),
            "evidence": [ev.model_dump() for ev in collected_evidence],
            "trace_event_count": len(trace),
            "trace": [t.model_dump() for t in trace],
        }
