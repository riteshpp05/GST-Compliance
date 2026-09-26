"""
tests.integration.test_s15_case_workflow
===========================================
Integration Test Suite for Sprint 15 Case Workflow Orchestration.
Verifies complete end-to-end CaseService business logic:
  1. Case creation from session or manual request
  2. Case triage and priority/risk level assignment
  3. Investigation plan creation and retrieval
  4. Investigation start (state transition)
  5. Evidence record collection & retrieval
  6. Case findings creation & retrieval
  7. Risk assessment creation & retrieval
  8. Resolution recommendation proposal & retrieval
  9. Human review handling (APPROVE, RETURN_FOR_INVESTIGATION)
 10. Case resolution & closure
 11. Timeline event logging & audit trail integrity
"""

import unittest
from app.case.models import (
    CaseCreateRequest,
    CaseDecisionEnum,
    CaseStatusEnum,
    CaseTriageRequest,
    EvidenceCreateRequest,
    FindingCreateRequest,
    InvestigationPlanCreateRequest,
    RecommendationCreateRequest,
    RiskAssessmentCreateRequest,
)
from app.case.repository import InMemoryCaseRepository
from app.case.service import CaseService


class TestS15CaseWorkflowIntegration(unittest.TestCase):
    """Integration test suite for CaseService workflow operations."""

    def setUp(self):
        self.repo = InMemoryCaseRepository()
        self.service = CaseService(repository=self.repo)

    def test_complete_enterprise_case_lifecycle(self):
        """Test complete 10-step enterprise case workflow from CREATED to CLOSED."""
        # Step 1: Create Case
        create_req = CaseCreateRequest(
            invoice_id="INV-8000001",
            counterparty_gstin="29XCDBM5846M9ZE",
            title="Investigate Tax Rate & POS Mismatch on INV-8000001",
            source="AUTOMATED_SCAN",
            created_by="TAX_ANALYST_BOB",
        )
        case = self.service.create_case(create_req)
        self.assertIsNotNone(case.case_id)
        self.assertEqual(case.status, CaseStatusEnum.CREATED)
        self.assertEqual(case.invoice_id, "INV-8000001")

        # Verify initial timeline event
        timeline = self.service.get_case_timeline(case.case_id)
        self.assertTrue(any(e.event_type.value == "CASE_CREATED" for e in timeline))

        # Step 2: Triage Case
        triage_req = CaseTriageRequest(
            priority="P1",
            risk_level="CRITICAL",
            category="TAX_POS_MISMATCH",
            investigation_scope="FULL_TAX_AUDIT",
            assigned_to="TAX_LEAD_ALICE",
            actor="TRIAGE_SYSTEM",
        )
        triage_res = self.service.triage_case(case.case_id, triage_req)
        triaged_case = self.service.get_case(case.case_id)
        self.assertEqual(triaged_case.status, CaseStatusEnum.TRIAGED)
        self.assertEqual(triage_res.priority, "P1")
        self.assertEqual(triage_res.risk_level, "CRITICAL")
        self.assertEqual(triage_res.assigned_to, "TAX_LEAD_ALICE")

        # Step 3: Create Investigation Plan
        plan_req = InvestigationPlanCreateRequest(
            objective="Confirm Place of Supply and verify IGST vs CGST/SGST liability.",
            questions=["Was invoice intra-state or inter-state?", "Is e-Way bill required?"],
            required_data=["GSTR-1", "GSTR-2B", "E-Way Bill Portal"],
            expected_evidence=["EVIDENCE_POS_CHECK", "EVIDENCE_EWB_STATUS"],
            analysis_tasks=["Check POS state against vendor GSTIN state"],
            risk_areas=["INCORRECT_TAX_PAYMENT"],
        )
        plan = self.service.create_investigation_plan(case.case_id, plan_req)
        self.assertIsNotNone(plan.plan_id)
        self.assertEqual(plan.case_id, case.case_id)

        retrieved_plan = self.service.get_investigation_plan(case.case_id)
        self.assertIsNotNone(retrieved_plan)
        self.assertEqual(retrieved_plan.objective, plan_req.objective)

        # Step 4: Start Investigation
        inv_case = self.service.start_investigation(case.case_id, actor="TAX_LEAD_ALICE")
        self.assertEqual(inv_case.status, CaseStatusEnum.INVESTIGATING)

        # Step 5: Add Evidence
        ev1 = self.service.add_evidence(
            case.case_id,
            EvidenceCreateRequest(
                evidence_type="GST_RETURNS",
                source="GSTR-2B",
                description="Invoice absent from GSTR-2B filing",
                data={"gstr2b_status": "MISSING", "itc_amount": 15840.0},
                reliability=1.0,
                collected_by="INVESTIGATION_AGENT",
            ),
        )
        self.assertIsNotNone(ev1.evidence_id)

        ev_records = self.service.get_evidence_records(case.case_id)
        self.assertEqual(len(ev_records), 1)

        # Step 6: Add Finding
        finding = self.service.add_finding(
            case.case_id,
            FindingCreateRequest(
                title="GSTR-2B Mismatch & Missing E-Way Bill",
                description="Supplier failed to report invoice in GSTR-1 and did not generate e-Way bill.",
                category="ITC_EWAY_MISMATCH",
                severity="HIGH",
                evidence_ids=[ev1.evidence_id],
                confidence=0.95,
                created_by="INVESTIGATION_AGENT",
            ),
        )
        self.assertIsNotNone(finding.finding_id)

        findings = self.service.get_findings(case.case_id)
        self.assertEqual(len(findings), 1)

        # Step 7: Assess Risk
        risk = self.service.assess_risk(
            case.case_id,
            RiskAssessmentCreateRequest(
                risk_score=92.0,
                risk_level="CRITICAL",
                contributing_factors=["Unmatched ITC", "Overcharged Tax", "Missing E-Way Bill"],
                explanation="High tax exposure with statutory compliance breach.",
            ),
        )
        self.assertEqual(risk.risk_score, 92.0)

        # Step 8: Propose Recommendation
        rec = self.service.propose_recommendation(
            case.case_id,
            RecommendationCreateRequest(
                recommended_action="RECONCILIATION_REQUIRED",
                rationale="Hold ITC claim until vendor files GSTR-1 amendment and issues credit note.",
                supporting_finding_ids=[finding.finding_id],
                confidence=0.9,
                generated_by="AI_INVESTIGATION_AGENT",
            ),
        )
        self.assertEqual(rec.recommended_action, "RECONCILIATION_REQUIRED")

        # Verify case status transitioned to RESOLUTION_PROPOSED or PENDING_REVIEW
        case_now = self.service.get_case(case.case_id)
        self.assertIn(case_now.status, [CaseStatusEnum.RESOLUTION_PROPOSED, CaseStatusEnum.PENDING_REVIEW])

        # Step 9: Submit Human Review Decision (APPROVE)
        reviewed_case = self.service.submit_human_review(
            case.case_id,
            reviewer="CHIEF_TAX_OFFICER",
            reviewer_role="Chief Tax Officer",
            decision=CaseDecisionEnum.APPROVE,
            comment="Approved recommendation to hold ITC and initiate vendor reconciliation.",
        )
        self.assertEqual(reviewed_case.status, CaseStatusEnum.READY_FOR_RESOLUTION)
        self.assertEqual(len(reviewed_case.decisions), 1)

        # Step 10: Resolve & Close Case
        resolved_case = self.service.resolve_case(
            case.case_id,
            actor="CHIEF_TAX_OFFICER",
            resolution_summary="Vendor reconciliation initiated. Invoice blocked from GSTR-3B.",
        )
        self.assertEqual(resolved_case.status, CaseStatusEnum.RESOLVED)

        closed_case = self.service.close_case(
            case.case_id,
            actor="CHIEF_TAX_OFFICER",
            closure_notes="Case closed post approval.",
        )
        self.assertEqual(closed_case.status, CaseStatusEnum.CLOSED)

        # Verify Audit Timeline
        full_timeline = self.service.get_case_timeline(case.case_id)
        self.assertGreater(len(full_timeline), 5)
        event_types = [e.event_type.value for e in full_timeline]
        self.assertIn("CASE_CREATED", event_types)
        self.assertIn("CASE_TRIAGED", event_types)
        self.assertIn("CASE_RESOLVED", event_types)
        self.assertIn("CASE_CLOSED", event_types)

    def test_return_for_investigation_flow(self):
        """Test returning a case for further investigation when human reviewer rejects draft recommendation."""
        create_req = CaseCreateRequest(invoice_id="INV-8000002", title="Investigate INV-8000002")
        case = self.service.create_case(create_req)
        self.service.triage_case(case.case_id, CaseTriageRequest(priority="P2", risk_level="MEDIUM"))
        self.service.start_investigation(case.case_id)
        self.service.add_evidence(case.case_id, EvidenceCreateRequest(evidence_type="INVOICE", source="ERP", description="Invoice payload"))
        self.service.propose_recommendation(case.case_id, RecommendationCreateRequest(recommended_action="CLOSE_CASE", rationale="Appears normal"))

        # Reviewer submits RETURN_FOR_INVESTIGATION
        returned_case = self.service.submit_human_review(
            case.case_id,
            reviewer="AUDIT_MANAGER",
            decision=CaseDecisionEnum.RETURN_FOR_INVESTIGATION,
            comment="Insufficient evidence regarding HSN tax rate difference. Please re-investigate.",
        )
        self.assertEqual(returned_case.status, CaseStatusEnum.RETURNED_FOR_INVESTIGATION)

        # Re-start investigation
        restarted_case = self.service.start_investigation(case.case_id, actor="TAX_ANALYST_BOB")
        self.assertEqual(restarted_case.status, CaseStatusEnum.INVESTIGATING)


if __name__ == "__main__":
    unittest.main()
