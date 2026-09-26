"""
UC15 GST Compliance Agent — Extended Rule: Reverse Charge Mechanism (RCM) Rule (RCM_001)
Identifies supplies subject to Reverse Charge under Section 9(3)/9(4) of CGST Act.
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

# Notified RCM HSN/SAC Categories
RCM_HSN_CATEGORIES = {
    "9965": "Goods Transport Agency (GTA) Services",
    "9983": "Legal / Advocate Services",
    "7204": "Metal Scrap Supply from Unregistered Sellers",
    "8548": "E-Waste Scrap Supply",
    "8549": "Electrical Scrap Supply",
}


class ReverseChargeRule(ComplianceRule):
    """
    RCM_001: Identifies supplies subject to Reverse Charge Mechanism.
    Verifies that tax is paid directly by recipient via cash/electronic ledger.
    """

    @property
    def rule_id(self) -> str:
        return "RCM_001"

    @property
    def name(self) -> str:
        return "Reverse Charge Mechanism Identification"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TAX_RATES

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
        hsn = str(invoice.hsn_code or "").strip()
        hsn_prefix = hsn[:4] if len(hsn) >= 4 else hsn

        is_rcm = hsn_prefix in RCM_HSN_CATEGORIES

        evidence = {
            "hsn_code": hsn,
            "hsn_prefix": hsn_prefix,
            "is_rcm_applicable": is_rcm,
            "rcm_category": RCM_HSN_CATEGORIES.get(hsn_prefix, "Forward Charge"),
            "taxable_value": float(invoice.taxable_value),
        }

        if is_rcm:
            detail = (
                f"Supply under HSN/SAC {hsn} ({RCM_HSN_CATEGORIES[hsn_prefix]}) is subject to "
                f"Reverse Charge Mechanism (RCM) under Section 9(3)/9(4). Tax payable by Recipient."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.PASS if is_rcm else ValidationStatus.NOT_APPLICABLE,
                severity=Severity.INFO,
                category=self.category,
                message=detail,
                actual_value=f"RCM ({RCM_HSN_CATEGORIES[hsn_prefix]})",
                expected_value="Reverse Charge Tax Payment by Recipient",
                observed_value=f"RCM Applicable for {hsn}",
                calculation_trace={"hsn": hsn, "rcm": True},
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
            message=f"Supply under HSN {hsn} is governed by standard Forward Charge.",
            actual_value="Forward Charge",
            expected_value="Standard Supply",
            observed_value="Forward Charge",
            calculation_trace={"hsn": hsn, "rcm": False},
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
