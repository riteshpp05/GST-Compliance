"""
app.investigation.graph
=======================
Dependency-Aware Investigation Graph & Execution Order Resolver for UC15 (Sprint 18).
Builds DAG topologies for investigation steps and resolves executable step sets based on dependencies.
"""

from __future__ import annotations

from typing import List, Optional
from app.investigation.plan import (
    InvestigationBudget,
    InvestigationPlan,
    InvestigationStep,
    StepDependency,
    StepResultStatusEnum,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class InvestigationGraph:
    """
    Dependency resolver and execution topology builder for Investigation Plans.
    """

    @staticmethod
    def get_executable_steps(plan: InvestigationPlan) -> List[InvestigationStep]:
        """
        Return steps that are ready for execution:
        Status is PENDING and all prerequisite dependencies are satisfied.
        """
        completed_step_ids = {
            s.step_id
            for s in plan.steps
            if s.status in {StepResultStatusEnum.SUCCESS, StepResultStatusEnum.SKIPPED}
        }
        failed_step_ids = {
            s.step_id
            for s in plan.steps
            if s.status in {StepResultStatusEnum.FAILED, StepResultStatusEnum.BLOCKED, StepResultStatusEnum.TIMEOUT}
        }

        executable: List[InvestigationStep] = []
        for step in plan.steps:
            if step.status != StepResultStatusEnum.PENDING:
                continue

            # Check dependencies
            all_satisfied = True
            is_blocked = False

            for dep in step.dependencies:
                prereq_id = dep.prerequisite_step_id
                if prereq_id in failed_step_ids:
                    is_blocked = True
                    all_satisfied = False
                    break
                if prereq_id not in completed_step_ids:
                    all_satisfied = False
                    break

            if is_blocked:
                step.status = StepResultStatusEnum.BLOCKED
                logger.warning(f"Step '{step.step_id}' ({step.tool_name}) marked BLOCKED due to failed prerequisite.")
            elif all_satisfied:
                executable.append(step)

        return executable

    @staticmethod
    def is_plan_complete(plan: InvestigationPlan) -> bool:
        """Check if all steps in the plan have reached terminal status."""
        terminal_statuses = {
            StepResultStatusEnum.SUCCESS,
            StepResultStatusEnum.FAILED,
            StepResultStatusEnum.SKIPPED,
            StepResultStatusEnum.BLOCKED,
            StepResultStatusEnum.TIMEOUT,
        }
        return all(step.status in terminal_statuses for step in plan.steps)

    @staticmethod
    def build_default_plan(
        case_id: str,
        objective: str,
        invoice_id: Optional[str] = None,
        tenant_id: str = "tenant_default",
        intent_category: str = "GENERAL",
    ) -> InvestigationPlan:
        """
        Construct a default dependency-aware investigation plan based on objective and intent.
        """
        target_inv = invoice_id or "INV-UNKNOWN"
        steps: List[InvestigationStep] = []
        common_params = {"invoice_no": target_inv, "invoice_id": target_inv}

        # Step 1: GST Compliance Validation
        s1 = InvestigationStep(
            tool_name="get_compliance_result",
            purpose="Validate GST compliance gates and tax calculations.",
            input_params=common_params,
            expected_output="Six-gate compliance evaluation.",
        )
        steps.append(s1)

        # Step 2: Risk Assessment (Depends on Step 1)
        s2 = InvestigationStep(
            tool_name="get_risk_assessment",
            purpose="Assess compliance risk score and priority.",
            input_params=common_params,
            expected_output="Risk score and contributing drivers.",
            dependencies=[StepDependency(prerequisite_step_id=s1.step_id)],
        )
        steps.append(s2)

        # Step 3: Duplicate Check (Depends on Step 1)
        s3 = InvestigationStep(
            tool_name="find_duplicates",
            purpose="Check exact and potential duplicate signals.",
            input_params=common_params,
            expected_output="Duplicate matching results.",
            dependencies=[StepDependency(prerequisite_step_id=s1.step_id)],
        )
        steps.append(s3)

        # Step 4: Financial Exposure Calculation (Depends on Step 1)
        s4 = InvestigationStep(
            tool_name="get_financial_exposure",
            purpose="Quantify financial exposure and tax differential.",
            input_params=common_params,
            expected_output="Financial exposure breakdown.",
            dependencies=[StepDependency(prerequisite_step_id=s1.step_id)],
        )
        steps.append(s4)

        # Step 5: Historical Behavior Analysis (Depends on Step 1)
        s5 = InvestigationStep(
            tool_name="get_historical_patterns",
            purpose="Analyze counterparty historical filing patterns.",
            input_params=common_params,
            expected_output="Historical trend analysis.",
            dependencies=[StepDependency(prerequisite_step_id=s1.step_id)],
        )
        steps.append(s5)

        # Step 6: Root Cause Investigation (Depends on Step 1, Step 2)
        s6 = InvestigationStep(
            tool_name="investigate_root_cause",
            purpose="Identify primary root cause of compliance defect.",
            input_params=common_params,
            expected_output="Root cause classification.",
            dependencies=[
                StepDependency(prerequisite_step_id=s1.step_id),
                StepDependency(prerequisite_step_id=s2.step_id),
            ],
        )
        steps.append(s6)

        # Step 7: Blast Radius Analysis (Depends on Step 6)
        s7 = InvestigationStep(
            tool_name="get_blast_radius",
            purpose="Assess cross-entity and period blast radius.",
            input_params=common_params,
            expected_output="Multidimensional blast radius scope.",
            dependencies=[StepDependency(prerequisite_step_id=s6.step_id)],
        )
        steps.append(s7)

        # Step 8: Regulatory Knowledge Retrieval (Depends on Step 6)
        s8 = InvestigationStep(
            tool_name="retrieve_gst_knowledge",
            purpose="Retrieve relevant statutory GST circulars and rules.",
            input_params={"query": f"GST compliance rules for invoice {target_inv}"},
            expected_output="Statutory citations.",
            dependencies=[StepDependency(prerequisite_step_id=s6.step_id)],
        )
        steps.append(s8)

        return InvestigationPlan(
            case_id=case_id,
            objective=objective,
            subject_invoice_id=target_inv,
            tenant_id=tenant_id,
            steps=steps,
            budget=InvestigationBudget(),
        )
