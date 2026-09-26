"""
UC15 GST Compliance Agent — Evidence Sufficiency Evaluator (Sprint 22)
Evaluates evidence completeness and itemizes missing evidence required for finance investigation.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.investigation.evidence.models import (
    EvidenceSufficiencyReport,
    EvidenceSufficiencyState,
    MissingEvidenceItem,
    MissingEvidenceUrgency,
)


class EvidenceSufficiencyEvaluator:
    """
    Evaluates presence, completeness, and sufficiency of evidence for an invoice case.
    Explicitly identifies missing evidence with urgency levels and recommended actions.
    """

    def evaluate(
        self,
        case_id: str,
        invoice: Optional[Invoice] = None,
        decision: Optional[ComplianceDecision] = None,
        reconciliation_result: Optional[Any] = None,
    ) -> EvidenceSufficiencyReport:
        inv_id = (
            getattr(invoice, "invoice_id", None)
            or getattr(decision, "invoice_no", None)
            or case_id
        )

        present: List[str] = []
        missing: List[MissingEvidenceItem] = []
        notes: List[str] = []

        total_weights = 0.0
        earned_weights = 0.0

        # 1. Invoice Baseline Record
        total_weights += 20.0
        if invoice is not None or (decision and decision.invoice_no):
            present.append("INVOICE_RECORD")
            earned_weights += 20.0
        else:
            missing.append(
                MissingEvidenceItem(
                    evidence_type="INVOICE_RECORD",
                    description="Raw or structured invoice payload is missing.",
                    urgency=MissingEvidenceUrgency.CRITICAL,
                    impact_on_investigation="Cannot verify line items, tax breakdown, or counterparty headers.",
                    recommended_action="Upload original invoice JSON or scanned document.",
                )
            )

        # 2. Statutory Rule Evaluation Results
        total_weights += 20.0
        if decision and getattr(decision, "gates", None):
            present.append("STATUTORY_RULE_EVALUATION")
            earned_weights += 20.0
        else:
            missing.append(
                MissingEvidenceItem(
                    evidence_type="STATUTORY_RULE_EVALUATION",
                    description="Compliance screening gate results not available.",
                    urgency=MissingEvidenceUrgency.HIGH,
                    impact_on_investigation="Cannot identify statutory rule failures or rule versions.",
                    recommended_action="Run compliance validation engine on the invoice.",
                )
            )

        # 3. GSTR-2B Filing Entry
        total_weights += 20.0
        gstr2b_found = False
        if invoice and getattr(invoice, "is_gstr2b_matched", False):
            gstr2b_found = True
        elif decision and getattr(decision, "evidence", None):
            ev = decision.evidence
            if isinstance(ev, dict) and ev.get("gstr2b_matched"):
                gstr2b_found = True

        if gstr2b_found:
            present.append("GSTR2B_FILING_RECORD")
            earned_weights += 20.0
        else:
            missing.append(
                MissingEvidenceItem(
                    evidence_type="GSTR2B_RECORD",
                    description="Invoice details not confirmed present in buyer's GSTR-2B auto-populated statement.",
                    urgency=MissingEvidenceUrgency.CRITICAL if (invoice and invoice.direction == "AP") else MissingEvidenceUrgency.MEDIUM,
                    impact_on_investigation="ITC claim cannot be reconciled against supplier GSTR-1 filing under Section 16(2)(aa).",
                    recommended_action="Fetch latest GSTR-2B JSON payload or request supplier GSTR-1 filing status.",
                )
            )

        # 4. Supplier Active GSTIN Master
        total_weights += 15.0
        gstin_verified = False
        if invoice and getattr(invoice, "supplier_gstin", None):
            gstin_verified = True
        elif decision and getattr(decision, "counterparty_gstin", None):
            gstin_verified = True

        if gstin_verified:
            present.append("SUPPLIER_GSTIN_REGISTRATION")
            earned_weights += 15.0
        else:
            missing.append(
                MissingEvidenceItem(
                    evidence_type="SUPPLIER_ERP_MASTER",
                    description="Supplier GSTIN registration status and master record unverified.",
                    urgency=MissingEvidenceUrgency.HIGH,
                    impact_on_investigation="Risk of transacting with cancelled/suspended GSTIN.",
                    recommended_action="Verify supplier GSTIN via Portal API or Master Data DB.",
                )
            )

        # 5. IRN / E-Invoice Validation
        total_weights += 15.0
        irn_present = False
        if invoice and getattr(invoice, "irn", None):
            irn_present = True
        elif decision and getattr(decision, "evidence", None):
            ev = decision.evidence
            if isinstance(ev, dict) and ev.get("irn_present"):
                irn_present = True

        if irn_present:
            present.append("IRN_EINVOICE_RECORD")
            earned_weights += 15.0
        else:
            tot_val = Decimal("0.00")
            if invoice and invoice.total_amount:
                tot_val = invoice.total_amount
            if tot_val >= Decimal("50000.00"):
                missing.append(
                    MissingEvidenceItem(
                        evidence_type="IRN_EINVOICE",
                        description="Invoice lacks verified IRN barcode or e-invoice confirmation.",
                        urgency=MissingEvidenceUrgency.HIGH,
                        impact_on_investigation="Mandatory B2B e-invoicing compliance under Rule 48(4) cannot be confirmed.",
                        recommended_action="Request e-invoice JSON QR payload from supplier.",
                    )
                )

        # 6. E-Way Bill / Proof of Movement
        total_weights += 10.0
        ewb_present = False
        if invoice and getattr(invoice, "eway_bill_no", None):
            ewb_present = True

        if ewb_present:
            present.append("EWAY_BILL_RECORD")
            earned_weights += 10.0
        else:
            tot_val = Decimal("0.00")
            if invoice and invoice.total_amount:
                tot_val = invoice.total_amount
            if tot_val >= Decimal("50000.00"):
                missing.append(
                    MissingEvidenceItem(
                        evidence_type="EWAY_BILL",
                        description="No E-Way Bill number attached for consignment > INR 50,000.",
                        urgency=MissingEvidenceUrgency.MEDIUM,
                        impact_on_investigation="Goods movement verification under Rule 138 cannot be established.",
                        recommended_action="Provide E-Way Bill number or transport delivery receipt.",
                    )
                )

        score = round(earned_weights / total_weights, 2) if total_weights > 0 else 0.0

        if score >= 0.90:
            state = EvidenceSufficiencyState.SUFFICIENT
            notes.append("Evidence is complete and sufficient for conclusive investigation.")
        elif score >= 0.60:
            state = EvidenceSufficiencyState.PARTIALLY_SUFFICIENT
            notes.append("Partial evidence available; key statutory records missing.")
        elif score > 0.0:
            state = EvidenceSufficiencyState.INSUFFICIENT
            notes.append("Evidence is insufficient; multiple critical records missing.")
        else:
            state = EvidenceSufficiencyState.NOT_AVAILABLE
            notes.append("No evidence records available.")

        return EvidenceSufficiencyReport(
            case_id=case_id,
            invoice_id=inv_id,
            sufficiency_state=state,
            score=score,
            present_evidence_types=present,
            missing_evidence_items=missing,
            notes=notes,
        )
