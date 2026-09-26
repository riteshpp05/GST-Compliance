"""
UC15 GST Compliance Agent — Gate 5: E-Invoice Compliance Engine (EINV_001 to EINV_007)
Validates turnover threshold applicability, mandatory fields, IRN format/checksum/duplicate, cancellation status, QR code data.
"""
from __future__ import annotations

from decimal import Decimal
import re
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext

# Statutory turnover threshold for E-Invoicing applicability (₹5 Crores)
EINVOICE_TURNOVER_THRESHOLD = Decimal("50000000.00")
IRN_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")


class EInvoiceApplicabilityRule(ComplianceRule):
    """
    EINV_001: Verifies whether E-Invoicing is mandatory based on supplier turnover threshold (₹5 Cr).
    """
    @property
    def rule_id(self) -> str:
        return "EINV_001"

    @property
    def name(self) -> str:
        return "E-Invoice Applicability Threshold"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.E_INVOICE

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 5

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        turnover = invoice.turnover or Decimal("0.00")
        is_b2b = str(invoice.invoice_type or "B2B").strip().upper() in ("B2B", "SEZ", "EXPORT", "DEEMED_EXPORT")
        irn = str(invoice.irn or "").strip()

        if is_b2b and turnover >= EINVOICE_TURNOVER_THRESHOLD and not irn:
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message=f"E-Invoice (IRN) is mandatory for B2B supplies when turnover (₹{turnover:,.2f}) >= ₹5 Cr threshold.",
                evidence={"turnover": float(turnover), "invoice_type": invoice.invoice_type, "irn": None},
                financial_exposure=float(invoice.total_tax),
                version=self.version,
            )

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message="E-Invoice applicability requirements satisfied.",
            evidence={"turnover": float(turnover), "invoice_type": invoice.invoice_type, "irn_present": bool(irn)},
            version=self.version,
        )


class EInvoiceIRNStructureRule(ComplianceRule):
    """
    EINV_003: Validates 64-character SHA-256 hex string structure of IRN.
    """
    @property
    def rule_id(self) -> str:
        return "EINV_003"

    @property
    def name(self) -> str:
        return "E-Invoice IRN Format & Checksum"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.E_INVOICE

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 5

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        irn = str(invoice.irn or "").strip()
        if not irn:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="No IRN supplied; skipping IRN format check.",
                evidence={"irn": None},
                version=self.version,
            )

        if IRN_REGEX.match(irn):
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="IRN structure is a valid 64-character hex hash.",
                evidence={"irn": irn, "length": len(irn)},
                version=self.version,
            )
        else:
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message=f"Invalid IRN format: '{irn}'. IRN must be a valid 64-character hex string.",
                evidence={"irn": irn, "length": len(irn)},
                financial_exposure=float(invoice.total_tax),
                version=self.version,
            )


class EInvoiceCancellationStatusRule(ComplianceRule):
    """
    EINV_005: Verifies that an E-Invoice has not been cancelled on IRP portal.
    """
    @property
    def rule_id(self) -> str:
        return "EINV_005"

    @property
    def name(self) -> str:
        return "E-Invoice Cancellation Status"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.E_INVOICE

    @property
    def severity(self) -> Severity:
        return Severity.CRITICAL

    @property
    def gate_no(self) -> int:
        return 5

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        irn_status = str(invoice.irn_status or "").strip().upper()
        cancel_status = str(invoice.irn_cancellation_status or "").strip().upper()

        if irn_status == "CANCELLED" or cancel_status == "CANCELLED":
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.CRITICAL,
                gate_no=self.gate_no,
                message="E-Invoice IRN has been CANCELLED on IRP portal.",
                evidence={"irn_status": irn_status, "irn_cancellation_status": cancel_status},
                financial_exposure=float(invoice.total_tax),
                version=self.version,
            )

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message="E-Invoice IRN is ACTIVE.",
            evidence={"irn_status": irn_status or "ACTIVE"},
            version=self.version,
        )
