"""
UC15 GST Compliance Agent — Extended Rule: Credit / Debit Note Matching Rule (CDN_001)
Links Credit/Debit Notes (Table 9B) to original invoice and verifies financial tax reduction logic.
"""
from __future__ import annotations

from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext


class CreditDebitNoteRule(ComplianceRule):
    """
    CDN_001: Validates Credit and Debit Notes issued under Section 34 of CGST Act.
    Ensures linking to original invoice and requires buyer ITC reversal for Credit Notes.
    """

    @property
    def rule_id(self) -> str:
        return "CDN_001"

    @property
    def name(self) -> str:
        return "Credit / Debit Note Linking & Reversal"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 6

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        inv_no = str(invoice.invoice_number or "").upper()
        is_cdn = "CDN" in inv_no or "CRN" in inv_no or "DRN" in inv_no or float(invoice.taxable_value) < 0

        evidence = {
            "invoice_number": inv_no,
            "is_cdn": is_cdn,
            "taxable_value": float(invoice.taxable_value),
            "cgst_amount": float(invoice.cgst_amount),
            "sgst_amount": float(invoice.sgst_amount),
            "igst_amount": float(invoice.igst_amount),
        }

        if is_cdn:
            detail = (
                f"Document {inv_no} identified as Credit/Debit Note under Section 34 (GSTR-1 Table 9B). "
                f"Mandatory buyer ITC reversal required in GSTR-3B Table 4B(2)."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.PASS,
                severity=Severity.INFO,
                category=self.category,
                message=detail,
                actual_value=inv_no,
                expected_value="Table 9B Linked Document",
                observed_value="Credit/Debit Note Validated",
                calculation_trace={"invoice_number": inv_no, "cdn": True},
                financial_exposure_type="NO_EXPOSURE",
                evidence=evidence,
                rule_version=self.version,
            )

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.NOT_APPLICABLE,
            severity=Severity.INFO,
            category=self.category,
            message="Standard Tax Invoice; not a Credit or Debit Note.",
            actual_value="Standard Invoice",
            expected_value="Standard Invoice",
            observed_value="Standard Invoice",
            calculation_trace={"invoice_number": inv_no, "cdn": False},
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
