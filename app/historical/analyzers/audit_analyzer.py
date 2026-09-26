"""
UC15 GST Compliance Agent — Historical Audit & Retroactive Simulation Analyzer (Sprint 5)
Evaluates historical transactions using reference data valid on the transaction date
and compares outcomes against recorded historical results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision
from app.historical.models.audit import AuditOutcome, HistoricalAuditComparison
from app.historical.models.record import HistoricalRecord
from app.reference.services.reference_service import ReferenceService
from app.rules.context import ValidationContext


class HistoricalAuditAnalyzer:
    """
    Executes retroactive simulations on historical transactions using effective-date reference resolution.
    Identifies if statutory outcomes or reference versions shifted over time without mutating historical records.
    """

    def __init__(self, reference_service: Optional[ReferenceService] = None) -> None:
        self.reference_service = reference_service or ReferenceService(auto_load=True)

    def audit_record(
        self,
        record: HistoricalRecord,
        invoice: Optional[Invoice] = None,
        retroactive_decision: Optional[ComplianceDecision] = None,
    ) -> HistoricalAuditComparison:
        """
        Perform retroactive comparison on a single historical transaction.
        If retroactive_decision is not provided, runs validation using the transaction date's references.
        """
        from app.engine.decision_engine import DecisionEngine
        from app.engine.validation_engine import ValidationEngine

        # Build synthetic invoice if not passed
        if invoice is None:
            # Map direction, counterparty GSTIN, etc.
            invoice = Invoice.from_record(
                invoice_no=record.invoice_id,
                invoice_date=record.invoice_date.isoformat(),
                direction=record.direction,
                counterparty_gstin=record.counterparty_gstin,
                counterparty_name=record.counterparty_name,
                place_of_supply=record.place_of_supply,
                hsn_code=record.hsn_code,
                item_desc=record.item_desc,
                taxable_value_inr=float(record.taxable_value),
                cgst_rate=0.0,
                sgst_rate=0.0,
                igst_rate=0.0,
                total_amt=float(record.total_amount),
                eway_bill_status="",
                gstr2b_reflected=True,
            )

        # Run retroactive validation if not provided
        if retroactive_decision is None:
            context = ValidationContext(reference_service=self.reference_service)
            v_engine = ValidationEngine(context=context)
            d_engine = DecisionEngine()
            report = v_engine.validate(invoice)
            retroactive_decision = d_engine.decide(invoice, report)

        orig_status = (record.compliance_status or "").upper()
        retro_status = (retroactive_decision.status or "").upper()

        # Extract retroactive reference versions
        retro_versions: Dict[str, str] = {}
        snap = getattr(retroactive_decision, "reference_snapshot", None)
        if snap:
            for rk, rv in getattr(snap, "references", {}).items():
                retro_versions[rk] = getattr(rv, "version", "1.0")

        orig_versions = dict(record.reference_versions)
        ref_diffs: List[str] = []
        if orig_versions and retro_versions:
            for k in set(orig_versions.keys()) & set(retro_versions.keys()):
                v_orig = orig_versions.get(k)
                v_retro = retro_versions.get(k)
                if v_orig != v_retro:
                    ref_diffs.append(f"Reference '{k}': original version='{v_orig}', retroactive version='{v_retro}'")

        # Gate failures comparison
        retro_failed_rules = [
            g.rule_id for g in getattr(retroactive_decision, "gates", [])
            if g.status == "FAIL"
        ]

        # Determine outcome
        outcome = AuditOutcome.SAME_RESULT
        reason = "Retroactive evaluation under historical reference yielded identical compliance verdict."

        if orig_status != retro_status:
            if orig_status == "NEEDS_REVIEW" and retro_status in ("COMPLIANT", "NON_COMPLIANT"):
                outcome = AuditOutcome.PREVIOUSLY_UNRESOLVED
                reason = f"Transaction was previously {orig_status}; retroactive reference resolution resolved status to {retro_status}."
            elif orig_status == "NON_COMPLIANT" and retro_status == "COMPLIANT":
                outcome = AuditOutcome.NEWLY_COMPLIANT
                reason = f"Transaction status upgraded from {orig_status} to {retro_status} under applicable historical reference data."
            elif orig_status in ("COMPLIANT", "NEEDS_REVIEW") and retro_status == "NON_COMPLIANT":
                outcome = AuditOutcome.NEWLY_NON_COMPLIANT
                reason = f"Transaction newly classified as {retro_status} (previously {orig_status}) under retroactive verification."
            else:
                outcome = AuditOutcome.RESULT_CHANGED
                reason = f"Compliance verdict shifted from {orig_status} to {retro_status}."
        elif ref_diffs:
            outcome = AuditOutcome.REFERENCE_CHANGED
            reason = f"Status remained {orig_status}, but underlying reference version(s) changed: {'; '.join(ref_diffs)}."

        evidence = {
            "invoice_id": record.invoice_id,
            "invoice_date": record.invoice_date.isoformat(),
            "original_status": orig_status,
            "retroactive_status": retro_status,
            "outcome": outcome.value,
            "reference_differences": ref_diffs,
            "original_failed_rules": record.failed_rule_ids,
            "retroactive_failed_rules": retro_failed_rules,
            "reason": reason,
        }

        return HistoricalAuditComparison(
            invoice_id=record.invoice_id,
            invoice_date=record.invoice_date,
            original_status=orig_status,
            retroactive_status=retro_status,
            outcome=outcome,
            original_reference_versions=orig_versions,
            retroactive_reference_versions=retro_versions,
            reference_differences=ref_diffs,
            original_failed_rules=record.failed_rule_ids,
            retroactive_failed_rules=retro_failed_rules,
            reason=reason,
            evidence=evidence,
        )

    def audit_batch(
        self,
        records: List[HistoricalRecord],
        invoices: Optional[Dict[str, Invoice]] = None,
    ) -> List[HistoricalAuditComparison]:
        """
        Audit a batch of historical records.
        """
        results: List[HistoricalAuditComparison] = []
        inv_map = invoices or {}
        for rec in records:
            inv = inv_map.get(rec.invoice_id)
            comp = self.audit_record(rec, invoice=inv)
            results.append(comp)
        return results
