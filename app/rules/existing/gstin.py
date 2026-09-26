"""
UC15 GST Compliance Agent — Gate 1: GSTIN Format & Checksum Validity Rule (v2.0)
Implements structural pattern verification and Indian GSTIN Luhn Modulo-36 Checksum algorithm.
"""
from __future__ import annotations

import re
from typing import Optional

from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.domain.enums.validation_status import ValidationStatus
from app.domain.models.invoice import Invoice
from app.domain.models.validation import ValidationResult
from app.rules.base import ComplianceRule
from app.rules.context import ValidationContext

GSTIN_PATTERN = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def calculate_gstin_checksum(gstin14: str) -> Optional[str]:
    """
    Calculate 15th checksum character using Indian GSTN Luhn Modulo-36 algorithm.
    Algorithm:
      Weights alternate [1, 2, 1, 2, ...] across the first 14 characters.
      Sum digits of (val * factor // 36) + (val * factor % 36).
      Check code = (36 - (total % 36)) % 36.
    """
    gstin14 = gstin14.strip().upper()
    if len(gstin14) != 14:
        return None

    factor = 1
    total = 0
    for char in gstin14:
        if char not in GSTIN_CHARS:
            return None
        val = GSTIN_CHARS.index(char) * factor
        val = (val // 36) + (val % 36)
        total += val
        factor = 2 if factor == 1 else 1

    rem = total % 36
    check_code = (36 - rem) % 36
    return GSTIN_CHARS[check_code]


def verify_gstin_checksum(gstin: str) -> bool:
    """Verify whether a 15-character GSTIN has a valid Modulo-36 checksum."""
    gstin = gstin.strip().upper()
    if len(gstin) != 15:
        return False
    expected = calculate_gstin_checksum(gstin[:14])
    return expected is not None and gstin[14] == expected


class GSTINFormatRule(ComplianceRule):
    """
    Gate 1: Verifies counterparty GSTIN format and checksum.
    - Pattern check: 2 state digits + 10 PAN characters + 1 entity code + 'Z' + 1 checksum character.
    - Modulo-36 Checksum verification (distinguishes FORMAT_INVALID, CHECKSUM_INVALID, VALID).
    Failure on format is a fatal hard override blocking filing.
    """

    @property
    def rule_id(self) -> str:
        return "GSTIN_001"

    @property
    def name(self) -> str:
        return "GSTIN Format Validity"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.MASTER_DATA

    @property
    def severity(self) -> Severity:
        return Severity.CRITICAL

    @property
    def gate_no(self) -> int:
        return 1

    @property
    def version(self) -> str:
        return "2.0"

    def validate(
        self,
        invoice: Invoice,
        context: Optional[ValidationContext] = None,
    ) -> ValidationResult:
        from app.domain.models.transaction_context import TransactionContext, TransactionScope
        txn_ctx = getattr(context, "transaction_context", None) or TransactionContext.from_invoice(invoice)

        gstin = (invoice.counterparty_gstin or invoice.gstin or "").strip()
        inv_type = (invoice.invoice_type or "").upper()

        # Applicability Check: Foreign / Export / Import / Unregistered counterparty / B2C
        is_b2c = inv_type in ("B2C", "B2CL", "B2CS")
        is_foreign_or_urp = (
            not gstin
            or gstin.upper() in ("URP", "OVERSEAS", "FOREIGN", "EXPORT", "N/A", "NONE")
            or txn_ctx.scope in (TransactionScope.IMPORT, TransactionScope.EXPORT)
            or txn_ctx.is_foreign_counterparty
            or inv_type in ("EXPORT", "IMPORT")
            or is_b2c
        )

        if is_foreign_or_urp and (not gstin or gstin.upper() in ("URP", "OVERSEAS", "FOREIGN", "N/A", "NONE")):
            if is_b2c:
                reason = "B2C consumer supply does not require recipient GSTIN (statutorily valid for unregistered persons)."
            else:
                reason = f"Transaction scope '{txn_ctx.scope.value}' / foreign counterparty does not require domestic GSTIN registration."
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NOT_APPLICABLE,
                severity=Severity.INFO,
                category=self.category,
                message=f"GSTIN validation: {reason}",
                actual_value=gstin or "N/A (B2C / URP)",
                expected_value="NOT_APPLICABLE for consumer / foreign / unregistered supplies",
                observed_value=gstin or "N/A",
                applicability="NOT_APPLICABLE",
                applicability_reason=reason,
                evidence={"gstin": gstin, "transaction_scope": txn_ctx.scope.value},
                rule_version=self.version,
            )

        format_valid = bool(GSTIN_PATTERN.match(gstin))

        # Checksum calculation
        expected_checksum = calculate_gstin_checksum(gstin[:14]) if len(gstin) >= 14 else None
        actual_checksum = gstin[14] if len(gstin) == 15 else None
        checksum_valid = expected_checksum is not None and actual_checksum == expected_checksum

        validate_checksum_strictly = bool(context and context.validate_gstin_checksum)

        evidence = {
            "gstin": gstin,
            "format_valid": format_valid,
            "checksum_valid": checksum_valid,
            "expected_checksum": expected_checksum,
            "actual_checksum": actual_checksum,
            "state_code": gstin[:2] if len(gstin) >= 2 else None,
            "pan": gstin[2:12] if len(gstin) >= 12 else None,
            "strict_mode": validate_checksum_strictly,
        }

        app_reason = "Domestic registered counterparty subject to statutory GSTIN format and checksum verification."

        if not format_valid:
            format_status = "GSTIN_STRUCTURALLY_INVALID"
            evidence["format_classification_status"] = format_status
            trace = {
                "gstin": gstin,
                "format_valid": False,
                "format_classification_status": format_status,
            }
            detail = f"GSTIN {gstin} does not match the standard 15-character GSTIN format."
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=detail,
                actual_value=gstin,
                expected_value="15-character GSTIN (State+PAN+Entity+Z+Checksum)",
                observed_value=gstin,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                calculation_trace=trace,
                financial_exposure_type="Undetermined",
                evidence=evidence,
                rule_version=self.version,
            )

        if validate_checksum_strictly and not checksum_valid:
            format_status = "GSTIN_CHECKSUM_INVALID"
            evidence["format_classification_status"] = format_status
            trace = {
                "gstin": gstin,
                "format_valid": True,
                "checksum_valid": False,
                "expected_checksum": expected_checksum,
                "actual_checksum": actual_checksum,
                "format_classification_status": format_status,
            }
            detail = (
                f"GSTIN {gstin} matches 15-character format but has an invalid Modulo-36 checksum "
                f"(expected '{expected_checksum}', found '{actual_checksum}')."
            )
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=Severity.HIGH,
                category=self.category,
                message=detail,
                actual_value=actual_checksum,
                expected_value=expected_checksum,
                observed_value=actual_checksum,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                calculation_trace=trace,
                financial_exposure_type="Undetermined",
                evidence=evidence,
                rule_version=self.version,
            )

        # Valid format (and checksum if strict or matching)
        format_status = "GSTIN_FORMAT_VALID"
        evidence["format_classification_status"] = format_status
        trace = {
            "gstin": gstin,
            "format_valid": True,
            "checksum_valid": checksum_valid,
            "format_classification_status": format_status,
        }
        detail = f"GSTIN {gstin} matches the standard 15-character format."
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS,
            severity=Severity.INFO,
            category=self.category,
            message=detail,
            actual_value=gstin,
            expected_value="15-character valid GSTIN",
            observed_value=gstin,
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            calculation_trace=trace,
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
