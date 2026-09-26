"""
UC15 GST Compliance Agent — Gate 6: ITC Eligibility / GSTR-2B Match Rule (Sprint 4)
Verifies Input Tax Credit eligibility, Section 17(5) blocked credit policies, and GSTR-2B reflection.
"""
from __future__ import annotations

from datetime import date, datetime
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


class ITCEligibilityRule(ComplianceRule):
    """
    Gate 6: Verifies Input Tax Credit (ITC) eligibility for inward supplies (AP).
    - Not applicable to AR (outward).
    - Checks Section 17(5) blocked credit categories via temporal policy references.
    - Checks counterparty filing reflection in GSTR-2B.
    """

    @property
    def rule_id(self) -> str:
        return "ITC_001"

    @property
    def name(self) -> str:
        return "ITC Eligibility / GSTR-2B Match"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ITC

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
        target_date = _extract_date(invoice.invoice_date)
        evidence = {
            "direction": invoice.direction,
            "item_desc": invoice.item_desc,
            "gstr2b_reflected": invoice.gstr2b_reflected,
            "blocked_match": None,
            "itc_claimable": False,
            "policy_id": None,
            "reference_version": None,
            "resolution_status": ResolutionStatus.NOT_FOUND.value,
            "transaction_date": str(target_date),
        }

        if invoice.direction != "AP":
            reason = "Input Tax Credit (ITC) eligibility applies exclusively to Inward Purchase (AP) transactions."
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.NOT_APPLICABLE,
                severity=Severity.INFO,
                category=self.category,
                message=f"Not applicable: {reason}",
                actual_value=invoice.direction,
                expected_value="AP",
                applicability="NOT_APPLICABLE",
                applicability_reason=reason,
                evidence=evidence,
                rule_version=self.version,
            )

        app_reason = "Inward Purchase (AP) transaction subject to Section 17(5) blocked credit rules and GSTR-2B reflection check."

        # 1. Check blocked keywords from context
        blocked_keywords = context.itc_blocked_keywords if context else []
        desc_lower = (invoice.item_desc or "").lower()
        blocked = next((kw for kw in blocked_keywords if kw in desc_lower), None)

        # 2. Check temporal ITC policy from reference service
        if context and context.reference_service:
            if not context.reference_service.repo.get_itc_policies():
                evidence["resolution_status"] = ResolutionStatus.NOT_FOUND.value
                if context.current_snapshot:
                    context.current_snapshot.record_unresolved(
                        "itc_policy",
                        invoice.item_desc or "EMPTY",
                        ResolutionStatus.NOT_FOUND.value,
                        "No ITC policies registered in reference catalog",
                    )
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.NEEDS_REVIEW,
                    severity=self.severity,
                    category=self.category,
                    message="Cannot verify ITC eligibility - ITC policy reference catalog is empty or missing.",
                    actual_value=invoice.item_desc,
                    expected_value="Active Section 17(5) policy reference",
                    applicability="REVIEW",
                    applicability_reason="ITC policy catalog empty or uninitialized.",
                    evidence=evidence,
                    rule_version=self.version,
                )

            res = context.reference_service.resolve_itc_policy(invoice.item_desc, target_date)
            evidence["resolution_status"] = res.status.value
            if res.status == ResolutionStatus.CONFLICT:
                if context.current_snapshot:
                    context.current_snapshot.record_unresolved(
                        "itc_policy",
                        invoice.item_desc or "EMPTY",
                        res.status.value,
                        res.reason or "ITC policy conflict",
                    )
                return ValidationResult(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    gate_no=self.gate_no,
                    status=ValidationStatus.NEEDS_REVIEW,
                    severity=self.severity,
                    category=self.category,
                    message=f"ITC policy conflict: multiple active Section 17(5) policies match item description on {target_date}.",
                    actual_value=invoice.item_desc,
                    expected_value="Single unique active policy",
                    applicability="REVIEW",
                    applicability_reason="ITC policy resolution conflict.",
                    evidence=evidence,
                    rule_version=self.version,
                )
            if res.is_resolved:
                pol = res.record
                evidence["policy_id"] = pol.policy_id
                evidence["reference_version"] = pol.version
                evidence["blocked_reason"] = pol.blocked_reason
                if pol.is_blocked_17_5 and not blocked:
                    # Find which keyword matched
                    for kw in pol.blocked_keywords:
                        if kw.lower() in desc_lower:
                            blocked = kw
                            break
                    if not blocked:
                        blocked = pol.category

                if context.current_snapshot:
                    context.current_snapshot.set_policy("itc_policy", pol)

        evidence["blocked_match"] = blocked

        trace = {
            "direction": invoice.direction,
            "item_desc": invoice.item_desc,
            "blocked_match": blocked,
            "gstr2b_reflected": invoice.gstr2b_reflected,
            "policy_id": evidence.get("policy_id"),
            "reference_version": evidence.get("reference_version"),
        }

        pol_id = evidence.get("policy_id")
        pol_ver = evidence.get("reference_version")

        if blocked:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message=f"Input tax credit flagged as potential blocked-ITC indicator requiring finance review (Section 17(5)) - matches category '{blocked}'.",
                actual_value=blocked,
                expected_value="Eligible credit category",
                observed_value=blocked,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=pol_id,
                reference_version=pol_ver,
                calculation_trace=trace,
                financial_exposure_type="ITC at Risk",
                evidence=evidence,
                rule_version=self.version,
            )

        if not invoice.gstr2b_reflected:
            return ValidationResult(
                rule_id=self.rule_id,
                rule_name=self.name,
                gate_no=self.gate_no,
                status=ValidationStatus.FAIL,
                severity=self.severity,
                category=self.category,
                message="This invoice is not reflected in GSTR-2B - ITC claim is at risk (Potential ITC reconciliation issue requiring finance review).",
                actual_value=invoice.gstr2b_reflected,
                expected_value=True,
                observed_value=invoice.gstr2b_reflected,
                applicability="APPLICABLE",
                applicability_reason=app_reason,
                reference_id=pol_id,
                reference_version=pol_ver,
                calculation_trace=trace,
                financial_exposure_type="ITC at Risk",
                evidence=evidence,
                rule_version=self.version,
            )

        evidence["itc_claimable"] = True
        return ValidationResult(
            rule_id=self.rule_id,
            rule_name=self.name,
            gate_no=self.gate_no,
            status=ValidationStatus.PASS,
            severity=Severity.INFO,
            category=self.category,
            message="Not a blocked category and reflected in GSTR-2B - ITC eligible.",
            actual_value=True,
            expected_value=True,
            observed_value=True,
            applicability="APPLICABLE",
            applicability_reason=app_reason,
            reference_id=pol_id,
            reference_version=pol_ver,
            calculation_trace=trace,
            financial_exposure_type="NO_EXPOSURE",
            evidence=evidence,
            rule_version=self.version,
        )
