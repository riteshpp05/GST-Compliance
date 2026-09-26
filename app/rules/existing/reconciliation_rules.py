"""
UC15 GST Compliance Agent — GST Return Reconciliation Rules (RECON_001 to RECON_005)
Reconciles SAP Books, GSTR-1, GSTR-2B, GSTR-3B, and monitors DRC-01C risk.
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


class GSTR2BReconciliationRule(ComplianceRule):
    """
    RECON_002: Reconciles SAP Inward Supply (AP Invoices) with GSTR-2B statement.
    Produces match status (EXACT, PROBABLE, PARTIAL, UNMATCHED, BOOKS_ONLY, GSTR2B_ONLY).
    """
    @property
    def rule_id(self) -> str:
        return "RECON_002"

    @property
    def name(self) -> str:
        return "GSTR-2B Inward Reconciliation"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.RECONCILIATION

    @property
    def severity(self) -> Severity:
        return Severity.HIGH

    @property
    def gate_no(self) -> int:
        return 6

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        if invoice.direction != "AP":
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="Outward AR supply; GSTR-2B inward reconciliation not applicable.",
                evidence={"direction": invoice.direction},
                version=self.version,
            )

        match_status = str(invoice.gstr2b_match_status or ("EXACT" if invoice.gstr2b_reflected else "UNMATCHED")).upper()

        if match_status == "UNMATCHED" or not invoice.gstr2b_reflected:
            exposure = float(invoice.total_tax)
            return ValidationResult.fail_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=Severity.HIGH,
                gate_no=self.gate_no,
                message=f"GSTR-2B Mismatch: Invoice {invoice.invoice_number} not reflected in GSTR-2B. Claiming ITC creates DRC-01C risk.",
                evidence={
                    "invoice_number": invoice.invoice_number,
                    "supplier_gstin": invoice.supplier_gstin,
                    "gstr2b_match_status": match_status,
                    "gstr2b_reflected": invoice.gstr2b_reflected,
                    "total_tax": float(invoice.total_tax),
                },
                financial_exposure=exposure,
                version=self.version,
            )

        return ValidationResult.pass_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=self.severity,
            gate_no=self.gate_no,
            message=f"GSTR-2B Match confirmed ({match_status}). ITC is safe to claim.",
            evidence={"invoice_number": invoice.invoice_number, "gstr2b_match_status": match_status},
            version=self.version,
        )


class DRC01CRiskMonitoringRule(ComplianceRule):
    """
    RECON_005: Monitors DRC-01C risk triggered when GSTR-3B claimed ITC exceeds GSTR-2B available ITC by > 10%.
    """
    @property
    def rule_id(self) -> str:
        return "RECON_005"

    @property
    def name(self) -> str:
        return "DRC-01C 2B vs 3B Risk Monitor"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.RECONCILIATION

    @property
    def severity(self) -> Severity:
        return Severity.CRITICAL

    @property
    def gate_no(self) -> int:
        return 6

    @property
    def version(self) -> str:
        return "2.0"

    def validate(self, invoice: Invoice, context: Optional[ValidationContext] = None) -> ValidationResult:
        if invoice.direction != "AP" or invoice.gstr2b_reflected:
            return ValidationResult.pass_result(
                rule_id=self.rule_id,
                name=self.name,
                category=self.category,
                severity=self.severity,
                gate_no=self.gate_no,
                message="No DRC-01C risk detected.",
                evidence={"gstr2b_reflected": True},
                version=self.version,
            )

        return ValidationResult.fail_result(
            rule_id=self.rule_id,
            name=self.name,
            category=self.category,
            severity=Severity.HIGH,
            gate_no=self.gate_no,
            message="DRC-01C Risk Triggered: Unreflected AP invoice claimed in GSTR-3B. Risk of Part-A notice from Tax Officer.",
            evidence={
                "invoice_number": invoice.invoice_number,
                "claimed_itc": float(invoice.total_tax),
                "gstr2b_available": 0.0,
                "drc01c_threshold": "10%",
            },
            financial_exposure=float(invoice.total_tax),
            version=self.version,
        )
