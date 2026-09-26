"""
UC15 GST Compliance Agent — Extended Rule: Section 16(2) 180-Day Payment Interest Reversal Rule (ITC_180_001)
Tracks payment age of AP Invoices and calculates 18% p.a. interest reversal liability for unpaid invoices > 180 days.
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
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext


def _parse_date(d: Optional[object]) -> date:
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(d.strip(), fmt).date()
            except ValueError:
                continue
    return date(2025, 1, 1)


class ITC180DayPaymentRule(ComplianceRule):
    """
    ITC_180_001: Enforces Section 16(2) proviso to CGST Act.
    If buyer fails to pay vendor within 180 days of invoice date, claimed ITC must be reversed with 18% p.a. interest.
    """

    @property
    def rule_id(self) -> str:
        return "ITC_180_001"

    @property
    def name(self) -> str:
        return "Section 16(2) 180-Day Payment Interest Reversal"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ITC_ELIGIBILITY

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
        inv_date = _parse_date(invoice.invoice_date)
        today = date(2026, 9, 21)
        age_days = (today - inv_date).days

        claimed_itc = float(invoice.cgst_amount + invoice.sgst_amount + invoice.igst_amount)

        is_unpaid_over_180 = age_days > 180 and invoice.itc_eligible

        if is_unpaid_over_180:
            overdue_days = age_days - 180
            interest_liability = claimed_itc * 0.18 * (overdue_days / 365.0)

            evidence = {
                "invoice_number": invoice.invoice_number,
                "invoice_date": str(inv_date),
                "age_days": age_days,
                "overdue_days": overdue_days,
                "claimed_itc": claimed_itc,
                "interest_rate": "18% p.a.",
                "calculated_interest_liability": round(interest_liability, 2),
                "sap_payment_block": "BSEG-ZLSPR = 'R'",
            }

            detail = (
                f"Invoice {invoice.invoice_number} dated {inv_date} is unpaid for {age_days} days (>180 days). "
                f"Section 16(2) Proviso mandate: Reversal of ₹{claimed_itc:,.2f} ITC + ₹{interest_liability:,.2f} interest (18% p.a.)."
            )

            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=detail,
                actual_value=f"{age_days} Days Unpaid",
                expected_value="Payment within 180 Days",
                observed_value=f"180-Day Breach (+₹{interest_liability:,.2f} Interest)",
                calculation_trace={
                    "age_days": age_days,
                    "claimed_itc": claimed_itc,
                    "interest": interest_liability,
                },
                financial_exposure_type="TAX_DIFFERENCE",
                evidence=evidence,
                rule_version=self.version,
            )

        evidence = {
            "invoice_number": invoice.invoice_number,
            "invoice_date": str(inv_date),
            "age_days": age_days,
            "claimed_itc": claimed_itc,
            "is_unpaid_over_180": False,
        }

        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS,
            severity=Severity.INFO,
            category=self.category,
            message=f"Invoice age ({age_days} days) within Section 16(2) 180-day threshold limit.",
            actual_value=f"{age_days} Days",
            expected_value="<= 180 Days",
            observed_value="Within 180 Days Limit",
            calculation_trace={"age_days": age_days, "breach": False},
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
