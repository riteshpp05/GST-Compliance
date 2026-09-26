"""
UC15 GST Compliance Agent — SAP FI/SD Tax Configuration & Drift Engine
Validates SAP BSEG/BKPF & VBRK/VBRP canonical accounting documents, tax codes V1-V3/A1/O1, condition types JOIC-JOCP, and clearing documents.
"""
from __future__ import annotations

from typing import List

from app.decision.context import ComplianceContext
from app.decision.result import ComplianceDecisionPath, DecisionStatus, DecisionStepTrace
from app.domain.enums.rule_category import RuleCategory
from app.domain.enums.severity import Severity

SAP_TAX_CODES = {
    "V1": {"type": "INPUT_IGST", "rate": 18.0, "cgst": 0.0, "sgst": 0.0, "igst": 18.0, "rcm": False},
    "V2": {"type": "INPUT_LOCAL", "rate": 18.0, "cgst": 9.0, "sgst": 9.0, "igst": 0.0, "rcm": False},
    "V3": {"type": "INPUT_RCM", "rate": 18.0, "cgst": 0.0, "sgst": 0.0, "igst": 18.0, "rcm": True},
    "A1": {"type": "OUTPUT_IGST", "rate": 18.0, "cgst": 0.0, "sgst": 0.0, "igst": 18.0, "rcm": False},
    "O1": {"type": "EXEMPT", "rate": 0.0, "cgst": 0.0, "sgst": 0.0, "igst": 0.0, "rcm": False},
}


