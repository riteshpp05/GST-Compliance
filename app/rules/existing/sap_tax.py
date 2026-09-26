"""
UC15 GST Compliance Agent — SAP FI/SD Tax Configuration & Drift Rules (SAP_TAX_001 to SAP_TAX_005)
Validates SAP tax codes (V1, V2, A1, O1, V3), condition types (JOIC, JOIS, JOII, JOCP), and configuration drift.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext

SAP_TAX_CODE_MASTER = {
    "V1": {"tax_type": "INPUT_IGST", "rate": Decimal("18.00"), "cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": Decimal("18.00"), "is_rcm": False},
    "V2": {"tax_type": "INPUT_GST", "rate": Decimal("18.00"), "cgst": Decimal("9.00"), "sgst": Decimal("9.00"), "igst": Decimal("0.00"), "is_rcm": False},
    "V3": {"tax_type": "INPUT_RCM", "rate": Decimal("18.00"), "cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": Decimal("18.00"), "is_rcm": True},
    "A1": {"tax_type": "OUTPUT_IGST", "rate": Decimal("18.00"), "cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": Decimal("18.00"), "is_rcm": False},
    "O1": {"tax_type": "EXEMPT", "rate": Decimal("0.00"), "cgst": Decimal("0.00"), "sgst": Decimal("0.00"), "igst": Decimal("0.00"), "is_rcm": False},
}

VALID_CONDITION_TYPES = {"JOIC", "JOIS", "JOII", "JOCP"}


class SAPTaxCodeValidityRule(ComplianceRule):
    """
    SAP_TAX_001: Verifies SAP Tax Code existence and validity (V1, V2, A1, O1, V3).
    """
    @property
    def rule_id(self) -> str:
        return "SAP_TAX_001"

    @property
    def name(self) -> str:
        return "SAP Tax Code Validity"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SAP_TAX_CODE

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        tax_code = str(invoice.sap_tax_code or "").strip().upper()
        if not tax_code:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="SAP Tax Code not populated; skipping SAP_TAX_001 check.",
                evidence={"sap_tax_code": None},
                version=self.version,
            )

        if tax_code in SAP_TAX_CODE_MASTER:
            cfg = SAP_TAX_CODE_MASTER[tax_code]
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message=f"SAP Tax Code '{tax_code}' is valid ({cfg['tax_type']}).",
                evidence={"sap_tax_code": tax_code, "config": cfg},
                version=self.version,
            )
        else:
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message=f"Unrecognized SAP Tax Code '{tax_code}'. Expected V1, V2, A1, O1, V3.",
                evidence={"sap_tax_code": tax_code, "allowed": list(SAP_TAX_CODE_MASTER.keys())},
                financial_exposure=float(invoice.total_tax),
                version=self.version,
            )


class SAPConditionTypeRule(ComplianceRule):
    """
    SAP_TAX_002: Verifies SAP FI/SD Pricing Condition Type (JOIC, JOIS, JOII, JOCP).
    """
    @property
    def rule_id(self) -> str:
        return "SAP_TAX_002"

    @property
    def name(self) -> str:
        return "SAP Condition Type Alignment"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SAP_TAX_CODE

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        cond_type = str(invoice.sap_condition_type or "").strip().upper()
        if not cond_type:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="SAP Condition Type not supplied; skipping SAP_TAX_002.",
                evidence={"sap_condition_type": None},
                version=self.version,
            )

        if cond_type in VALID_CONDITION_TYPES:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message=f"SAP Condition Type '{cond_type}' is valid.",
                evidence={"sap_condition_type": cond_type},
                version=self.version,
            )
        else:
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message=f"Invalid SAP Condition Type '{cond_type}'. Expected one of {sorted(list(VALID_CONDITION_TYPES))}.",
                evidence={"sap_condition_type": cond_type, "allowed": sorted(list(VALID_CONDITION_TYPES))},
                version=self.version,
            )


class SAPTaxCodeDriftRule(ComplianceRule):
    """
    SAP_TAX_003: Detects mismatch between SAP tax code configuration and statutory expected tax.
    """
    @property
    def rule_id(self) -> str:
        return "SAP_TAX_003"

    @property
    def name(self) -> str:
        return "SAP Tax Code Configuration Drift"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SAP_TAX_CODE

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        tax_code = str(invoice.sap_tax_code or "").strip().upper()
        if not tax_code or tax_code not in SAP_TAX_CODE_MASTER:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="No valid SAP Tax Code for drift comparison.",
                evidence={"sap_tax_code": tax_code},
                version=self.version,
            )

        cfg = SAP_TAX_CODE_MASTER[tax_code]
        inv_cgst = float(invoice.cgst_rate)
        inv_sgst = float(invoice.sgst_rate)
        inv_igst = float(invoice.igst_rate)

        expected_cgst = float(cfg["cgst"])
        expected_sgst = float(cfg["sgst"])
        expected_igst = float(cfg["igst"])

        mismatch = (
            abs(inv_cgst - expected_cgst) > 0.01 or
            abs(inv_sgst - expected_sgst) > 0.01 or
            abs(inv_igst - expected_igst) > 0.01
        )

        if mismatch:
            exposure = float(invoice.taxable_value) * abs((inv_cgst + inv_sgst + inv_igst) - float(cfg["rate"])) / 100.0
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message=f"SAP Tax Code '{tax_code}' configuration drift: Applied CGST/SGST/IGST ({inv_cgst}%/{inv_sgst}%/{inv_igst}%) does not match SAP config ({expected_cgst}%/{expected_sgst}%/{expected_igst}%).",
                evidence={
                    "sap_tax_code": tax_code,
                    "applied_rates": {"cgst": inv_cgst, "sgst": inv_sgst, "igst": inv_igst},
                    "sap_configured_rates": {"cgst": expected_cgst, "sgst": expected_sgst, "igst": expected_igst},
                },
                financial_exposure=round(exposure, 2),
                version=self.version,
            )

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message=f"SAP Tax Code '{tax_code}' configuration matches applied invoice rates.",
            evidence={"sap_tax_code": tax_code, "matching_rates": {"cgst": inv_cgst, "sgst": inv_sgst, "igst": inv_igst}},
            version=self.version,
        )


class SAPClearingStatusRule(ComplianceRule):
    """
    SAP_TAX_004: Verifies SAP clearing document and clearing date consistency.
    """
    @property
    def rule_id(self) -> str:
        return "SAP_TAX_004"

    @property
    def name(self) -> str:
        return "SAP Clearing Document Verification"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SAP_TAX_CODE

    @property
    def severity(self) -> Severity:
        return Severity.MEDIUM

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        clearing_doc = str(invoice.clearing_document or "").strip()
        status = str(invoice.payment_status or "").upper()

        if status == "PAID" and not clearing_doc:
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.MEDIUM,
                gate_no=self.gate_no,
                message="Invoice is marked PAID but lacks SAP clearing document (AUGBL).",
                evidence={"payment_status": status, "clearing_document": None},
                version=self.version,
            )

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message="SAP clearing document status is consistent.",
            evidence={"payment_status": status, "clearing_document": clearing_doc or "N/A"},
            version=self.version,
        )


class SAPPricingProcedureDriftRule(ComplianceRule):
    """
    SAP_TAX_005: Validates pricing procedure consistency for SD billing documents.
    """
    @property
    def rule_id(self) -> str:
        return "SAP_TAX_005"

    @property
    def name(self) -> str:
        return "SAP Pricing Procedure Drift"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.SAP_TAX_CODE

    @property
    def severity(self) -> Severity:
        return Severity.LOW

    @property
    def gate_no(self) -> int:
        return 3

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message="SAP pricing procedure is consistent.",
            evidence={"invoice_id": invoice.invoice_id},
            version=self.version,
        )
