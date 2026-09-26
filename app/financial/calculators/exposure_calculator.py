"""
UC15 GST Compliance Agent — Invoice Exposure Calculator (Sprint 6)
Evaluates compliance findings on an invoice to produce deterministic FinancialImpact instances.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union

from app.domain.models.invoice import Invoice
from app.domain.models.validation import ComplianceDecision, ValidationResult
from app.financial.calculators.tax_difference import (
    TaxDifferenceCalculator,
    parse_decimal_safe,
    parse_tax_rate,
)
from app.financial.models.impact import (
    CalculationStatus,
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    round_monetary,
)


def _extract_date_safe(d: Any) -> Optional[date]:
    if isinstance(d, date):
        return d
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, str):
        try:
            return date.fromisoformat(d.strip()[:10])
        except Exception:
            pass
    return None


class InvoiceExposureCalculator:
    """
    Orchestrates financial impact quantification across all gate findings for an invoice.
    Consumes compliance decisions without modifying or duplicating validation logic.
    """

    def __init__(self) -> None:
        self.tax_calc = TaxDifferenceCalculator()

    def evaluate_decision(
        self,
        decision: ComplianceDecision,
        invoice: Optional[Invoice] = None,
    ) -> List[FinancialImpact]:
        """
        Produce FinancialImpact records for all findings in a ComplianceDecision.
        """
        return self.calculate_invoice_impact(decision, invoice)

    def calculate_invoice_impact(
        self,
        decision: ComplianceDecision,
        invoice: Optional[Invoice] = None,
    ) -> List[FinancialImpact]:
        """
        Produce FinancialImpact records for all findings in a ComplianceDecision.
        """
        impacts: List[FinancialImpact] = []
        inv_id = decision.invoice_no
        inv_date = _extract_date_safe(decision.invoice_date)
        counterparty_id = decision.counterparty_gstin or decision.counterparty_name
        counterparty_name = decision.counterparty_name

        taxable_val = parse_decimal_safe(getattr(decision, "taxable_value_inr", None))
        total_amt = parse_decimal_safe(getattr(decision, "total_amt", None))
        if invoice:
            if taxable_val is None:
                taxable_val = parse_decimal_safe(invoice.taxable_value)
            if total_amt is None:
                total_amt = parse_decimal_safe(invoice.total_amount)

        # Compute total tax
        total_tax: Optional[Decimal] = None
        if total_amt is not None and taxable_val is not None:
            total_tax = total_amt - taxable_val if total_amt >= taxable_val else Decimal("0.00")
        elif invoice and invoice.total_tax:
            total_tax = parse_decimal_safe(invoice.total_tax)

        gates = getattr(decision, "gates", [])
        failed_gates = [g for g in gates if g.status == "FAIL"]

        # If compliant or no failures
        if not failed_gates:
            clean_impact = FinancialImpact(
                impact_id=f"IMP-{inv_id}-CLEAN",
                invoice_id=inv_id,
                invoice_date=inv_date,
                counterparty_id=counterparty_id,
                counterparty_name=counterparty_name,
                rule_id="COMPLIANT",
                rule_category="COMPLIANCE",
                impact_type=FinancialImpactType.OTHER,
                calculation_status=CalculationStatus.NOT_APPLICABLE,
                direction=ImpactDirection.NO_TAX_DIFFERENCE,
                taxable_value=taxable_val,
                potential_exposure=Decimal("0.00"),
                currency="INR",
                calculation_basis="Invoice is fully compliant; zero potential financial exposure.",
                confidence=1.0,
                evidence={"status": "COMPLIANT", "failed_gates": 0},
            )
            return [clean_impact]

        # Process each failed gate
        for g in failed_gates:
            rid = g.rule_id
            cat = g.category or "STATUTORY"

            # 1. Gate 3 / Tax Rate Mismatch
            if cat == "TAX" or "tax" in rid.lower() or g.gate_no == 3:
                recorded_rate = None
                expected_rate = None
                if isinstance(g.evidence, dict):
                    applied = g.evidence.get("applied_rates")
                    expected = g.evidence.get("expected_rates")
                    if applied and expected:
                        recorded_rate = applied
                        expected_rate = expected
                if recorded_rate is None:
                    recorded_rate = g.actual_value
                if expected_rate is None:
                    expected_rate = g.expected_value

                # If still not in gate, check invoice line item rates
                if recorded_rate is None and invoice:
                    if invoice.igst_rate and float(invoice.igst_rate) > 0:
                        recorded_rate = invoice.igst_rate
                    elif invoice.cgst_rate and invoice.sgst_rate:
                        recorded_rate = invoice.cgst_rate + invoice.sgst_rate

                impact = self.tax_calc.calculate(
                    invoice_id=inv_id,
                    taxable_value=taxable_val,
                    recorded_rate=recorded_rate,
                    expected_rate=expected_rate,
                    invoice_date=inv_date,
                    counterparty_id=counterparty_id,
                    counterparty_name=counterparty_name,
                    rule_id=rid,
                    rule_category=cat,
                    tax_type="INTER_STATE" if (invoice and float(invoice.igst_rate) > 0) else "INTRA_STATE",
                )
                impacts.append(impact)

            # 2. Gate 6 / Blocked ITC
            elif cat == "ITC" or "itc" in rid.lower() or g.gate_no == 6:
                # ITC applies strictly to inward supplies (AP)
                is_ap = getattr(decision, "direction", "AP") == "AP" or (invoice and invoice.direction == "AP")
                if not is_ap:
                    impacts.append(
                        FinancialImpact(
                            impact_id=f"IMP-{inv_id}-{rid}",
                            invoice_id=inv_id,
                            invoice_date=inv_date,
                            counterparty_id=counterparty_id,
                            counterparty_name=counterparty_name,
                            rule_id=rid,
                            rule_category=cat,
                            impact_type=FinancialImpactType.ITC_EXPOSURE,
                            calculation_status=CalculationStatus.NOT_APPLICABLE,
                            direction=ImpactDirection.NOT_APPLICABLE,
                            taxable_value=taxable_val,
                            potential_exposure=Decimal("0.00"),
                            currency="INR",
                            calculation_basis="ITC is not applicable to outward (AR) sales invoices.",
                            reason="ITC is not applicable to outward (AR) sales invoices.",
                            evidence={"invoice_id": inv_id, "direction": "AR", "rule_message": g.message},
                        )
                    )
                elif total_tax is not None and total_tax > Decimal("0.00"):
                    itc_exp = round_monetary(total_tax)
                    calc_basis = f"Blocked Section 17(5) ITC on inward supply input tax: INR {itc_exp:,.2f}"
                    impacts.append(
                        FinancialImpact(
                            impact_id=f"IMP-{inv_id}-{rid}",
                            invoice_id=inv_id,
                            invoice_date=inv_date,
                            counterparty_id=counterparty_id,
                            counterparty_name=counterparty_name,
                            rule_id=rid,
                            rule_category=cat,
                            impact_type=FinancialImpactType.ITC_EXPOSURE,
                            calculation_status=CalculationStatus.CALCULATED,
                            direction=ImpactDirection.NOT_APPLICABLE,
                            taxable_value=taxable_val,
                            recorded_tax=itc_exp,
                            expected_tax=Decimal("0.00"),
                            potential_exposure=itc_exp,
                            currency="INR",
                            calculation_basis=calc_basis,
                            confidence=1.0,
                            evidence={
                                "invoice_id": inv_id,
                                "direction": "AP",
                                "blocked_input_tax": float(itc_exp),
                                "rule_message": g.message,
                            },
                        )
                    )
                else:
                    # Missing tax information
                    impacts.append(
                        FinancialImpact(
                            impact_id=f"IMP-{inv_id}-{rid}",
                            invoice_id=inv_id,
                            invoice_date=inv_date,
                            counterparty_id=counterparty_id,
                            counterparty_name=counterparty_name,
                            rule_id=rid,
                            rule_category=cat,
                            impact_type=FinancialImpactType.ITC_EXPOSURE,
                            calculation_status=CalculationStatus.UNDETERMINED,
                            direction=ImpactDirection.NOT_APPLICABLE,
                            taxable_value=taxable_val,
                            potential_exposure=Decimal("0.00"),
                            currency="INR",
                            calculation_basis="Cannot calculate ITC exposure: input tax amount is unavailable.",
                            reason="Total input tax amount unavailable on invoice.",
                            required_data=["total_tax", "cgst_amount", "sgst_amount", "igst_amount"],
                            evidence={"invoice_id": inv_id, "rule_message": g.message},
                        )
                    )

            # 3. Gate 5 / E-Way Bill
            elif cat in ("EWAY_BILL", "EWAY") or "eway" in rid.lower() or "ewb" in rid.lower() or g.gate_no == 5:
                # As per statutory guidelines: Do NOT invent a penalty! Return UNDETERMINED
                impacts.append(
                    FinancialImpact(
                        impact_id=f"IMP-{inv_id}-{rid}",
                        invoice_id=inv_id,
                        invoice_date=inv_date,
                        counterparty_id=counterparty_id,
                        counterparty_name=counterparty_name,
                        rule_id=rid,
                        rule_category=cat,
                        impact_type=FinancialImpactType.EWB_RELATED_EXPOSURE,
                        calculation_status=CalculationStatus.UNDETERMINED,
                        direction=ImpactDirection.NOT_APPLICABLE,
                        taxable_value=taxable_val,
                        potential_exposure=Decimal("0.00"),
                        currency="INR",
                        calculation_basis="No configured monetary penalty policy available for E-Way Bill non-compliance.",
                        reason="Potential financial consequence could not be quantified because no configured penalty/financial policy was available.",
                        required_data=["ewb_penalty_policy"],
                        evidence={"invoice_id": inv_id, "rule_message": g.message},
                    )
                )

            # 4. Gate 4 / Place of Supply
            elif cat in ("PLACE_OF_SUPPLY", "POS") or "pos" in rid.lower() or g.gate_no == 4:
                # Place of supply tax head misclassification has no direct statutory loss in current model
                # (Under Section 77 CGST / Section 19 IGST, misallocated taxes are refundable without interest)
                impacts.append(
                    FinancialImpact(
                        impact_id=f"IMP-{inv_id}-{rid}",
                        invoice_id=inv_id,
                        invoice_date=inv_date,
                        counterparty_id=counterparty_id,
                        counterparty_name=counterparty_name,
                        rule_id=rid,
                        rule_category=cat,
                        impact_type=FinancialImpactType.OTHER,
                        calculation_status=CalculationStatus.NOT_APPLICABLE,
                        direction=ImpactDirection.NOT_APPLICABLE,
                        taxable_value=taxable_val,
                        potential_exposure=Decimal("0.00"),
                        currency="INR",
                        calculation_basis="Place of supply misclassification has no direct statutory monetary exposure in current model (taxes refundable under Sec 77 CGST / Sec 19 IGST).",
                        reason="No financial consequence supported by current model for place of supply tax head reallocation.",
                        evidence={"invoice_id": inv_id, "rule_message": g.message},
                    )
                )

            # 5. Gate 1 / Data Quality / Other
            else:
                impacts.append(
                    FinancialImpact(
                        impact_id=f"IMP-{inv_id}-{rid}",
                        invoice_id=inv_id,
                        invoice_date=inv_date,
                        counterparty_id=counterparty_id,
                        counterparty_name=counterparty_name,
                        rule_id=rid,
                        rule_category=cat,
                        impact_type=FinancialImpactType.DATA_QUALITY_EXPOSURE if cat == "MASTER_DATA" else FinancialImpactType.OTHER,
                        calculation_status=CalculationStatus.UNDETERMINED,
                        direction=ImpactDirection.NOT_APPLICABLE,
                        taxable_value=taxable_val,
                        potential_exposure=Decimal("0.00"),
                        currency="INR",
                        calculation_basis=f"No direct financial formula applicable for {cat} failure.",
                        reason=f"Financial exposure cannot be quantified directly from {cat} defect.",
                        required_data=["statutory_penalty_schedule"],
                        evidence={"invoice_id": inv_id, "rule_message": g.message},
                    )
                )

        return impacts
