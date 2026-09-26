"""
tests.unit.test_s15_workflow_models
====================================
Unit Test Suite for Sprint 15 Domain Models, Request DTOs, and State Machine.
Verifies:
  1. CaseStatusEnum, CaseDecisionEnum, CaseEventTypeEnum integrity
  2. Pydantic Domain Models (InvestigationPlanDomain, CaseEvidenceRecord, CaseFinding, CaseRiskAssessment, CaseRecommendation, CaseTriageResult)
  3. Request DTO validation and default values
  4. CaseStateMachine transition rules and AI security boundaries
"""

from datetime import datetime, timezone
import unittest

from app.case.models import (
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
from app.case.state_machine import CaseStateMachine, CaseStateTransitionError


class TestS15WorkflowModels(unittest.TestCase):
    """Unit tests for S15 domain models and Pydantic schemas."""

    def test_01_enum_definitions(self):
        """Verify enum string values and completeness."""
        self.assertEqual(CaseStatusEnum.CREATED.value, "CREATED")
        self.assertEqual(CaseStatusEnum.TRIAGED.value, "TRIAGED")
        self.assertEqual(CaseStatusEnum.INVESTIGATING.value, "INVESTIGATING")
        self.assertEqual(CaseStatusEnum.EVIDENCE_COLLECTED.value, "EVIDENCE_COLLECTED")
        self.assertEqual(CaseStatusEnum.FINDINGS_READY.value, "FINDINGS_READY")
        self.assertEqual(CaseStatusEnum.RESOLUTION_PROPOSED.value, "RESOLUTION_PROPOSED")
        self.assertEqual(CaseStatusEnum.PENDING_REVIEW.value, "PENDING_REVIEW")
        self.assertEqual(CaseStatusEnum.RESOLVED.value, "RESOLVED")
        self.assertEqual(CaseStatusEnum.CLOSED.value, "CLOSED")

        # Preserved backward-compatible states
        self.assertEqual(CaseStatusEnum.OPEN.value, "OPEN")
        self.assertEqual(CaseStatusEnum.REVIEW_REQUIRED.value, "REVIEW_REQUIRED")
        self.assertEqual(CaseStatusEnum.APPROVED.value, "APPROVED")
        self.assertEqual(CaseStatusEnum.REJECTED.value, "REJECTED")

        # Decisions
        self.assertEqual(CaseDecisionEnum.APPROVE.value, "APPROVE")
        self.assertEqual(CaseDecisionEnum.RETURN_FOR_INVESTIGATION.value, "RETURN_FOR_INVESTIGATION")

    def test_02_investigation_plan_domain_model(self):
        """Verify InvestigationPlanDomain creation and defaults."""
        plan = InvestigationPlanDomain(
            case_id="CASE-12345",
            objective="Verify ITC claim compliance",
            questions=["Is counterparty active?", "Does GSTR-2B match?"],
            required_data=["GSTR-2B", "Purchase Register"],
            expected_evidence=["EVIDENCE_2B_MATCH"],
            analysis_tasks=["Compare line item values"],
            risk_areas=["ITC_MISMATCH"],
        )
        self.assertTrue(plan.plan_id.startswith("PLAN-"))
        self.assertEqual(plan.case_id, "CASE-12345")
        self.assertEqual(plan.status, "PLANNED")
        self.assertEqual(len(plan.questions), 2)

    def test_03_case_evidence_record_model(self):
        """Verify CaseEvidenceRecord schema."""
        record = CaseEvidenceRecord(
            case_id="CASE-12345",
            evidence_type="GST_RETURNS",
            source="GSTR-2B_INSPECTOR",
            description="Verified GSTR-2B filing status for 2026-07",
            data={"match_status": "MATCHED", "itc_available": 15840.0},
            reliability=0.95,
            collected_by="INVESTIGATION_AGENT",
        )
        self.assertTrue(record.evidence_id.startswith("EVD-"))
        self.assertEqual(record.reliability, 0.95)
        self.assertEqual(record.data["match_status"], "MATCHED")

    def test_04_case_finding_model(self):
        """Verify CaseFinding schema."""
        finding = CaseFinding(
            case_id="CASE-12345",
            title="Place of Supply Mismatch",
            description="CGST+SGST charged instead of IGST for inter-state supply.",
            category="POS_MISMATCH",
            severity="HIGH",
            evidence_ids=["EVD-001", "EVD-002"],
            confidence=1.0,
        )
        self.assertTrue(finding.finding_id.startswith("FND-"))
        self.assertEqual(finding.severity, "HIGH")
        self.assertEqual(len(finding.evidence_ids), 2)

    def test_05_case_risk_assessment_model(self):
        """Verify CaseRiskAssessment schema."""
        assessment = CaseRiskAssessment(
            case_id="CASE-12345",
            risk_score=85.5,
            risk_level="HIGH",
            contributing_factors=["Place of supply mismatch", "Missing e-Way bill"],
            explanation="Multiple high severity statutory gate failures.",
        )
        self.assertTrue(assessment.assessment_id.startswith("RSK-"))
        self.assertEqual(assessment.risk_score, 85.5)
        self.assertEqual(assessment.risk_level, "HIGH")

    def test_06_case_recommendation_model(self):
        """Verify CaseRecommendation schema."""
        rec = CaseRecommendation(
            case_id="CASE-12345",
            recommended_action="RECONCILIATION_REQUIRED",
            rationale="Issue credit note to adjust incorrect tax component.",
            supporting_finding_ids=["FND-001"],
            confidence=0.9,
            generated_by="AI_INVESTIGATION_AGENT",
        )
        self.assertTrue(rec.recommendation_id.startswith("REC-"))
        self.assertEqual(rec.recommended_action, "RECONCILIATION_REQUIRED")

    def test_07_request_dtos(self):
        """Verify Request DTO parsing."""
        create_req = CaseCreateRequest(
            invoice_id="INV-8000001",
            counterparty_gstin="29XCDBM5846M9ZE",
            title="Investigate INV-8000001",
            source="AUTOMATED_SCAN",
        )
        self.assertEqual(create_req.invoice_id, "INV-8000001")
        self.assertEqual(create_req.case_type, "GST_COMPLIANCE_INVESTIGATION")

        triage_req = CaseTriageRequest(
            priority="P1",
            risk_level="CRITICAL",
            category="ITC_ANOMALY",
            investigation_scope="FULL_AUDIT",
            actor="LEAD_TAX_OFFICER",
        )
        self.assertEqual(triage_req.priority, "P1")
        self.assertEqual(triage_req.risk_level, "CRITICAL")


class TestS15StateMachine(unittest.TestCase):
    """Unit tests for CaseStateMachine transitions and AI security boundaries."""

    def test_valid_enterprise_lifecycle(self):
        """Verify standard forward transitions across full enterprise case lifecycle."""
        # CREATED -> TRIAGED
        CaseStateMachine.validate_transition(CaseStatusEnum.CREATED, CaseStatusEnum.TRIAGED)

        # TRIAGED -> INVESTIGATING
        CaseStateMachine.validate_transition(CaseStatusEnum.TRIAGED, CaseStatusEnum.INVESTIGATING)

        # INVESTIGATING -> EVIDENCE_COLLECTED
        CaseStateMachine.validate_transition(CaseStatusEnum.INVESTIGATING, CaseStatusEnum.EVIDENCE_COLLECTED)

        # EVIDENCE_COLLECTED -> FINDINGS_READY
        CaseStateMachine.validate_transition(CaseStatusEnum.EVIDENCE_COLLECTED, CaseStatusEnum.FINDINGS_READY)

        # FINDINGS_READY -> RESOLUTION_PROPOSED
        CaseStateMachine.validate_transition(CaseStatusEnum.FINDINGS_READY, CaseStatusEnum.RESOLUTION_PROPOSED)

        # RESOLUTION_PROPOSED -> PENDING_REVIEW
        CaseStateMachine.validate_transition(CaseStatusEnum.RESOLUTION_PROPOSED, CaseStatusEnum.PENDING_REVIEW)

        # PENDING_REVIEW -> APPROVED (Human review with explicit decision)
        CaseStateMachine.validate_transition(
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.APPROVED,
            decision=CaseDecisionEnum.APPROVE,
            reviewer="Tax Senior Partner",
        )

        # APPROVED -> RESOLVED
        CaseStateMachine.validate_transition(CaseStatusEnum.APPROVED, CaseStatusEnum.RESOLVED)

        # RESOLVED -> CLOSED
        CaseStateMachine.validate_transition(CaseStatusEnum.RESOLVED, CaseStatusEnum.CLOSED)

    def test_ai_security_boundary_enforcement(self):
        """Verify AI is forbidden from transitioning case into approval/terminal states."""
        forbidden_targets = [
            CaseStatusEnum.APPROVED,
            CaseStatusEnum.REJECTED,
            CaseStatusEnum.READY_FOR_RESOLUTION,
            CaseStatusEnum.RESOLVED,
            CaseStatusEnum.CLOSED,
        ]
        for target in forbidden_targets:
            with self.assertRaises(CaseStateTransitionError) as ctx:
                CaseStateMachine.validate_transition(
                    CaseStatusEnum.PENDING_REVIEW,
                    target,
                    decision=CaseDecisionEnum.APPROVE,
                    reviewer="AI_AGENT",
                    actor_is_ai=True,
                )
            self.assertIn("Security Boundary Violation", str(ctx.exception))

    def test_return_for_investigation_loop(self):
        """Verify human reviewer can return case for investigation."""
        CaseStateMachine.validate_transition(
            CaseStatusEnum.PENDING_REVIEW,
            CaseStatusEnum.RETURNED_FOR_INVESTIGATION,
            decision=CaseDecisionEnum.RETURN_FOR_INVESTIGATION,
            reviewer="Chief Compliance Officer",
        )
        # RETURNED_FOR_INVESTIGATION -> INVESTIGATING
        CaseStateMachine.validate_transition(
            CaseStatusEnum.RETURNED_FOR_INVESTIGATION,
            CaseStatusEnum.INVESTIGATING,
        )


if __name__ == "__main__":
    unittest.main()
