"""
UC15 GST Compliance Agent — Contradiction Detector (Sprint 22)
Detects explicit contradictions across available evidence signals for finance investigations.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.reconciliation.models import ContradictionFinding, ContradictionSeverity


class ContradictionDetector:
    """
    Analyzes cross-source evidence signals to detect logical and financial contradictions.
    """

    def detect_contradictions(
        self,
        invoice: Optional[Invoice] = None,
        decision: Optional[ComplianceDecision] = None,
        gstr2b_record: Optional[Dict[str, Any]] = None,
        supplier_master: Optional[Dict[str, Any]] = None,
    ) -> List[ContradictionFinding]:
        contradictions: List[ContradictionFinding] = []

        inv_id = (
            getattr(invoice, "invoice_id", None)
            or getattr(decision, "invoice_no", None)
            or "UNKNOWN"
        )

        # 1. Tax Type vs Place of Supply Contradiction
        if invoice:
            cgst_charged = float(invoice.cgst_amount or 0) > 0 or float(invoice.cgst_rate or 0) > 0
            igst_charged = float(invoice.igst_amount or 0) > 0 or float(invoice.igst_rate or 0) > 0
            sup_state = (invoice.supplier_gstin[:2] if invoice.supplier_gstin and len(invoice.supplier_gstin) >= 2 else "")
            rec_state = (invoice.place_of_supply or (invoice.recipient_gstin[:2] if invoice.recipient_gstin and len(invoice.recipient_gstin) >= 2 else ""))

            if sup_state and rec_state:
                is_inter_state = (sup_state != rec_state)
                if is_inter_state and cgst_charged and not igst_charged:
                    contradictions.append(
                        ContradictionFinding(
                            contradiction_id=f"CON-{inv_id}-POS-TAX",
                            contradiction_type="POS_TAX_HEAD_CONTRADICTION",
                            severity=ContradictionSeverity.CRITICAL,
                            description=f"Intra-State tax (CGST+SGST) charged on Inter-State transaction (Supplier State {sup_state} != Place of Supply {rec_state}).",
                            conflicting_signals=[
                                {"signal": "Tax Heads Charged", "value": "CGST + SGST"},
                                {"signal": "Supplier State", "value": sup_state},
                                {"signal": "Place of Supply / Recipient State", "value": rec_state},
                            ],
                            impact_on_validity="Section 77 CGST / Section 19 IGST misclassification; tax paid under wrong tax head.",
                            recommended_investigation="Re-evaluate Place of Supply under Section 10/12 IGST Act and request supplier tax head credit adjustment.",
                        )
                    )

        # 2. Cancelled/Suspended Supplier with Active IRN / Transaction
        if supplier_master:
            status = supplier_master.get("status", "ACTIVE").upper()
            cancellation_date = supplier_master.get("cancellation_date")
            inv_date_str = str(getattr(invoice, "invoice_date", "")) if invoice else ""

            if status in ("CANCELLED", "SUSPENDED"):
                has_irn = bool(getattr(invoice, "irn", None))
                contradictions.append(
                    ContradictionFinding(
                        contradiction_id=f"CON-{inv_id}-SUPPLIER-STATUS",
                        contradiction_type="CANCELLED_SUPPLIER_ACTIVE_IRN_CONTRADICTION",
                        severity=ContradictionSeverity.CRITICAL,
                        description=f"Invoice issued by supplier with GSTIN status '{status}' (Cancelled on {cancellation_date or 'N/A'}).",
                        conflicting_signals=[
                            {"signal": "Supplier GSTIN Status", "value": status},
                            {"signal": "Invoice Date", "value": inv_date_str},
                            {"signal": "IRN E-Invoice Claimed", "value": "YES" if has_irn else "NO"},
                        ],
                        impact_on_validity="Section 16(2)(a) violation; invalid tax invoice issued by non-registered/cancelled entity.",
                        recommended_investigation="Block ITC claim immediately and verify GST portal registration cancellation effective date.",
                    )
                )

        # 3. ERP Payment Recorded vs GSTR-2B Missing
        if invoice and invoice.direction == "AP":
            payment_made = getattr(invoice, "is_paid", False) or getattr(invoice, "payment_status", "") == "PAID"
            in_gstr2b = getattr(invoice, "is_gstr2b_matched", False)

            if payment_made and not in_gstr2b and gstr2b_record is None:
                contradictions.append(
                    ContradictionFinding(
                        contradiction_id=f"CON-{inv_id}-ERP-2B-MISMATCH",
                        contradiction_type="ERP_PAID_GSTR2B_MISSING_CONTRADICTION",
                        severity=ContradictionSeverity.HIGH,
                        description="Payment remitted to supplier in ERP, but invoice is completely missing from buyer's GSTR-2B statement.",
                        conflicting_signals=[
                            {"signal": "ERP Payment Status", "value": "PAID"},
                            {"signal": "GSTR-2B Filing Status", "value": "NOT_FOUND"},
                        ],
                        impact_on_validity="Section 16(2)(aa) ITC risk; payment made but tax credit not auto-populated in GSTR-2B.",
                        recommended_investigation="Withhold further payments or issue communication to supplier to file GSTR-1 for period.",
                    )
                )

        # 4. Failed Gate Contradictions from Decision
        if decision and getattr(decision, "gates", None):
            for g in decision.gates:
                if g.status == "FAIL" and g.gate_no == 3:
                    contradictions.append(
                        ContradictionFinding(
                            contradiction_id=f"CON-{inv_id}-TAX-RATE",
                            contradiction_type="EFFECTIVE_DATE_TAX_RATE_CONTRADICTION",
                            severity=ContradictionSeverity.HIGH,
                            description=f"Applied tax rate ({g.actual_value}%) contradicts statutory schedule rate ({g.expected_value}%) for transaction date.",
                            conflicting_signals=[
                                {"signal": "Recorded Invoice Tax Rate", "value": f"{g.actual_value}%"},
                                {"signal": "Statutory Effective Rate", "value": f"{g.expected_value}%"},
                            ],
                            impact_on_validity="Tax rate misclassification; potential under/overcharging of statutory tax.",
                            recommended_investigation="Review HSN classification schedule and effective statutory rate notifications.",
                        )
                    )

        return contradictions
