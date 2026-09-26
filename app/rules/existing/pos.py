"""
UC15 GST Compliance Agent — Gate 4: Place of Supply Correctness Rule (Sprint 4)
Validates tax structure consistency with state jurisdiction reference and audit evidence.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.reference.resolvers.effective_date import ResolutionStatus
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext


def _to_pct(val: Optional[float]) -> float:
    if val is None:
        return 0.0
    v = float(val)
    return v * 100.0 if (0.0 < v <= 1.0) else v


def _extract_date(d: Optional[object]) -> date:
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(d.strip(), fmt).date()
            except ValueError:
                continue
    return date(2023, 1, 1)


class PlaceOfSupplyRule(ComplianceRule):
    """
    Gate 4: Verifies tax type matches Place of Supply (POS).
    State codes are validated against statutory state master with temporal awareness.
    Intra-state (counterparty state == POS) must apply CGST + SGST (IGST = 0).
    Inter-state (counterparty state != POS) must apply IGST (CGST = SGST = 0).
    """

    @property
    def rule_id(self) -> str:
        return "POS_001"

    @property
    def name(self) -> str:
        return "Place of Supply Correctness"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PLACE_OF_SUPPLY

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 4

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        target_date = _extract_date(invoice.invoice_date)
        gstin = invoice.counterparty_gstin or invoice.gstin
        state_code = gstin[:2] if len(gstin) >= 2 else ""

        gstin_state = None
        ref_id = None
        ref_ver = None
        res_status = ResolutionStatus.NOT_FOUND.value

        # Query ReferenceService exclusively (legacy context inputs are adapted at context init)
        if context and context.reference_service:
            res = context.reference_service.resolve_state(state_code, target_date)
            res_status = res.status.value
            if res.is_resolved:
                st_rec = res.record
                gstin_state = st_rec.state_name
                ref_id = st_rec.reference_id
                ref_ver = st_rec.version

                if context.current_snapshot:
                    context.current_snapshot.set_state(st_rec)

        if gstin_state is None:
            msg = (
                f"State reference conflict for GSTIN prefix {state_code} on {target_date}."
                if res_status == ResolutionStatus.CONFLICT.value
                else f"Could not resolve state for GSTIN prefix {state_code} on {target_date}."
            )
            if context and context.current_snapshot:
                context.current_snapshot.record_unresolved(
                    "state",
                    str(state_code),
                    res_status,
                    msg,
                )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message=msg,
                actual_value=state_code,
                expected_value="Known 2-digit state code in reference",
                evidence={
                    "state_code": state_code,
                    "resolved": False,
                    "resolution_status": res_status,
                    "transaction_date": str(target_date),
                },
                rule_version=self.version,
            )

        raw_pos = invoice.place_of_supply.strip()
        if not raw_pos:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message="Place of supply is missing or empty - cannot determine tax jurisdiction.",
                actual_value=None,
                expected_value="Declared Place of Supply",
                applicability="REVIEW",
                applicability_reason="Missing Place of Supply prevents deterministic tax head verification.",
                evidence={
                    "counterparty_state": gstin_state,
                    "place_of_supply_declared": "",
                    "is_intra_state": False,
                    "resolution_status": res_status,
                    "transaction_date": str(target_date),
                },
                rule_version=self.version,
            )

        from app.rules.tax_treatment import (
            TaxJurisdiction,
            TaxMismatchType,
            TaxTreatmentEngine,
            TaxTreatmentType,
        )

        inv_cgst = float(invoice.cgst_rate)
        inv_sgst = float(invoice.sgst_rate)
        inv_utgst = float(getattr(invoice, "utgst_rate", 0.0))
        inv_igst = float(invoice.igst_rate)
        inv_cess = float(getattr(invoice, "cess_rate", 0.0))

        eval_res = TaxTreatmentEngine.evaluate_transaction(
            invoice_id=str(invoice.invoice_id),
            taxable_value=Decimal(str(invoice.taxable_value)),
            applied_cgst_rate=Decimal(str(_to_pct(inv_cgst))),
            applied_sgst_rate=Decimal(str(_to_pct(inv_sgst))),
            applied_utgst_rate=Decimal(str(_to_pct(inv_utgst))),
            applied_igst_rate=Decimal(str(_to_pct(inv_igst))),
            applied_cess_rate=Decimal(str(_to_pct(inv_cess))),
            supplier_gstin=invoice.seller_gstin,
            supplier_state=invoice.seller_state,
            recipient_gstin=invoice.buyer_gstin,
            recipient_state=invoice.buyer_state,
            place_of_supply=raw_pos,
            direction=invoice.direction,
            invoice_type=getattr(invoice, "invoice_type", "B2B"),
            is_rcm=invoice.is_rcm,
            reference_service=context.reference_service if context else None,
        )

        is_intra_state = eval_res.jurisdiction in (TaxJurisdiction.INTRA_STATE, TaxJurisdiction.UT_INTRA_STATE)
        is_ut_intra = eval_res.jurisdiction == TaxJurisdiction.UT_INTRA_STATE
        is_sez_or_export = eval_res.jurisdiction in (TaxJurisdiction.SEZ, TaxJurisdiction.EXPORT)

        # Expected tax structure string for evidence
        if is_ut_intra:
            expected_type = "INTRA_STATE (CGST + UTGST)"
        elif is_intra_state:
            expected_type = "INTRA_STATE (CGST + SGST)"
        elif is_sez_or_export:
            expected_type = "INTER_STATE_SEZ_ZERO_RATED (IGST)"
        else:
            expected_type = "INTER_STATE (IGST)"

        correct = True
        exposure_type = "NO_EXPOSURE"
        detail = ""

        # Evaluate validity according to jurisdiction
        if is_ut_intra:
            # Union territory without legislature: MUST apply CGST + UTGST. SGST is invalid!
            if inv_sgst > 0:
                correct = False
                exposure_type = "Tax Head Mismatch (SGST in UT)"
                detail = (
                    f"Supply in {raw_pos} (Union Territory without legislature) "
                    f"statutorily requires CGST + UTGST, but SGST was applied."
                )
            elif inv_igst > 0:
                correct = False
                exposure_type = "Tax Head Mismatch (IGST in Intra-UT)"
                detail = f"Counterparty state ({gstin_state}) matches place of supply - intra-state, should use CGST+UTGST, not IGST."
            elif inv_cgst > 0 and inv_utgst == 0:
                correct = False
                exposure_type = "Missing UTGST"
                detail = f"Supply in {raw_pos} requires CGST + UTGST, but UTGST rate is missing."
            elif inv_cgst == 0 and inv_utgst > 0:
                correct = False
                exposure_type = "Invalid Tax Head Combination"
                detail = f"Supply in {raw_pos} requires CGST alongside UTGST."
            else:
                detail = f"Supply within {raw_pos} correctly applies intra-UT CGST + UTGST structure."

        elif is_intra_state:
            # Intra-State (State or UT with legislature): MUST apply CGST + SGST. UTGST and IGST are invalid!
            if inv_igst > 0:
                correct = False
                exposure_type = "Tax Head Mismatch (IGST on Intra-State)"
                detail = (
                    f"Counterparty state ({gstin_state}) matches place of supply - intra-state, "
                    f"should use CGST+SGST, not IGST."
                )
            elif inv_utgst > 0:
                correct = False
                exposure_type = "Invalid Tax Head (UTGST in State)"
                detail = f"Supply in {raw_pos} (State with legislature) statutorily requires CGST + SGST, but UTGST was applied."
            elif (inv_cgst > 0 and inv_sgst == 0) or (inv_sgst > 0 and inv_cgst == 0):
                correct = False
                exposure_type = "Invalid Tax Head Combination"
                detail = f"Intra-state supply in {raw_pos} requires both CGST and SGST in equal measure."
            elif inv_cgst == 0 and inv_sgst == 0 and not is_sez_or_export:
                correct = False
                exposure_type = "Zero Tax Applied"
                detail = f"Intra-state supply in {raw_pos} has no GST heads applied."
            else:
                detail = f"Counterparty state ({gstin_state}) matches place of supply - intra-state CGST + SGST applied correctly."

        elif is_sez_or_export:
            # SEZ / Export: Zero-rated inter-state supply under IGST Act Section 16
            if inv_cgst > 0 or inv_sgst > 0 or inv_utgst > 0:
                correct = False
                exposure_type = "Invalid Tax Head for Zero-Rated/SEZ"
                detail = (
                    f"Supply context ({gstin_state} -> {invoice.place_of_supply}) "
                    f"- inter-state / zero-rated SEZ, should use IGST or Zero-Rated structure."
                )
            else:
                detail = f"Supply context ({gstin_state} -> {invoice.place_of_supply}) - correctly structured under IGST Act Sec 16."

        else:
            # Inter-State Supply: MUST apply IGST. CGST / SGST / UTGST are invalid!
            if inv_cgst > 0 or inv_sgst > 0 or inv_utgst > 0:
                correct = False
                exposure_type = "Tax Head Mismatch (CGST/SGST on Inter-State)"
                detail = (
                    f"Supply context ({gstin_state} -> {invoice.place_of_supply}) "
                    f"- inter-state / zero-rated SEZ, should use IGST or Zero-Rated structure."
                )
            elif inv_igst == 0:
                correct = False
                exposure_type = "Missing IGST"
                detail = f"Inter-state supply context ({gstin_state} -> {invoice.place_of_supply}) requires IGST."
            else:
                detail = f"Supply context ({gstin_state} -> {invoice.place_of_supply}) correctly applies inter-state IGST structure."

        # Check for mixed IGST + CGST/SGST/UTGST invalid combinations
        if inv_igst > 0 and (inv_cgst > 0 or inv_sgst > 0 or inv_utgst > 0):
            correct = False
            exposure_type = "Invalid Tax Combination (Mixed IGST with CGST/SGST/UTGST)"
            detail = "Invalid tax combination: IGST cannot be charged alongside CGST, SGST, or UTGST on the same supply."

        evidence = {
            "counterparty_state": gstin_state,
            "place_of_supply_declared": invoice.place_of_supply,
            "is_intra_state": is_intra_state,
            "expected_tax_structure": expected_type,
            "tax_jurisdiction": eval_res.jurisdiction.value,
            "tax_treatment": eval_res.treatment.value,
            "applied_taxes": {
                "cgst": inv_cgst,
                "sgst": inv_sgst,
                "utgst": inv_utgst,
                "igst": inv_igst,
                "cess": inv_cess,
            },
            "expected_rates": {
                "cgst": float(eval_res.expected_cgst_rate),
                "sgst": float(eval_res.expected_sgst_rate),
                "utgst": float(eval_res.expected_utgst_rate),
                "igst": float(eval_res.expected_igst_rate),
                "cess": float(eval_res.expected_cess_rate),
            },
            "valid_structure": correct,
            "reference_id": ref_id,
            "reference_version": ref_ver,
            "resolution_status": res_status,
            "transaction_date": str(target_date),
            "tax_treatment_result": eval_res.to_dict(),
        }

        trace = {
            "counterparty_state": gstin_state,
            "supplier_state": eval_res.supplier_state,
            "place_of_supply": invoice.place_of_supply,
            "is_intra_state": is_intra_state,
            "applied_taxes": {"cgst": inv_cgst, "sgst": inv_sgst, "utgst": inv_utgst, "igst": inv_igst},
            "expected_tax_structure": expected_type,
            "tax_jurisdiction": eval_res.jurisdiction.value,
            "tax_treatment": eval_res.treatment.value,
            "reference_id": ref_id,
            "reference_version": ref_ver,
        }

        obs_val = {
            "state": gstin_state,
            "pos": invoice.place_of_supply,
            "cgst": inv_cgst,
            "sgst": inv_sgst,
            "utgst": inv_utgst,
            "igst": inv_igst,
        }
        app_reason = "Place of Supply state jurisdiction vs tax head alignment verification."

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS if correct else ValidationStatus.FAIL,
            severity=self.severity if not correct else Severity.INFO,
            category=self.category,
            message=detail,
            actual_value=obs_val,
            expected_value="CGST+SGST/UTGST for intra-state, IGST for inter-state",
            observed_value=obs_val,
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            reference_id=ref_id,
            reference_version=ref_ver,
            calculation_trace=trace,
            financial_exposure_type=exposure_type if not correct else "NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
