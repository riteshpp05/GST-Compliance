"""
UC15 GST Compliance Agent — Tax Rate & Component Symmetry Decision Matrix Engine
Validates line/invoice tax mathematics, rounding tolerances, and intra-state vs inter-state component symmetry.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity


class TaxDeterminationMatrixEngine:
    """
    Evaluates tax mathematics, rate matching, and component symmetry.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        results.append(cls._evaluate_component_symmetry(ctx))
        results.append(cls._evaluate_tax_mathematics(ctx))
        results.append(cls._evaluate_invoice_total_rounding(ctx))
        return results

    @classmethod
    def _evaluate_component_symmetry(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        from app.decision.context import normalize_state
        pos_norm = normalize_state(ctx.place_of_supply)
        s_norm = normalize_state(ctx.supplier_state)
        r_norm = normalize_state(ctx.recipient_state)
        is_inter_pos = bool(pos_norm and s_norm and pos_norm != s_norm)
        is_inter = (
            ctx.transaction_type == "INTER_STATE"
            or (bool(s_norm and r_norm) and s_norm != r_norm)
            or is_inter_pos
        )
        cgst = float(ctx.cgst_amount)
        sgst = float(ctx.sgst_amount)
        igst = float(ctx.igst_amount)

        trace = [
            DecisionStepTrace(step_no=1, condition="Transaction Type is Inter-State", evaluated_value=is_inter, result=is_inter, description="Determine if IGST or CGST+SGST applies.")
        ]

        if is_inter:
            has_local_tax = (cgst > 0 or sgst > 0)
            if has_local_tax:
                exposure = cgst + sgst
                return ComplianceDecisionPath(
                    rule_id="TAX_002",
                    rule_name="Inter-State Tax Structure Symmetry",
                    category=RuleCategory.TAX,
                    severity=Severity.HIGH,
                    status=DecisionStatus.FAIL,
                    applicability_condition="Inter-State transaction requiring IGST",
                    actual_value=f"CGST: Rs.{cgst:,.2f}, SGST: Rs.{sgst:,.2f}, IGST: Rs.{igst:,.2f}",
                    expected_value="IGST only (Zero CGST/SGST)",
                    difference=Decimal(str(exposure)),
                    financial_exposure=exposure,
                    evidence={"transaction_type": "INTER_STATE", "cgst": cgst, "sgst": sgst, "igst": igst},
                    legal_basis="Section 5 of IGST Act 2017",
                    remediation="Inter-state supplies require IGST. Charging CGST+SGST is legally invalid.",
                    decision_trace=trace,
                )
        else: # Intra-state
            has_igst = igst > 0
            asymmetric_local = abs(cgst - sgst) > 0.01
            if has_igst or asymmetric_local:
                exposure = igst if has_igst else abs(cgst - sgst)
                return ComplianceDecisionPath(
                    rule_id="TAX_002",
                    rule_name="Intra-State Tax Structure Symmetry",
                    category=RuleCategory.TAX,
                    severity=Severity.HIGH,
                    status=DecisionStatus.FAIL,
                    applicability_condition="Intra-State transaction requiring equal CGST and SGST",
                    actual_value=f"CGST: Rs.{cgst:,.2f}, SGST: Rs.{sgst:,.2f}, IGST: Rs.{igst:,.2f}",
                    expected_value="Equal CGST and SGST (Zero IGST)",
                    difference=Decimal(str(exposure)),
                    financial_exposure=exposure,
                    evidence={"transaction_type": "INTRA_STATE", "cgst": cgst, "sgst": sgst, "igst": igst},
                    legal_basis="Section 9 of CGST Act 2017 & SGST Act 2017",
                    remediation="Intra-state supplies require symmetric CGST and SGST.",
                    decision_trace=trace,
                )

        return ComplianceDecisionPath(
            rule_id="TAX_002",
            rule_name="Tax Component Symmetry",
            category=RuleCategory.TAX,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Tax component structure verification",
            actual_value="SYMMETRIC",
            expected_value="SYMMETRIC",
            evidence={"transaction_type": ctx.transaction_type, "cgst": cgst, "sgst": sgst, "igst": igst},
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_tax_mathematics(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        taxable = float(ctx.taxable_value)
        cgst_r = float(ctx.cgst_rate)
        sgst_r = float(ctx.sgst_rate)
        igst_r = float(ctx.igst_rate)

        expected_cgst_a = round((taxable * cgst_r) / 100.0, 2)
        expected_sgst_a = round((taxable * sgst_r) / 100.0, 2)
        expected_igst_a = round((taxable * igst_r) / 100.0, 2)
        expected_total_tax = expected_cgst_a + expected_sgst_a + expected_igst_a + float(ctx.cess_amount)

        actual_total_tax = float(ctx.total_tax)
        diff = abs(actual_total_tax - expected_total_tax)

        trace = [
            DecisionStepTrace(step_no=1, condition="Calculate Taxable Value * Rates", evaluated_value=f"Expected Tax: {expected_total_tax}", result=True, description="Verify line tax calculation."),
            DecisionStepTrace(step_no=2, condition="Compare Total Tax Difference", evaluated_value=f"Diff: {diff}", result=diff <= 1.0, description="Tolerance <= Rs. 1.00 for rounding.")
        ]

        if diff > 1.0:
            return ComplianceDecisionPath(
                rule_id="TAX_004",
                rule_name="Tax Calculation & Rounding Mathematics",
                category=RuleCategory.TAX,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="Mathematical tax validation",
                actual_value=f"Actual Tax: Rs.{actual_total_tax:,.2f}",
                expected_value=f"Expected Tax: Rs.{expected_total_tax:,.2f}",
                difference=Decimal(str(round(diff, 2))),
                financial_exposure=round(diff, 2),
                evidence={"taxable_value": taxable, "actual_total_tax": actual_total_tax, "expected_total_tax": expected_total_tax, "difference": round(diff, 2)},
                legal_basis="Section 15 of CGST Act 2017 & Rule 170",
                remediation="Recalculate tax amounts to align with taxable value * rate.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="TAX_004",
            rule_name="Tax Calculation & Rounding Mathematics",
            category=RuleCategory.TAX,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Mathematical tax validation",
            actual_value=actual_total_tax,
            expected_value=expected_total_tax,
            evidence={"taxable_value": taxable, "total_tax": actual_total_tax, "rounding_diff": round(diff, 2)},
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_invoice_total_rounding(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        taxable = float(ctx.taxable_value)
        total_tax = float(ctx.total_tax)
        discount = float(ctx.discount)
        freight = float(ctx.freight)
        other = float(ctx.other_charges)

        expected_inv_total = taxable + total_tax + freight + other - discount
        actual_inv_total = float(ctx.invoice_total)
        diff = abs(actual_inv_total - expected_inv_total)

        trace = [
            DecisionStepTrace(step_no=1, condition="Taxable + Tax + Charges - Discount", evaluated_value=f"Expected Total: {expected_inv_total}", result=True, description="Verify invoice grand total."),
            DecisionStepTrace(step_no=2, condition="Compare Invoice Total Difference", evaluated_value=f"Diff: {diff}", result=diff <= 2.0, description="Rounding tolerance <= Rs. 2.00.")
        ]

        if diff > 2.0:
            return ComplianceDecisionPath(
                rule_id="TAX_005",
                rule_name="Invoice Grand Total Reconciliation",
                category=RuleCategory.TAX,
                severity=Severity.MEDIUM,
                status=DecisionStatus.FAIL,
                applicability_condition="Invoice grand total verification",
                actual_value=f"Actual Total: Rs.{actual_inv_total:,.2f}",
                expected_value=f"Expected Total: Rs.{expected_inv_total:,.2f}",
                difference=Decimal(str(round(diff, 2))),
                financial_exposure=round(diff, 2),
                evidence={"taxable": taxable, "total_tax": total_tax, "actual_grand_total": actual_inv_total, "expected_grand_total": expected_inv_total},
                legal_basis="Section 15 of CGST Act 2017",
                remediation="Reconcile invoice grand total with taxable value, tax, freight, and discounts.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="TAX_005",
            rule_name="Invoice Grand Total Reconciliation",
            category=RuleCategory.TAX,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="Invoice grand total verification",
            actual_value=actual_inv_total,
            expected_value=expected_inv_total,
            evidence={"grand_total": actual_inv_total, "rounding_variance": round(diff, 2)},
            decision_trace=trace,
        )
