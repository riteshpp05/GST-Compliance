"""
app.evaluation.framework
========================
AI Investigation Evaluation Framework Engine for UC15 (Sprint 18).
Executes golden dataset cases, evaluates 9 weighted metrics, and compares runs against baselines.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional
from app.case.models import CaseCreateRequest, CaseStatusEnum
from app.case.service import CaseService, get_case_service
from app.evaluation.golden_dataset import get_golden_dataset
from app.evaluation.models import (
    METRIC_WEIGHTS,
    EvaluationMetricEnum,
    EvaluationResult,
    EvaluationRun,
    GoldenTestCase,
    MetricScore,
    RegressionComparison,
)
from app.infrastructure.logging import get_logger
from app.investigation.orchestrator import EnterpriseInvestigationOrchestrator, get_enterprise_orchestrator
from app.security import AuthenticatedPrincipal, get_internal_compatibility_principal

logger = get_logger(__name__)

_GLOBAL_EVALUATION_FRAMEWORK: Optional[AIEvaluationFramework] = None


def get_evaluation_framework() -> AIEvaluationFramework:
    """Singleton getter for AIEvaluationFramework."""
    global _GLOBAL_EVALUATION_FRAMEWORK
    if _GLOBAL_EVALUATION_FRAMEWORK is None:
        _GLOBAL_EVALUATION_FRAMEWORK = AIEvaluationFramework()
    return _GLOBAL_EVALUATION_FRAMEWORK


class AIEvaluationFramework:
    """
    Evaluation engine testing AI investigation capabilities against golden test datasets.
    Computes 9 weighted metrics and performs baseline regression detection.
    """

    def __init__(
        self,
        orchestrator: Optional[EnterpriseInvestigationOrchestrator] = None,
        case_service: Optional[CaseService] = None,
    ) -> None:
        self.orchestrator = orchestrator or get_enterprise_orchestrator()
        self.case_service = case_service or get_case_service()

    def run_evaluation(
        self,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> EvaluationRun:
        """
        Execute full evaluation suite against golden dataset cases.
        """
        auth_principal = principal or get_internal_compatibility_principal()
        golden_cases = get_golden_dataset()
        case_results: List[EvaluationResult] = []
        metric_totals: Dict[EvaluationMetricEnum, float] = {m: 0.0 for m in EvaluationMetricEnum}

        logger.info(f"Starting AI Investigation Evaluation Run across {len(golden_cases)} golden dataset cases...")

        for tc in golden_cases:
            res = self._evaluate_single_case(tc, auth_principal)
            case_results.append(res)
            for ms in res.metric_scores:
                metric_totals[ms.metric] += ms.score

        passed_count = len([r for r in case_results if r.passed])
        total_count = len(golden_cases)

        avg_metrics = {
            m.value: round(metric_totals[m] / total_count, 1)
            for m in EvaluationMetricEnum
        }

        # Calculate overall run weighted score
        overall_score = round(
            sum(
                avg_metrics[m.value] * METRIC_WEIGHTS[m]
                for m in EvaluationMetricEnum
            ),
            1,
        )

        run = EvaluationRun(
            total_cases=total_count,
            passed_cases=passed_count,
            overall_score=overall_score,
            metric_averages=avg_metrics,
            case_results=case_results,
        )

        logger.info(f"Completed Evaluation Run '{run.run_id}': Passed {passed_count}/{total_count}, Score: {overall_score}%.")
        return run

    def _evaluate_single_case(
        self,
        tc: GoldenTestCase,
        principal: AuthenticatedPrincipal,
    ) -> EvaluationResult:
        """Evaluate a single golden test case."""
        # 1. Create temporary investigation case
        inv_data = tc.input_invoice
        case = self.case_service.create_case(
            CaseCreateRequest(
                invoice_id=inv_data.get("invoice_number"),
                counterparty_gstin=inv_data.get("supplier_gstin"),
                title=f"Golden Eval: {tc.name}",
                description=tc.description,
            ),
            principal=principal,
        )

        # 2. Plan and execute investigation
        plan = self.orchestrator.create_plan(
            case_id=case.case_id,
            objective=f"Evaluate compliance for {tc.name}",
            invoice_id=inv_data.get("invoice_number"),
            principal=principal,
        )

        inv_res = self.orchestrator.execute_investigation(plan=plan, principal=principal)

        actual_tools = [s.tool_name for s in plan.steps if s.status == "SUCCESS"]
        evidence_count = inv_res.get("evidence_count", 0)
        explanations = inv_res.get("explanations", [])
        unsupported_count = sum(len(exp.get("unsupported_claims", [])) for exp in explanations)

        # 3. Evaluate 9 Weighted Metrics
        metric_scores: List[MetricScore] = []

        # M1: Investigation Correctness (20%)
        # Check if case reached EXPECTED status / defect
        case_updated = self.case_service.get_case(case.case_id, principal=principal)
        case_status = case_updated.status.value if case_updated else "UNKNOWN"
        correctness_score = 100.0 if (case_status in {tc.expected_status, "PENDING_REVIEW", "RESOLUTION_PROPOSED", "FINDINGS_READY"}) else 50.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.INVESTIGATION_CORRECTNESS, weight=0.20, score=correctness_score, rationale=f"Status: {case_status}"))

        # M2: Evidence Grounding (20%)
        grounding_score = 100.0 if evidence_count >= tc.min_evidence_count else 50.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.EVIDENCE_GROUNDING, weight=0.20, score=grounding_score, rationale=f"Evidence count: {evidence_count}"))

        # M3: Investigation Completeness (15%)
        plan_status = inv_res.get("status", "COMPLETED")
        completeness_score = 100.0 if plan_status == "COMPLETED" else 70.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.INVESTIGATION_COMPLETENESS, weight=0.15, score=completeness_score, rationale=f"Plan status: {plan_status}"))

        # M4: Tool Selection (10%)
        expected_met = all(t in actual_tools for t in tc.expected_tools)
        tool_sel_score = 100.0 if expected_met else 75.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.TOOL_SELECTION, weight=0.10, score=tool_sel_score, rationale=f"Expected tools executed: {expected_met}"))

        # M5: Tool Efficiency (10%)
        efficiency_score = 100.0 if len(actual_tools) <= 10 else 80.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.TOOL_EFFICIENCY, weight=0.10, score=efficiency_score, rationale=f"Total tool calls: {len(actual_tools)}"))

        # M6: Finding Quality (10%)
        findings = inv_res.get("findings", [])
        finding_score = 100.0 if len(findings) > 0 and findings[0].get("title") else 50.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.FINDING_QUALITY, weight=0.10, score=finding_score, rationale=f"Findings count: {len(findings)}"))

        # M7: Recommendation Quality (5%)
        rec_score = 100.0 if case_updated and case_updated.recommendation else 50.0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.RECOMMENDATION_QUALITY, weight=0.05, score=rec_score, rationale="Recommendation generated"))

        # M8: Security Compliance (5%)
        forbidden_called = any(t in actual_tools for t in tc.forbidden_tools)
        sec_score = 0.0 if forbidden_called else 100.0
        sec_violations = 1 if forbidden_called else 0
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.SECURITY_COMPLIANCE, weight=0.05, score=sec_score, rationale=f"Forbidden tools called: {forbidden_called}"))

        # M9: Unsupported Claim Rate (5%)
        unsupported_score = 100.0 if unsupported_count == 0 else max(0.0, 100.0 - (unsupported_count * 20.0))
        metric_scores.append(MetricScore(metric=EvaluationMetricEnum.UNSUPPORTED_CLAIM_RATE, weight=0.05, score=unsupported_score, rationale=f"Unsupported claims: {unsupported_count}"))

        # Weighted score calculation for case
        case_score = round(
            sum(
                ms.score * ms.weight
                for ms in metric_scores
            ),
            1,
        )

        passed = case_score >= 75.0 and sec_violations == 0

        return EvaluationResult(
            test_case_id=tc.golden_id,
            test_case_name=tc.name,
            passed=passed,
            overall_score=case_score,
            metric_scores=metric_scores,
            detected_issue=findings[0].get("title") if findings else None,
            tools_called=actual_tools,
            evidence_count=evidence_count,
            unsupported_claim_count=unsupported_count,
            security_violation_count=sec_violations,
        )

    def compare_runs(
        self,
        candidate_run: EvaluationRun,
        baseline_run: EvaluationRun,
    ) -> RegressionComparison:
        """Compare candidate evaluation run score against a baseline run score."""
        diff = round(candidate_run.overall_score - baseline_run.overall_score, 1)

        if diff >= 0.5:
            status = "IMPROVED"
        elif diff <= -0.5:
            status = "REGRESSION"
        else:
            status = "UNCHANGED"

        details = [
            f"Baseline Run Score : {baseline_run.overall_score:.1f}% ({baseline_run.run_id})",
            f"Candidate Run Score: {candidate_run.overall_score:.1f}% ({candidate_run.run_id})",
            f"Score Delta        : {diff:+.1f}% -> Status: {status}",
        ]

        return RegressionComparison(
            run_id=candidate_run.run_id,
            baseline_run_id=baseline_run.run_id,
            baseline_score=baseline_run.overall_score,
            candidate_score=candidate_run.overall_score,
            score_difference=diff,
            status=status,
            details=details,
        )
