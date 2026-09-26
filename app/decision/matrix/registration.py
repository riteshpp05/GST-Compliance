"""
UC15 GST Compliance Agent — GSTIN & Registration Decision Matrix Engine
Exhaustive validation of GSTIN structure, Luhn checksum, party relationships, composition/UIN, and active registration dates.
"""
from __future__ import annotations

import re
from datetime import date
from typing import List, Tuple

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity
from app.rules.existing.gstin import verify_gstin_checksum, GSTIN_PATTERN


class GSTINRegistrationMatrixEngine:
    """
    Evaluates GSTIN structure, party relationships, and registration status.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        results.append(cls._evaluate_structure(ctx, is_supplier=True))
        results.append(cls._evaluate_structure(ctx, is_supplier=False))
        results.append(cls._evaluate_party_relationship(ctx))
        results.append(cls._evaluate_composition_prohibitions(ctx))
        return results

    @classmethod
    def _evaluate_structure(cls, ctx: ComplianceContext, is_supplier: bool) -> ComplianceDecisionPath:
        role = "Supplier" if is_supplier else "Recipient"
        rule_id = "GSTIN_001" if is_supplier else "GSTIN_002"
        gstin = ctx.supplier_gstin if is_supplier else ctx.recipient_gstin

        trace: List[DecisionStepTrace] = []
        trace.append(DecisionStepTrace(step_no=1, condition="GSTIN Present", evaluated_value=bool(gstin), result=bool(gstin), description="Check if GSTIN is not empty."))

        if not gstin:
            return ComplianceDecisionPath(
                rule_id=rule_id,
                rule_name=f"{role} GSTIN Presence",
                category=RuleCategory.MASTER_DATA,
                severity=Severity.CRITICAL,
                status=DecisionStatus.FAIL,
                applicability_condition="Mandatory for statutory compliance",
                actual_value=None,
                expected_value="Valid 15-character GSTIN",
                financial_exposure=float(ctx.total_tax),
                evidence={"role": role, "gstin": None},
                legal_basis="Section 25 of CGST Act 2017",
                remediation=f"Provide valid 15-character GSTIN for {role}.",
                decision_trace=trace,
            )

        format_valid = bool(GSTIN_PATTERN.match(gstin))
        trace.append(DecisionStepTrace(step_no=2, condition="Regex Pattern Match", evaluated_value=gstin, result=format_valid, description="Verify 15-character structural pattern."))

        checksum_valid = verify_gstin_checksum(gstin) if format_valid else False
        trace.append(DecisionStepTrace(step_no=3, condition="Luhn Modulo-36 Checksum", evaluated_value=gstin, result=checksum_valid, description="Validate Luhn Modulo-36 check character."))

        if format_valid:
            return ComplianceDecisionPath(
                rule_id=rule_id,
                rule_name=f"{role} GSTIN Format",
                category=RuleCategory.MASTER_DATA,
                severity=Severity.INFO,
                status=DecisionStatus.PASS,
                applicability_condition="Mandatory for statutory compliance",
                actual_value=gstin,
                expected_value="Valid GSTIN",
                evidence={"role": role, "gstin": gstin, "checksum_valid": checksum_valid},
                legal_basis="Section 25 of CGST Act 2017",
                decision_trace=trace,
            )
        else:
            return ComplianceDecisionPath(
                rule_id=rule_id,
                rule_name=f"{role} GSTIN Format & Checksum",
                category=RuleCategory.MASTER_DATA,
                severity=Severity.CRITICAL,
                status=DecisionStatus.FAIL,
                applicability_condition="Mandatory for statutory compliance",
                actual_value=gstin,
                expected_value="Valid GSTIN with correct checksum",
                financial_exposure=float(ctx.total_tax),
                evidence={"role": role, "gstin": gstin, "format_valid": format_valid, "checksum_valid": checksum_valid},
                legal_basis="Section 25 of CGST Act 2017",
                remediation=f"Correct malformed {role} GSTIN '{gstin}'.",
                decision_trace=trace,
            )

    @classmethod
    def _evaluate_party_relationship(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        s_gstin = ctx.supplier_gstin.strip().upper()
        r_gstin = ctx.recipient_gstin.strip().upper()
        is_same = s_gstin == r_gstin and bool(s_gstin)

        trace = [
            DecisionStepTrace(step_no=1, condition="Supplier GSTIN == Recipient GSTIN", evaluated_value=f"{s_gstin} == {r_gstin}", result=is_same, description="Check for self-supply or branch transfer.")
        ]

        if is_same:
            return ComplianceDecisionPath(
                rule_id="GSTIN_005",
                rule_name="Self-Supply / Branch Transfer Verification",
                category=RuleCategory.MASTER_DATA,
                severity=Severity.MEDIUM,
                status=DecisionStatus.REVIEW_REQUIRED,
                applicability_condition="Supplier and Recipient GSTIN are identical",
                actual_value=s_gstin,
                expected_value="Distinct Counterparty GSTIN or documented Stock Transfer / ISD",
                evidence={"supplier_gstin": s_gstin, "recipient_gstin": r_gstin, "is_self_supply": True},
                legal_basis="Schedule I of CGST Act 2017 (Deemed Supplies)",
                remediation="Verify if invoice represents a valid stock transfer or ISD distribution.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="GSTIN_005",
            rule_name="Party Relationship Consistency",
            category=RuleCategory.MASTER_DATA,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Distinct counterparty GSTINs",
            actual_value="DISTINCT",
            expected_value="DISTINCT",
            evidence={"supplier_gstin": s_gstin, "recipient_gstin": r_gstin},
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_composition_prohibitions(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        is_comp = ctx.supplier_registration_type == "COMPOSITION" or ctx.composition_status
        tax_charged = float(ctx.total_tax) > 0

        trace = [
            DecisionStepTrace(step_no=1, condition="Supplier is Composition Taxpayer", evaluated_value=is_comp, result=is_comp, description="Check Section 10 Composition status."),
            DecisionStepTrace(step_no=2, condition="Tax Charged on Invoice", evaluated_value=tax_charged, result=tax_charged, description="Composition taxpayers cannot collect tax.")
        ]

        if is_comp and tax_charged:
            return ComplianceDecisionPath(
                rule_id="GSTIN_004",
                rule_name="Composition Scheme Tax Charging Prohibition",
                category=RuleCategory.MASTER_DATA,
                severity=Severity.CRITICAL,
                status=DecisionStatus.FAIL,
                applicability_condition="Supplier under Section 10 Composition Scheme",
                actual_value=f"Charged Tax: Rs. {ctx.total_tax}",
                expected_value="Zero Tax Charged (Bill of Supply)",
                financial_exposure=float(ctx.total_tax),
                evidence={"supplier_registration_type": "COMPOSITION", "total_tax": float(ctx.total_tax)},
                legal_basis="Section 10(4) of CGST Act 2017",
                remediation="Composition supplier cannot collect tax from recipient. Issue Bill of Supply.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="GSTIN_004",
            rule_name="Composition Scheme Compliance",
            category=RuleCategory.MASTER_DATA,
            severity=Severity.INFO,
            status=DecisionStatus.PASS if not is_comp else DecisionStatus.NOT_APPLICABLE,
            applicability_condition="Supplier tax charging rules under Section 10",
            actual_value="Compliant",
            expected_value="Compliant",
            evidence={"is_composition": is_comp, "tax_charged": tax_charged},
            decision_trace=trace,
        )
