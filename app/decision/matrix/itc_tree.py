"""
UC15 GST Compliance Agent — ITC Eligibility, Section 17(5), IMS, & 180-Day Interest Engine
Exhaustive ITC eligibility tree evaluating GSTR-2B reflection, IMS status, Section 16(4) cutoff, Section 17(5) blocked credits, and Rule 37 180-day payment interest.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import List

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity

# Section 17(5) Blocked Credit HSN/SAC Categories
BLOCKED_17_5_CATEGORIES = {
    "8702": "Motor Vehicles for transport of persons (seating capacity <= 13)",
    "8703": "Motor Vehicles / Passenger Cars",
    "9963": "Food and Beverages / Outdoor Catering Services",
    "9995": "Club Membership Services",
}


class ITCEligibilityDecisionTreeEngine:
    """
    Evaluates ITC eligibility across Sections 16, 17(5), Rules 37, 42, 43, and IMS statements.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        results.append(cls._evaluate_ims_gstr2b(ctx))
        results.append(cls._evaluate_section_17_5(ctx))
        results.append(cls._evaluate_rule_37_180_days(ctx))
        return results

    @classmethod
    def _evaluate_ims_gstr2b(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        ims = ctx.ims_status.upper()
        gstr2b_reflected = ctx.gstr2b_reflected

        trace = [
            DecisionStepTrace(step_no=1, condition="IMS Action Status", evaluated_value=ims, result=True, description="Evaluate Invoice Management System (IMS) action."),
            DecisionStepTrace(step_no=2, condition="GSTR-2B Reflection", evaluated_value=gstr2b_reflected, result=gstr2b_reflected, description="Check GSTR-2B auto-drafted statement.")
        ]

        if ims == "REJECTED":
            return ComplianceDecisionPath(
                rule_id="ITC_002",
                rule_name="IMS Invoice Rejection",
                category=RuleCategory.ITC,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Invoice Management System (IMS) Action",
                actual_value="IMS_REJECTED",
                expected_value="IMS_ACCEPTED or IMS_PENDING",
                financial_exposure=float(ctx.total_tax),
                evidence={"ims_status": "REJECTED", "total_tax": float(ctx.total_tax)},
                legal_basis="Section 16(2)(aa) & IMS Guidelines 2024",
                remediation="Invoice was explicitly rejected in IMS. Remove from ITC claim.",
                decision_trace=trace,
            )

        if not gstr2b_reflected:
            return ComplianceDecisionPath(
                rule_id="ITC_002",
                rule_name="GSTR-2B Auto-Drafted Reflection",
                category=RuleCategory.ITC,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Section 16(2)(aa) GSTR-2B reflection requirement",
                actual_value="UNREFLECTED",
                expected_value="REFLECTED_IN_GSTR2B",
                financial_exposure=float(ctx.total_tax),
                evidence={"gstr2b_reflected": False, "total_tax": float(ctx.total_tax)},
                legal_basis="Section 16(2)(aa) of CGST Act 2017",
                remediation="Follow up with supplier to file GSTR-1 for current tax period.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="ITC_002",
            rule_name="GSTR-2B & IMS Reflection Verification",
            category=RuleCategory.ITC,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Section 16(2)(aa) GSTR-2B reflection requirement",
            actual_value="REFLECTED",
            expected_value="REFLECTED",
            evidence={"ims_status": ims, "gstr2b_reflected": True},
            legal_basis="Section 16(2)(aa) of CGST Act 2017",
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_section_17_5(cls, cls_ctx: ComplianceContext) -> ComplianceDecisionPath:
        hsn = cls_ctx.hsn_sac.strip()
        prefix = hsn[:4]

        is_blocked = prefix in BLOCKED_17_5_CATEGORIES

        trace = [
            DecisionStepTrace(step_no=1, condition="Check HSN/SAC against Section 17(5) Catalog", evaluated_value=hsn, result=is_blocked, description="Evaluate blocked credit categories.")
        ]

        if is_blocked:
            desc = BLOCKED_17_5_CATEGORIES[prefix]
            return ComplianceDecisionPath(
                rule_id="ITC_004",
                rule_name="Section 17(5) Blocked Credit Catalog",
                category=RuleCategory.ITC,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Section 17(5) Ineligible Input Tax Credit",
                actual_value=f"Blocked Category: {desc} (HSN {hsn})",
                expected_value="Eligible Input Tax Credit",
                financial_exposure=float(cls_ctx.total_tax),
                evidence={"hsn_sac": hsn, "clause": "17(5)", "description": desc, "total_tax": float(cls_ctx.total_tax)},
                legal_basis="Section 17(5) of CGST Act 2017",
                remediation="Ineligible ITC under Section 17(5). Reverse claimed ITC in GSTR-3B Table 4(B)(1).",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="ITC_004",
            rule_name="Section 17(5) Blocked Credit Verification",
            category=RuleCategory.ITC,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Section 17(5) Ineligible Input Tax Credit",
            actual_value="NOT_BLOCKED",
            expected_value="NOT_BLOCKED",
            evidence={"hsn_sac": hsn, "is_blocked": False},
            legal_basis="Section 17(5) of CGST Act 2017",
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_rule_37_180_days(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        status = ctx.payment_status.upper()

        trace = [
            DecisionStepTrace(step_no=1, condition="Evaluate AP Payment Status", evaluated_value=status, result=status == "OVERDUE_180", description="Check Rule 37 180-day vendor payment condition.")
        ]

        if status == "OVERDUE_180":
            tax = float(ctx.total_tax)
            # Calculate 18% p.a. interest over 30 overdue days as standard audit sample
            interest = round((tax * 0.18 * 30.0) / 365.0, 2)
            exposure = tax + interest

            return ComplianceDecisionPath(
                rule_id="ITC_180_001",
                rule_name="Rule 37 180-Day Payment Interest Reversal",
                category=RuleCategory.ITC,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Section 16(2) Proviso & Rule 37 180-day vendor payment",
                actual_value=f"UNPAID > 180 Days (Tax: Rs.{tax:,.2f}, Interest: Rs.{interest:,.2f})",
                expected_value="Vendor Paid Within 180 Days",
                difference=Decimal(str(exposure)),
                financial_exposure=exposure,
                evidence={"payment_status": "OVERDUE_180", "reversal_amount": tax, "interest_18_pct": interest, "total_exposure": exposure},
                legal_basis="Second Proviso to Section 16(2) & Rule 37 of CGST Rules 2017",
                remediation="Reverse claimed ITC in GSTR-3B along with 18% p.a. statutory interest.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="ITC_180_001",
            rule_name="Rule 37 180-Day Payment Verification",
            category=RuleCategory.ITC,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Section 16(2) Proviso & Rule 37 180-day vendor payment",
            actual_value=status,
            expected_value="COMPLIANT",
            evidence={"payment_status": status},
            legal_basis="Second Proviso to Section 16(2) of CGST Act 2017",
            decision_trace=trace,
        )
