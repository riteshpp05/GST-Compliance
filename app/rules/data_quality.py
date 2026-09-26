"""
UC15 GST Compliance Agent — Data Quality Rules Layer
Provides foundational data-hygiene validation (DATA_001 through DATA_005) before statutory checks.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext


class MandatoryInvoiceIdRule(ComplianceRule):
    """DATA_001: Verifies mandatory invoice number is present and non-empty."""

    @property
    def rule_id(self) -> str:
        return "DATA_001"

    @property
    def name(self) -> str:
        return "Mandatory Invoice Identifier"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        inv_no = invoice.invoice_number.strip() if invoice.invoice_number else ""
        passed = bool(inv_no)
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            severity=self.severity,
            category=self.category,
            message="Invoice identifier is present." if passed else "Missing mandatory invoice identifier.",
            actual_value=inv_no,
            expected_value="Non-empty invoice identifier",
            evidence={"invoice_number": inv_no, "valid": passed},
        )


class ValidInvoiceDateRule(ComplianceRule):
    """DATA_002: Verifies invoice date format is valid and within standard range."""

    @property
    def rule_id(self) -> str:
        return "DATA_002"

    @property
    def name(self) -> str:
        return "Valid Invoice Date"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        d_str = str(invoice.invoice_date).strip()
        passed = False
        try:
            parsed = datetime.datetime.strptime(d_str, "%Y-%m-%d").date()
            # Invoice date should not be more than 10 years in the past or 1 year in the future
            today = datetime.date.today()
            passed = (today.year - 10) <= parsed.year <= (today.year + 1)
        except ValueError:
            passed = False

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            severity=self.severity,
            category=self.category,
            message=f"Invoice date '{d_str}' is valid." if passed else f"Invoice date '{d_str}' is invalid or out of realistic bounds.",
            actual_value=d_str,
            expected_value="ISO Date (YYYY-MM-DD) within realistic timeline",
            evidence={"raw_date": d_str, "valid_format": passed},
        )


class NonNegativeTaxableValueRule(ComplianceRule):
    """DATA_003: Verifies taxable value is non-negative and mathematically sound."""

    @property
    def rule_id(self) -> str:
        return "DATA_003"

    @property
    def name(self) -> str:
        return "Valid Taxable Value"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        passed = invoice.taxable_value >= Decimal("0.00")
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            severity=self.severity,
            category=self.category,
            message=f"Taxable value ₹{invoice.taxable_value:,.2f} is non-negative." if passed else f"Negative taxable value ₹{invoice.taxable_value:,.2f} found.",
            actual_value=str(invoice.taxable_value),
            expected_value=">= 0.00",
            evidence={"taxable_value": str(invoice.taxable_value), "is_positive": passed},
        )


class NumericTaxRateRule(ComplianceRule):
    """DATA_004: Verifies tax rates are valid percentages (0% to 50%)."""

    @property
    def rule_id(self) -> str:
        return "DATA_004"

    @property
    def name(self) -> str:
        return "Numeric Tax Rates Validity"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        rates = [invoice.cgst_rate, invoice.sgst_rate, invoice.igst_rate]
        valid = all(Decimal("0.00") <= r <= Decimal("50.00") for r in rates)
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=ValidationStatus.PASS if valid else ValidationStatus.FAIL,
            severity=self.severity,
            category=self.category,
            message="Tax rates are within valid GST percentage bounds." if valid else "One or more tax rates are negative or exceed 50%.",
            actual_value={"cgst": str(invoice.cgst_rate), "sgst": str(invoice.sgst_rate), "igst": str(invoice.igst_rate)},
            expected_value="Between 0% and 50%",
            evidence={"cgst_rate": str(invoice.cgst_rate), "sgst_rate": str(invoice.sgst_rate), "igst_rate": str(invoice.igst_rate)},
        )


class CounterpartyInfoRule(ComplianceRule):
    """DATA_005: Verifies counterparty name and place of supply are present."""

    @property
    def rule_id(self) -> str:
        return "DATA_005"

    @property
    def name(self) -> str:
        return "Required Counterparty Information"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DATA_QUALITY

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        has_name = bool(invoice.counterparty_name and invoice.counterparty_name.strip())
        has_pos = bool(invoice.place_of_supply and invoice.place_of_supply.strip())
        passed = has_name and has_pos
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            status=ValidationStatus.PASS if passed else ValidationStatus.WARNING,
            severity=self.severity,
            category=self.category,
            message="Counterparty name and Place of Supply are present." if passed else "Missing counterparty name or Place of Supply.",
            actual_value={"counterparty": invoice.counterparty_name, "pos": invoice.place_of_supply},
            expected_value="Both counterparty name and Place of Supply must be populated",
            evidence={"has_name": has_name, "has_pos": has_pos},
        )
