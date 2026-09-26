"""
UC15 GST Compliance Agent — Gate 2: HSN/SAC Code Validity Rule (Sprint 4)
Verifies HSN/SAC classification against temporal reference master with resolution audit evidence.
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


class HSNValidityRule(ComplianceRule):
    """
    Gate 2: Verifies that the invoice HSN/SAC classification exists in the official master.
    Effective-date aware: distinguishes active, expired, future, and conflicting classifications.
    Unknown HSN fails validation and cascades to Gate 3 rate check failure.
    """

    @property
    def rule_id(self) -> str:
        return "HSN_001"

    @property
    def name(self) -> str:
        return "HSN/SAC Code Validity"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.CLASSIFICATION

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 2

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        hsn_code = invoice.hsn_code
        target_date = _extract_date(invoice.invoice_date)

        ref_id = None
        ref_ver = None
        eff_from = None
        eff_to = None
        res_status = ResolutionStatus.NOT_FOUND.value
        res_reason = None
        desc = None
        cgst = None
        sgst = None
        igst = None
        is_resolved = False
        is_conflict = False

        # Query ReferenceService exclusively (legacy context inputs are adapted at context init)
        if context and context.reference_service:
            res = context.reference_service.resolve_hsn(hsn_code, target_date)
            res_status = res.status.value
            res_reason = res.reason

            if res.is_resolved:
                is_resolved = True
                rec = res.record
                ref_id = rec.reference_id
                ref_ver = rec.version
                eff_from = str(rec.effective_from)
                eff_to = str(rec.effective_to) if rec.effective_to else None
                desc = rec.description
                cgst = str(rec.default_cgst_rate) if rec.default_cgst_rate is not None else None
                sgst = str(rec.default_sgst_rate) if rec.default_sgst_rate is not None else None
                igst = str(rec.default_igst_rate) if rec.default_igst_rate is not None else None

                if context.current_snapshot:
                    context.current_snapshot.set_hsn(rec)
            elif res.status == ResolutionStatus.CONFLICT:
                is_conflict = True

        evidence = {
            "hsn_code": hsn_code,
            "master_found": is_resolved,
            "description": desc,
            "official_rates": {
                "cgst": cgst,
                "sgst": sgst,
                "igst": igst,
            } if is_resolved else None,
            "reference_id": ref_id,
            "reference_version": ref_ver,
            "effective_from": eff_from,
            "effective_to": eff_to,
            "resolution_status": res_status,
            "resolution_reason": res_reason,
            "transaction_date": str(target_date),
        }

        reference_status = "VALID_REFERENCE" if is_resolved else ("UNKNOWN_REFERENCE" if not is_conflict else "CONFLICTING_REFERENCE")
        evidence["reference_classification_status"] = reference_status

        trace = {
            "hsn_code": hsn_code,
            "resolution_status": res_status,
            "reference_classification_status": reference_status,
            "reference_id": ref_id,
            "reference_version": ref_ver,
            "transaction_date": str(target_date),
        }

        app_reason = "Invoice item classification code present and subject to statutory HSN/SAC master lookup."

        is_b2c = (invoice.invoice_type or "").upper() in ("B2C", "B2CL", "B2CS") or not (invoice.counterparty_gstin or invoice.gstin)
        turnover = getattr(invoice, "turnover", None)
        turnover_exceeds_5cr = turnover is not None and turnover > Decimal("50000000")

        if not hsn_code:
            if is_b2c and not turnover_exceeds_5cr:
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.PASS,
                    severity=Severity.INFO,
                    category=self.category,
                    message="HSN/SAC code is optional for B2C supplies where annual turnover is up to INR 5 Crore (Notification No. 78/2020-Central Tax).",
                    actual_value="OPTIONAL",
                    expected_value="OPTIONAL (B2C <= 5 Cr)",
                    observed_value=None,
                    applicability="OPTIONAL",
                    applicability_reason="Notification No. 78/2020: HSN is optional on B2C tax invoices for turnover up to INR 5 Crore.",
                    evidence=evidence,
                    rule_version=self.version,
                )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message="HSN/SAC code missing from invoice line item.",
                actual_value=None,
                expected_value="Valid 4 to 8 digit HSN/SAC code",
                observed_value=None,
                applicability="REVIEW",
                applicability_reason="HSN/SAC code missing from invoice line item.",
                evidence=evidence,
                rule_version=self.version,
            )

        if is_conflict:
            if context and context.current_snapshot:
                context.current_snapshot.record_unresolved(
                    "hsn",
                    str(hsn_code),
                    res_status,
                    res_reason or "HSN resolution conflict",
                )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message=f"HSN resolution conflict: multiple active versions found for HSN code '{hsn_code}' on {target_date} - authoritative version unknown.",
                actual_value=hsn_code,
                expected_value="Single unique active HSN version in Master",
                observed_value=hsn_code,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=ref_id,
                reference_version=ref_ver,
                calculation_trace=trace,
                financial_exposure_type="Undetermined",
                evidence=evidence,
                rule_version=self.version,
            )

        if not is_resolved:
            if context and context.current_snapshot:
                context.current_snapshot.record_unresolved(
                    "hsn",
                    str(hsn_code),
                    res_status,
                    res_reason or "HSN not found in master",
                )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message=f"HSN code {hsn_code} was not found in the HSN/SAC master on {target_date}.",
                actual_value=hsn_code,
                expected_value="Valid HSN code in Master",
                observed_value=hsn_code,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=ref_id,
                reference_version=ref_ver,
                calculation_trace=trace,
                financial_exposure_type="Undetermined",
                evidence=evidence,
                rule_version=self.version,
            )

        # Check statutory digit requirements (Notification No. 78/2020-Central Tax)
        clean_digits = "".join([c for c in str(hsn_code) if c.isdigit()])
        if turnover_exceeds_5cr and 0 < len(clean_digits) < 6:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message=f"Taxpayer turnover exceeds INR 5 Crore: minimum 6-digit HSN code mandatory (Notification No. 78/2020-Central Tax). Found {len(clean_digits)} digits for '{hsn_code}'.",
                actual_value=hsn_code,
                expected_value="Minimum 6-digit HSN code",
                observed_value=hsn_code,
                applicability="APPLICABLE",
                applicability_reason="Turnover > INR 5 Crore requires minimum 6 digits.",
                evidence=evidence,
                rule_version=self.version,
            )

        if not turnover_exceeds_5cr and not is_b2c and 0 < len(clean_digits) < 4:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NEEDS_REVIEW,
                severity=self.severity,
                category=self.category,
                message=f"B2B invoices require a minimum 4-digit HSN code for turnover up to INR 5 Crore (Notification No. 78/2020-Central Tax). Found {len(clean_digits)} digits for '{hsn_code}'.",
                actual_value=hsn_code,
                expected_value="Minimum 4-digit HSN code",
                observed_value=hsn_code,
                applicability="APPLICABLE",
                applicability_reason="B2B turnover <= INR 5 Crore requires minimum 4 digits.",
                evidence=evidence,
                rule_version=self.version,
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS,
            severity=Severity.INFO,
            category=self.category,
            message=f"HSN code {hsn_code} ({desc}) is a recognized classification.",
            actual_value=hsn_code,
            expected_value=desc,
            observed_value=hsn_code,
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            reference_id=ref_id,
            reference_version=ref_ver,
            calculation_trace=trace,
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
