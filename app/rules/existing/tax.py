"""
UC15 GST Compliance Agent — Gate 3: Tax Rate Correctness Rule (Sprint 4)
Validates applied tax rates against temporal statutory schedule with reference audit evidence.
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


def _to_pct(val: Optional[float]) -> float:
    if val is None:
        return 0.0
    v = float(val)
    return v * 100.0 if (0.0 < v <= 1.0) else v


class TaxRateCorrectnessRule(ComplianceRule):
    """
    Gate 3: Verifies that applied CGST/SGST or IGST tax rates match official HSN master rates.
    Temporal-aware: evaluates rates against statutory notifications active on transaction date.
    """

    @property
    def rule_id(self) -> str:
        return "TAX_001"

    @property
    def name(self) -> str:
        return "Tax Rate Correctness"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TAX

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        target_date = _extract_date(invoice.invoice_date)
        inv_cgst = float(invoice.cgst_rate)
        inv_sgst = float(invoice.sgst_rate)
        inv_igst = float(invoice.igst_rate)
        using_igst = inv_igst > 0

        hsn_cgst = None
        hsn_sgst = None
        hsn_igst = None
        ref_id = None
        ref_ver = None
        notif_no = None
        res_status = ResolutionStatus.NOT_FOUND.value
        rate_found = False

        # Query ReferenceService exclusively (legacy context inputs are adapted at context init)
        if context and context.reference_service:
            res = context.reference_service.resolve_tax_rate(
                invoice.hsn_code,
                target_date,
                is_interstate=using_igst,
            )
            res_status = res.status.value
            if res.is_resolved:
                tax_rec = res.record
                hsn_cgst = float(tax_rec.cgst_rate)
                hsn_sgst = float(tax_rec.sgst_rate)
                hsn_igst = float(tax_rec.igst_rate)
                ref_id = tax_rec.reference_id
                ref_ver = tax_rec.version
                notif_no = tax_rec.notification_no
                rate_found = True

                if context.current_snapshot:
                    context.current_snapshot.set_tax_rate(tax_rec)

        if not rate_found:
            msg = (
                f"Tax rate schedule conflict for HSN '{invoice.hsn_code}' on {target_date}."
                if res_status == ResolutionStatus.CONFLICT.value
                else "Cannot verify rate - HSN code not found in master."
            )
            if context and context.current_snapshot:
                context.current_snapshot.record_unresolved(
                    "tax_rate",
                    str(invoice.hsn_code),
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
                actual_value=None,
                expected_value=None,
                applicability="REVIEW",
                applicability_reason="Tax rate schedule conflict or missing HSN master reference.",
                evidence={
                    "hsn_code": invoice.hsn_code,
                    "master_found": False,
                    "resolution_status": res_status,
                    "transaction_date": str(target_date),
                },
                rule_version=self.version,
            )

        inv_cgst_pct = _to_pct(inv_cgst)
        inv_sgst_pct = _to_pct(inv_sgst)
        inv_utgst_pct = _to_pct(float(getattr(invoice, "utgst_rate", 0.0)))
        inv_igst_pct = _to_pct(inv_igst)
        inv_cess_pct = _to_pct(float(getattr(invoice, "cess_rate", 0.0)))

        hsn_cgst_pct = _to_pct(hsn_cgst)
        hsn_sgst_pct = _to_pct(hsn_sgst)
        hsn_igst_pct = _to_pct(hsn_igst)

        tolerance = float(context.rate_tolerance_pct) if context else 0.01

        is_exempt_or_zero_rated = (
            (hsn_cgst_pct == 0 and hsn_sgst_pct == 0 and hsn_igst_pct == 0)
            or getattr(invoice, "invoice_type", "B2B").upper() in ("EXEMPT", "SEZ", "EXPORT")
        )

        from app.rules.tax_treatment import TaxJurisdiction, TaxTreatmentEngine

        expected_combined_rate = Decimal(str(hsn_igst_pct if hsn_igst_pct > 0 else (hsn_cgst_pct + hsn_sgst_pct)))

        eval_res = TaxTreatmentEngine.evaluate_transaction(
            taxable_value=Decimal(str(invoice.taxable_value)),
            supplier_state=invoice.seller_state,
            recipient_state=invoice.buyer_state,
            place_of_supply=invoice.place_of_supply,
            applied_cgst_rate=Decimal(str(inv_cgst_pct)),
            applied_sgst_rate=Decimal(str(inv_sgst_pct)),
            applied_utgst_rate=Decimal(str(inv_utgst_pct)),
            applied_igst_rate=Decimal(str(inv_igst_pct)),
            applied_cess_rate=Decimal(str(inv_cess_pct)),
            applicable_rate=expected_combined_rate,
            reported_total_tax=getattr(invoice, "reported_total_tax", None),
            reported_total_amount=getattr(invoice, "reported_total_amount", None),
            invoice_type=getattr(invoice, "invoice_type", "B2B"),
            is_export=(getattr(invoice, "invoice_type", "B2B").upper() == "EXPORT"),
            is_sez=(getattr(invoice, "invoice_type", "B2B").upper() == "SEZ"),
            tolerance=Decimal(str(tolerance)),
        )

        using_igst = inv_igst_pct > 0
        if is_exempt_or_zero_rated:
            rate_ok = (inv_cgst_pct == 0 and inv_sgst_pct == 0 and inv_utgst_pct == 0 and inv_igst_pct == 0)
            zero_ok = True
        elif using_igst:
            rate_ok = abs(inv_igst_pct - hsn_igst_pct) <= tolerance
            zero_ok = (inv_cgst_pct == 0 and inv_sgst_pct == 0 and inv_utgst_pct == 0)
        else:
            # Intra-state: CGST + SGST (or CGST + UTGST)
            rate_ok = (
                abs(inv_cgst_pct - hsn_cgst_pct) <= tolerance
                and (abs(inv_sgst_pct - hsn_sgst_pct) <= tolerance or abs(inv_utgst_pct - hsn_sgst_pct) <= tolerance)
            )
            zero_ok = (inv_igst_pct == 0)

        math_ok = eval_res.is_math_correct
        invoice_total_ok = eval_res.is_invoice_total_correct

        is_intra = eval_res.tax_jurisdiction in (TaxJurisdiction.INTRA_STATE, TaxJurisdiction.UT_INTRA_STATE)

        evidence = {
            "hsn_code": invoice.hsn_code,
            "tax_type": eval_res.tax_treatment.value,
            "tax_treatment": eval_res.tax_treatment.value,
            "tax_jurisdiction": eval_res.tax_jurisdiction.value,
            "applied_rates": {
                "cgst": inv_cgst_pct,
                "sgst": inv_sgst_pct,
                "utgst": inv_utgst_pct,
                "igst": inv_igst_pct,
                "cess": inv_cess_pct,
            },
            "expected_rates": {
                "cgst": hsn_cgst_pct,
                "sgst": hsn_sgst_pct,
                "utgst": float(eval_res.expected_utgst_rate),
                "igst": hsn_igst_pct,
                "cess": float(eval_res.expected_cess_rate),
            },
            "applied_amounts": {
                "cgst": float(eval_res.applied_cgst_amount),
                "sgst": float(eval_res.applied_sgst_amount),
                "utgst": float(eval_res.applied_utgst_amount),
                "igst": float(eval_res.applied_igst_amount),
                "cess": float(eval_res.applied_cess_amount),
                "total": float(eval_res.applied_total_tax),
            },
            "expected_amounts": {
                "cgst": float(eval_res.expected_cgst_amount),
                "sgst": float(eval_res.expected_sgst_amount),
                "utgst": float(eval_res.expected_utgst_amount),
                "igst": float(eval_res.expected_igst_amount),
                "cess": float(eval_res.expected_cess_amount),
                "total": float(eval_res.expected_total_tax),
            },
            "tolerance": tolerance,
            "rate_matched": rate_ok,
            "math_matched": math_ok,
            "invoice_total_matched": invoice_total_ok,
            "zero_tax_correct": zero_ok,
            "reference_id": ref_id,
            "reference_version": ref_ver,
            "notification_no": notif_no,
            "resolution_status": res_status,
            "transaction_date": str(target_date),
            "tax_treatment_result": eval_res.to_dict(),
        }

        trace = {
            "input_rates": {"cgst": inv_cgst_pct, "sgst": inv_sgst_pct, "utgst": inv_utgst_pct, "igst": inv_igst_pct},
            "expected_rates": {"cgst": hsn_cgst_pct, "sgst": hsn_sgst_pct, "utgst": float(eval_res.expected_utgst_rate), "igst": hsn_igst_pct},
            "tolerance": tolerance,
            "resolution_status": res_status,
            "reference_id": ref_id,
            "reference_version": ref_ver,
            "math_matched": math_ok,
            "invoice_total_matched": invoice_total_ok,
        }

        app_reason = "Tax rate quantum and mathematical tax calculation verification against statutory HSN schedule."

        def _fmt(n: float) -> str:
            return str(int(n)) if n.is_integer() else str(n)

        # Gate 3 Failure Hierarchy: Rate Mismatch -> Math Mismatch -> Invoice Total Mismatch
        if not (rate_ok and zero_ok):
            detail = (
                f"Invoice shows CGST {_fmt(inv_cgst_pct)}% / SGST {_fmt(inv_sgst_pct)}% / IGST {_fmt(inv_igst_pct)}% "
                f"- official rate for HSN {invoice.hsn_code} is CGST {_fmt(hsn_cgst_pct)}% / "
                f"SGST {_fmt(hsn_sgst_pct)}% / IGST {_fmt(hsn_igst_pct)}%."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=detail,
                actual_value={"cgst": inv_cgst_pct, "sgst": inv_sgst_pct, "igst": inv_igst_pct},
                expected_value={"cgst": hsn_cgst_pct, "sgst": hsn_sgst_pct, "igst": hsn_igst_pct},
                observed_value={"cgst": inv_cgst_pct, "sgst": inv_sgst_pct, "igst": inv_igst_pct},
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=ref_id,
                reference_version=ref_ver,
                calculation_trace=trace,
                financial_exposure_type="Tax Rate Mismatch",
                evidence=evidence,
                rule_version=self.version,
            )

        if not math_ok:
            detail = (
                f"Tax calculation mismatch: Applied tax ₹{eval_res.applied_total_tax:,.2f} differs from "
                f"mathematically calculated ₹{eval_res.expected_total_tax:,.2f} on taxable value ₹{invoice.taxable_value:,.2f}."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=detail,
                actual_value=float(eval_res.applied_total_tax),
                expected_value=float(eval_res.expected_total_tax),
                observed_value=float(eval_res.applied_total_tax),
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=ref_id,
                reference_version=ref_ver,
                calculation_trace=trace,
                financial_exposure_type="Tax Calculation Mismatch",
                evidence=evidence,
                rule_version=self.version,
            )

        if not invoice_total_ok:
            detail = (
                f"Invoice total mismatch: Reported total ₹{eval_res.reported_total_amount:,.2f} differs from "
                f"expected ₹{eval_res.expected_invoice_total:,.2f} (Taxable ₹{invoice.taxable_value:,.2f} + Tax ₹{eval_res.expected_total_tax:,.2f})."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=detail,
                actual_value=float(eval_res.reported_total_amount or 0),
                expected_value=float(eval_res.expected_invoice_total),
                observed_value=float(eval_res.reported_total_amount or 0),
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=ref_id,
                reference_version=ref_ver,
                calculation_trace=trace,
                financial_exposure_type="Invoice Total Mismatch",
                evidence=evidence,
                rule_version=self.version,
            )

        # Gate 3 Passes cleanly. If tax head alignment (IGST on intra-state) needs attention, note Gate 4 handoff.
        msg_note = " (Intra-state CGST+SGST structure evaluated in Gate 4)" if (using_igst and is_intra) else ""
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS,
            severity=Severity.INFO,
            category=self.category,
            message=f"Rate Quantum ({hsn_igst_pct:.0f}%) matches official rate for HSN {invoice.hsn_code}{msg_note}.",
            actual_value={"cgst": inv_cgst_pct, "sgst": inv_sgst_pct, "igst": inv_igst_pct},
            expected_value={"cgst": hsn_cgst_pct, "sgst": hsn_sgst_pct, "igst": hsn_igst_pct},
            observed_value={"cgst": inv_cgst_pct, "sgst": inv_sgst_pct, "igst": inv_igst_pct},
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            reference_id=ref_id,
            reference_version=ref_ver,
            calculation_trace=trace,
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
