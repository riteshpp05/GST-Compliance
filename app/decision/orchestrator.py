"""
UC15 GST Compliance Agent — Master Exhaustive Decision Matrix Orchestrator
Orchestrates all decision matrix engines and generates a unified, auditable decision package.
"""
from __future__ import annotations

from typing import List, Dict, Any
from pydantic import BaseModel, Field

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus
from app.decision.matrix.registration import GSTINRegistrationMatrixEngine
from app.decision.matrix.tax_determination import TaxDeterminationMatrixEngine
from app.decision.matrix.pos_tree import PlaceOfSupplyDecisionTreeEngine
from app.decision.matrix.itc_tree import ITCEligibilityDecisionTreeEngine
from app.decision.matrix.rcm_engine import RCMDecisionEngine
from app.decision.matrix.eway_matrix import EWayBillMatrixEngine
from app.decision.matrix.sap_engine import SAPTaxEngine
from app.domain.models.invoice import Invoice


class TransactionAuditDecisionPackage(BaseModel):
    """
    Complete audit decision package produced for a transaction.
    """
    invoice_id: str
    supplier_gstin: str
    recipient_gstin: str
    transaction_date: str

    overall_status: DecisionStatus
    failing_rules_count: int
    total_financial_exposure: float
    decision_paths: List[ComplianceDecisionPath] = Field(default_factory=list)
    audit_summary: Dict[str, Any] = Field(default_factory=dict)


class ExhaustiveDecisionOrchestrator:
    """
    Master orchestrator executing all statutory, SAP, and reconciliation decision engines.
    """

    @classmethod
    def evaluate_transaction(cls, invoice: Invoice) -> TransactionAuditDecisionPackage:
        ctx = ComplianceContext.from_invoice(invoice)
        paths: List[ComplianceDecisionPath] = []

        # Execute decision matrix engines
        paths.extend(GSTINRegistrationMatrixEngine.evaluate(ctx))
        paths.extend(TaxDeterminationMatrixEngine.evaluate(ctx))
        paths.extend(PlaceOfSupplyDecisionTreeEngine.evaluate(ctx))
        paths.extend(ITCEligibilityDecisionTreeEngine.evaluate(ctx))
        paths.extend(RCMDecisionEngine.evaluate(ctx))
        paths.extend(EWayBillMatrixEngine.evaluate(ctx))
        paths.extend(SAPTaxEngine.evaluate(ctx))

        failing = [p for p in paths if p.status == DecisionStatus.FAIL]
        total_exposure = sum(p.financial_exposure for p in failing)

        if len(failing) == 0:
            overall = DecisionStatus.PASS
        elif any(p.severity.value == "CRITICAL" for p in failing):
            overall = DecisionStatus.FAIL
        else:
            overall = DecisionStatus.REVIEW_REQUIRED if len(failing) == 1 else DecisionStatus.FAIL

        return TransactionAuditDecisionPackage(
            invoice_id=invoice.invoice_id,
            supplier_gstin=ctx.supplier_gstin,
            recipient_gstin=ctx.recipient_gstin,
            transaction_date=str(ctx.transaction_date),
            overall_status=overall,
            failing_rules_count=len(failing),
            total_financial_exposure=round(total_exposure, 2),
            decision_paths=paths,
            audit_summary={
                "total_controls_evaluated": len(paths),
                "passing_controls": len([p for p in paths if p.status == DecisionStatus.PASS]),
                "failing_controls": len(failing),
                "review_required_controls": len([p for p in paths if p.status == DecisionStatus.REVIEW_REQUIRED]),
                "not_applicable_controls": len([p for p in paths if p.status == DecisionStatus.NOT_APPLICABLE]),
                "overall_status": overall.value,
                "total_exposure": round(total_exposure, 2),
            },
        )
