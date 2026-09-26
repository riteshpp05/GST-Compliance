"""
UC15 GST Compliance Agent — Decision Engine (v2.0)
Translates ValidationReports into actionable ComplianceDecisions.
Distinguishes statutory gate compliance from data-quality findings.
"""
from __future__ import annotations

import uuid
from typing import List, Optional
from app.domain.enums.compliance_status import ComplianceStatus
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationReport, ValidationResult
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DecisionEngine:
    """
    Evaluates rule validation reports and derives compliance classification.
    Implements 6-gate decision matrix while isolating data-quality findings:
      - Gate 1 fail       -> NON_COMPLIANT (hard override)
      - 0 gate failures   -> COMPLIANT (filing ready)
      - 1 gate failure    -> NEEDS_REVIEW (same-cycle SLA)
      - 2+ gate failures  -> NON_COMPLIANT (blocked)
    """

    def decide(self, invoice: Invoice, report: ValidationReport) -> ComplianceDecision:
        """Derive a ComplianceDecision from the validation report."""
        alerts: List[str] = []

        # Separate statutory 6 gates from data quality pre-checks
        statutory_results = [r for r in report.results if r.gate_no is not None]
        dq_results = [
            r for r in report.results
            if r.category == RuleCategory.DATA_QUALITY.value or r.gate_no is None
        ]

        gates_to_evaluate = statutory_results if statutory_results else report.results

        # Find gate 1 result
        gate1 = next(
            (r for r in gates_to_evaluate if r.gate_no == 1 or r.rule_id == "GSTIN_001"),
            None,
        )
        gate2 = next(
            (r for r in gates_to_evaluate if r.gate_no == 2 or r.rule_id == "HSN_001"),
            None,
        )

        if gate2 and (gate2.status in (ValidationStatus.FAIL.value, ValidationStatus.NEEDS_REVIEW.value)) and "not found" in gate2.message.lower():
            alerts.append(
                f"HSN code {invoice.hsn_code} not found in the master - requires classification review."
            )

        # Track Data Quality issues in alerts
        for dq in dq_results:
            if dq.status in (ValidationStatus.FAIL.value, ValidationStatus.WARNING.value):
                alerts.append(f"Data Quality Notice: [{dq.rule_id}] {dq.name} - {dq.message}")

        failed_results = [r for r in gates_to_evaluate if r.status == ValidationStatus.FAIL.value]
        failed_count = len(failed_results)

        review_results = [r for r in gates_to_evaluate if r.status == ValidationStatus.NEEDS_REVIEW.value]
        review_count = len(review_results)

        hard_override = gate1 is not None and gate1.status == ValidationStatus.FAIL.value

        if hard_override:
            status = ComplianceStatus.NON_COMPLIANT.value
            justification = (
                f"Gate 1 (GSTIN Format Validity) failed - {gate1.message} "
                f"This blocks filing regardless of every other gate."
            )
            recommended_action = "Correct the counterparty GSTIN before this invoice can be included in any GSTR filing."
            sap_action = "Held from GSTR-1/GSTR-3B filing - GSTIN correction required in KNA1/LFA1 master data."
        elif failed_count >= 2:
            status = ComplianceStatus.NON_COMPLIANT.value
            gate_names = ", ".join(g.name for g in failed_results)
            justification = f"{failed_count} gates failed ({gate_names}) - too many issues to include in this filing cycle."
            recommended_action = "Correct all flagged issues before this invoice can be filed."
            sap_action = "Held from GSTR-1/GSTR-3B filing pending multi-issue correction."
        elif failed_count == 1:
            status = ComplianceStatus.NEEDS_REVIEW.value
            f = failed_results[0]
            justification = f"1 gate failed: {f.name} - {f.detail}"
            recommended_action = "Flag for correction within this filing cycle; not severe enough to hold the whole return."
            sap_action = "Flagged in the compliance queue - no automated correction, held for tax team review."
        elif review_count > 0:
            status = ComplianceStatus.NEEDS_REVIEW.value
            gate_names = ", ".join(g.name for g in review_results)
            justification = (
                f"{review_count} gate(s) require review ({gate_names}) due to missing or conflicting "
                f"statutory reference data. Insufficient evidence to conclude non-compliance."
            )
            recommended_action = "Verify classification, tax rate schedules, or statutory policy with the tax department."
            sap_action = "Flagged in the compliance queue - held for tax master data review."
        else:
            status = ComplianceStatus.COMPLIANT.value
            justification = (
                "All applicable gates passed - GSTIN valid, HSN and tax rate correct, "
                "place of supply consistent, e-Way Bill and ITC checks clear."
            )
            recommended_action = "Include in this period's GSTR filing - no correction needed."
            sap_action = "Read via BKPF/BSEG + KONV (tax conditions) + KNA1/LFA1 (GSTIN) - ready for GSTR-1/GSTR-3B filing."

        audit_ref = f"GST-{uuid.uuid4().hex[:10].upper()}"

        return ComplianceDecision(
            invoice_no=invoice.invoice_number,
            invoice_date=str(invoice.invoice_date),
            direction=invoice.direction,
            counterparty_gstin=invoice.counterparty_gstin,
            counterparty_name=invoice.counterparty_name,
            place_of_supply=invoice.place_of_supply,
            hsn_code=invoice.hsn_code,
            item_desc=invoice.item_desc,
            taxable_value_inr=float(invoice.taxable_value),
            total_amt=float(invoice.total_amount),
            gates=gates_to_evaluate,
            failed_gate_count=failed_count,
            status=status,
            justification=justification,
            recommended_action=recommended_action,
            sap_action=sap_action,
            audit_trail_ref=audit_ref,
            hard_override=hard_override,
            alerts=alerts,
            data_quality_results=dq_results,
            reference_snapshot=report.metadata.get("reference_snapshot"),
        )