class SAPTaxEngine:
    """
    Evaluates SAP FI/SD Tax Codes, Pricing Conditions, and Accounting Document Drift.
    """

    @classmethod
    def evaluate(cls, ctx: ComplianceContext) -> List[ComplianceDecisionPath]:
        results = []
        results.append(cls._evaluate_tax_code_validity(ctx))
        results.append(cls._evaluate_tax_code_drift(ctx))
        results.append(cls._evaluate_clearing_document(ctx))
        return results

    @classmethod
    def _evaluate_tax_code_validity(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        code = str(ctx.sap_tax_code or "").strip().upper()

        trace = [
            DecisionStepTrace(step_no=1, condition="SAP Tax Code Present", evaluated_value=bool(code), result=bool(code), description="Check if SAP tax code (MWSKZ) is populated.")
        ]

        if not code:
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_001",
                rule_name="SAP Tax Code Presence",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.INFO,
                status=DecisionStatus.NOT_APPLICABLE,
                applicability_condition="SAP Tax Code MWSKZ field in BSEG/VBRP",
                actual_value=None,
                expected_value="Valid SAP Tax Code (V1, V2, A1, O1, V3)",
                evidence={"sap_tax_code": None},
                decision_trace=trace,
            )

        if code in SAP_TAX_CODES:
            cfg = SAP_TAX_CODES[code]
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_001",
                rule_name="SAP Tax Code Validity",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.INFO,
                status=DecisionStatus.PASS,
                applicability_condition="SAP Tax Code MWSKZ field in BSEG/VBRP",
                actual_value=code,
                expected_value="Valid SAP Tax Code",
                evidence={"sap_tax_code": code, "configured_type": cfg["type"], "rate": cfg["rate"]},
                decision_trace=trace,
            )
        else:
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_001",
                rule_name="SAP Tax Code Validity",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="SAP Tax Code MWSKZ field in BSEG/VBRP",
                actual_value=code,
                expected_value="Valid SAP Tax Code (V1, V2, A1, O1, V3)",
                financial_exposure=float(ctx.total_tax),
                evidence={"sap_tax_code": code, "allowed": list(SAP_TAX_CODES.keys())},
                remediation=f"SAP Tax Code '{code}' is not defined in FTXP master.",
                decision_trace=trace,
            )

    @classmethod
    def _evaluate_tax_code_drift(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        code = str(ctx.sap_tax_code or "").strip().upper()
        if not code or code not in SAP_TAX_CODES:
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_003",
                rule_name="SAP Tax Code Drift",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.INFO,
                status=DecisionStatus.NOT_APPLICABLE,
                applicability_condition="SAP Tax Code configuration drift evaluation",
                actual_value="N/A",
                expected_value="N/A",
                evidence={"sap_tax_code": code},
            )

        cfg = SAP_TAX_CODES[code]
        cgst = float(ctx.cgst_rate)
        sgst = float(ctx.sgst_rate)
        igst = float(ctx.igst_rate)

        drift = (
            abs(cgst - cfg["cgst"]) > 0.01 or
            abs(sgst - cfg["sgst"]) > 0.01 or
            abs(igst - cfg["igst"]) > 0.01
        )

        trace = [
            DecisionStepTrace(step_no=1, condition="Compare Applied Rates vs SAP Config", evaluated_value=f"Applied: {cgst}%/{sgst}%/{igst}%, Config: {cfg['cgst']}%/{cfg['sgst']}%/{cfg['igst']}%", result=not drift, description="Detect configuration drift.")
        ]

        if drift:
            component_diff = abs(cgst - cfg["cgst"]) + abs(sgst - cfg["sgst"]) + abs(igst - cfg["igst"])
            exposure = float(ctx.taxable_value) * (component_diff / 100.0) / 2.0
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_003",
                rule_name="SAP Tax Code Configuration Drift",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.HIGH,
                status=DecisionStatus.FAIL,
                applicability_condition="SAP Tax Code rate consistency",
                actual_value=f"Applied: CGST {cgst}%, SGST {sgst}%, IGST {igst}%",
                expected_value=f"SAP Tax Code '{code}': CGST {cfg['cgst']}%, SGST {cfg['sgst']}%, IGST {cfg['igst']}%",
                financial_exposure=round(exposure, 2),
                evidence={"sap_tax_code": code, "applied": {"cgst": cgst, "sgst": sgst, "igst": igst}, "sap_configured": cfg},
                remediation=f"Fix SAP Tax Code configuration drift for '{code}' in FTXP.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="SAP_TAX_003",
            rule_name="SAP Tax Code Configuration Verification",
            category=RuleCategory.SAP_TAX_CODE,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="SAP Tax Code rate consistency",
            actual_value="MATCHING",
            expected_value="MATCHING",
            evidence={"sap_tax_code": code, "rates": {"cgst": cgst, "sgst": sgst, "igst": igst}},
            decision_trace=trace,
        )

    @classmethod
    def _evaluate_clearing_document(cls, ctx: ComplianceContext) -> ComplianceDecisionPath:
        clearing = str(ctx.clearing_document or "").strip()
        status = ctx.payment_status.upper()

        trace = [
            DecisionStepTrace(step_no=1, condition="Payment Status is PAID", evaluated_value=status, result=status == "PAID", description="Check if clearing document (AUGBL) is required.")
        ]

        if status == "PAID" and not clearing:
            return ComplianceDecisionPath(
                rule_id="SAP_TAX_004",
                rule_name="SAP Clearing Document Verification",
                category=RuleCategory.SAP_TAX_CODE,
                severity=Severity.MEDIUM,
                status=DecisionStatus.FAIL,
                applicability_condition="SAP FI Vendor Clearing (BSEG-AUGBL)",
                actual_value="PAID with missing clearing document",
                expected_value="Valid clearing document number (AUGBL)",
                evidence={"payment_status": "PAID", "clearing_document": None},
                remediation="Post vendor clearing document (F-44 or F110 auto-payment) in SAP FI.",
                decision_trace=trace,
            )

        return ComplianceDecisionPath(
            rule_id="SAP_TAX_004",
            rule_name="SAP Clearing Document Verification",
            category=RuleCategory.SAP_TAX_CODE,
            severity=Severity.INFO,
            status=DecisionStatus.PASS,
            applicability_condition="SAP FI Vendor Clearing (BSEG-AUGBL)",
            actual_value=clearing or "UNCLEARED",
            expected_value=clearing or "UNCLEARED",
            evidence={"payment_status": status, "clearing_document": clearing or "N/A"},
            decision_trace=trace,
        )
