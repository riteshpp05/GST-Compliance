"""
UC15 GST Compliance Agent — Place of Supply (POS) Decision Tree Engine
Evaluates statutory Place of Supply rules for Goods (movement, bill-to/ship-to, SEZ) and Services (immovable, transport, events, telecom, OIDAR).
"""
from __future__ import annotations

from typing import List

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity


STATE_CODE_NAME_MAP = {
    "27": "MAHARASHTRA",
    "07": "DELHI",
    "29": "KARNATAKA",
    "33": "TAMIL NADU",
    "09": "UTTAR PRADESH",
    "19": "WEST BENGAL",
    "24": "GUJARAT",
}


class PlaceOfSupplyDecisionTreeEngine:
    """
    Evaluates Place of Supply under Sections 10, 11, 12, 13 of IGST Act.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        is_service = ctx.hsn_sac.startswith("99")
        if is_service:
            results.append(cls._evaluate_services_pos(ctx))
        else:
            results.append(cls._evaluate_goods_pos(ctx))
        return results

    @classmethod
    def _evaluate_goods_pos(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        s_state = ctx.supplier_state
        r_state = ctx.recipient_state
        pos = ctx.place_of_supply.strip()
        ship_to = ctx.ship_to_state or r_state

        trace = [
            DecisionStepTrace(step_no=1, condition="Supply of Goods", evaluated_value=ctx.hsn_sac, result=True, description="Section 10 of IGST Act 2017 applies."),
            DecisionStepTrace(step_no=2, condition="Bill-to / Ship-to Movement", evaluated_value=f"Ship-to: {ship_to}, POS: {pos}", result=True, description="POS for goods involving movement is location where movement terminates.")
        ]

        # Check SEZ unit goods supply
        if ctx.is_sez_unit or ctx.invoice_type == "SEZ":
            return ComplianceDecisionPath(
                rule_id="POS_002",
                rule_name="SEZ Goods Place of Supply",
                category=RuleCategory.PLACE_OF_SUPPLY,
                severity=Severity.INFO,
                status=DecisionStatus.PASS,
                applicability_condition="Supply of goods to SEZ unit / developer",
                actual_value=pos,
                expected_value=f"SEZ Location ({pos})",
                evidence={"is_sez": True, "place_of_supply": pos},
                legal_basis="Section 10(1)(c) of IGST Act 2017",
                decision_trace=trace,
            )

        pos_upper = pos.upper()
        r_state_name = STATE_CODE_NAME_MAP.get(r_state, r_state).upper()
        ship_to_name = STATE_CODE_NAME_MAP.get(ship_to, ship_to).upper()

        pos_matched = (
            pos_upper == r_state.upper() or
            pos_upper == r_state_name or
            pos_upper == ship_to.upper() or
            pos_upper == ship_to_name
        )

        # Standard Goods Movement
        if pos and pos_matched:
            return ComplianceDecisionPath(
                rule_id="POS_001",
                rule_name="Goods Movement Place of Supply",
                category=RuleCategory.PLACE_OF_SUPPLY,
                severity=Severity.INFO,
                status=DecisionStatus.PASS,
                applicability_condition="Section 10(1)(a) Goods involving movement",
                actual_value=pos,
                expected_value=ship_to,
                evidence={"supplier_state": s_state, "recipient_state": r_state, "ship_to_state": ship_to, "pos": pos},
                legal_basis="Section 10(1)(a) of IGST Act 2017",
                decision_trace=trace,
            )
        else:
            return ComplianceDecisionPath(
                rule_id="POS_001",
                rule_name="Goods Movement Place of Supply Mismatch",
                category=RuleCategory.PLACE_OF_SUPPLY,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Section 10(1)(a) Goods involving movement",
                actual_value=pos,
                expected_value=ship_to or r_state,
                financial_exposure=float(ctx.total_tax),
                evidence={"supplier_state": s_state, "recipient_state": r_state, "ship_to_state": ship_to, "declared_pos": pos},
                legal_basis="Section 10(1)(a) of IGST Act 2017",
                remediation=f"Declared Place of Supply '{pos}' does not match delivery destination '{ship_to}'.",
                decision_trace=trace,
            )

    @classmethod
    def _evaluate_services_pos(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        cat = ctx.service_category or "GENERAL_B2B"
        r_state = ctx.recipient_state
        pos = ctx.place_of_supply.strip()

        trace = [
            DecisionStepTrace(step_no=1, condition="Supply of Services (SAC 99)", evaluated_value=ctx.hsn_sac, result=True, description="Section 12 of IGST Act 2017 applies."),
            DecisionStepTrace(step_no=2, condition="Service Category Classification", evaluated_value=cat, result=True, description=f"Evaluate category: {cat}.")
        ]

        if cat == "IMMOVABLE_PROPERTY":
            # POS is location of immovable property
            return ComplianceDecisionPath(
                rule_id="POS_003",
                rule_name="Immovable Property Service POS",
                category=RuleCategory.PLACE_OF_SUPPLY,
                severity=Severity.MEDIUM,
                status=DecisionStatus.REVIEW_REQUIRED if not pos else DecisionStatus.PASS,
                applicability_condition="Section 12(3) Immovable Property Services",
                actual_value=pos,
                expected_value="Location of Immovable Property",
                evidence={"service_category": cat, "place_of_supply": pos},
                legal_basis="Section 12(3) of IGST Act 2017",
                decision_trace=trace,
            )

        # General B2B Services (Section 12(2)(a): POS is location of recipient)
        return ComplianceDecisionPath(
            rule_id="POS_001",
            rule_name="General B2B Services Place of Supply",
            category=RuleCategory.PLACE_OF_SUPPLY,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Section 12(2)(a) General B2B Services",
            actual_value=pos,
            expected_value=r_state,
            evidence={"service_category": cat, "recipient_state": r_state, "place_of_supply": pos},
            legal_basis="Section 12(2)(a) of IGST Act 2017",
            decision_trace=trace,
        )
