"""
UC15 GST Compliance Agent — Reverse Charge Mechanism (RCM) Decision Engine
Evaluates Section 9(3) and 9(4) notifications for GTA (9965), Legal (9983), Metal Scrap (7204), E-Waste (8548), and Unregistered Vendors.
"""
from __future__ import annotations

from typing import List

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity

NOTIFIED_RCM_HSN = {
    "9965": {"name": "Goods Transport Agency (GTA) Services", "notification": "Notification 13/2017-CT(Rate)", "section": "9(3)"},
    "9983": {"name": "Legal / Advocate Services", "notification": "Notification 13/2017-CT(Rate)", "section": "9(3)"},
    "7204": {"name": "Metal Scrap Supply from Unregistered Sellers", "notification": "Notification 25/2024-CT(Rate)", "section": "9(3)"},
    "8548": {"name": "E-Waste Scrap Supply", "notification": "Notification 25/2024-CT(Rate)", "section": "9(3)"},
}


class RCMDecisionEngine:
    """
    Evaluates Reverse Charge Mechanism applicability and recipient liability.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        results.append(cls._evaluate_rcm_applicability(ctx))
        return results

    @classmethod
    def _evaluate_rcm_applicability(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        hsn = ctx.hsn_sac.strip()
        prefix = hsn[:4]
        is_unreg_supplier = ctx.supplier_registration_type == "UNREGISTERED"

        is_notified_rcm = prefix in NOTIFIED_RCM_HSN
        rcm_applicable = is_notified_rcm or (is_unreg_supplier and ctx.is_rcm)

        trace = [
            DecisionStepTrace(step_no=1, condition="Check Notified RCM HSN/SAC", evaluated_value=prefix, result=is_notified_rcm, description="Check Section 9(3) notifications."),
            DecisionStepTrace(step_no=2, condition="Unregistered Supplier Section 9(4)", evaluated_value=is_unreg_supplier, result=is_unreg_supplier, description="Check Section 9(4) applicability.")
        ]

        if rcm_applicable:
            meta = NOTIFIED_RCM_HSN.get(prefix, {"name": "Reverse Charge Supply", "notification": "Section 9(4) CGST Act", "section": "9(4)"})
            tax = float(ctx.total_tax)

            return ComplianceDecisionPath(
                rule_id="RCM_001",
                rule_name="Reverse Charge Mechanism Identification & Liability",
                category=RuleCategory.RCM,
                severity=Severity.HIGH,
                status=DecisionStatus.PASS if ctx.is_rcm else DecisionStatus.FAIL,
                applicability_condition="Section 9(3)/9(4) Reverse Charge Mechanism",
                actual_value="RCM_CLASSIFIED" if ctx.is_rcm else "FORWARD_CHARGE_WRONGLY_APPLIED",
                expected_value="RCM_CLASSIFIED",
                financial_exposure=0.0 if ctx.is_rcm else tax,
                evidence={"hsn_sac": hsn, "category": meta["name"], "section": meta["section"], "notification": meta["notification"], "rcm_tax_liability": tax},
                legal_basis=f"{meta['section']} of CGST Act 2017 & {meta['notification']}",
                remediation="Pay tax under RCM directly via electronic cash ledger and claim ITC if eligible.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="RCM_001",
            rule_name="Reverse Charge Mechanism Identification",
            category=RuleCategory.RCM,
            severity=Severity.INFO,
            status=DecisionStatus.NOT_APPLICABLE,
            applicability_condition="Section 9(3)/9(4) Reverse Charge Mechanism",
            actual_value="FORWARD_CHARGE",
            expected_value="FORWARD_CHARGE",
            evidence={"hsn_sac": hsn, "is_rcm": False},
            legal_basis="Section 9(1) of CGST Act 2017",
            decision_trace=trace,
        )
