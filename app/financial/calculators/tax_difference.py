"""
UC15 GST Compliance Agent — Tax Difference Calculator (Sprint 6)
Computes deterministic tax discrepancies, rate mismatches, overcharge/undercharge directions,
and component-level (CGST/SGST/IGST) tax differences using Decimal precision.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple, Union

from app.financial.models.impact import (
    CalculationStatus,
    FinancialImpact,
    FinancialImpactType,
    ImpactDirection,
    round_monetary,
)


def parse_decimal_safe(val: Any) -> Optional[Decimal]:
    """Safely parse input to Decimal, returning None on failure."""
    if val is None or val == "":
        return None
    if isinstance(val, Decimal):
        return val
    try:
        clean_str = str(val).strip().replace(",", "").replace("₹", "").replace("INR", "").strip()
        return Decimal(clean_str)
    except (InvalidOperation, ValueError):
        return None


def parse_tax_rate(val: Any) -> Optional[Decimal]:
    """
    Parse rate input (number, string, or rate component dict) into a percentage Decimal.
    e.g. 18 -> 18.0, "18%" -> 18.0, 0.18 -> 18.0, {"cgst": 9, "sgst": 9} -> 18.0, {"rate": 18.0} -> 18.0.
    """
    if val is None or val == "":
        return None
    if isinstance(val, dict):
        for rate_key in ("rate", "tax_rate", "total", "total_rate"):
            if rate_key in val and val[rate_key] is not None:
                return parse_tax_rate(val[rate_key])
        igst = parse_tax_rate(val.get("igst")) or Decimal("0.0")
        if igst > Decimal("0.0"):
            return igst
        cgst = parse_tax_rate(val.get("cgst")) or Decimal("0.0")
        sgst = parse_tax_rate(val.get("sgst")) or Decimal("0.0")
        utgst = parse_tax_rate(val.get("utgst") or val.get("ugst")) or Decimal("0.0")
        if cgst > Decimal("0.0") or sgst > Decimal("0.0") or utgst > Decimal("0.0"):
            return cgst + sgst + utgst
        return None

    clean = str(val).strip().replace("%", "").strip()
    d = parse_decimal_safe(clean)
    if d is None:
        return None
    # If expressed as fraction (e.g. 0.18 for 18%)
    if Decimal("0.0") < d <= Decimal("1.0"):
        return round_monetary(d * Decimal("100.0"))
    return d


class TaxDifferenceCalculator:
    """
    Deterministic calculator for statutory tax rate mismatches.
    Enforces strict mathematical accuracy and transparent explainability.
    """

    def calculate(
        self,
        invoice_id: str,
        taxable_value: Optional[Union[Decimal, float, str, int]],
        recorded_rate: Optional[Any],
        expected_rate: Optional[Any],
        invoice_date: Optional[date] = None,
        counterparty_id: str = "",
        counterparty_name: str = "",
        rule_id: str = "TAX_001",
        rule_category: str = "TAX",
        tax_type: Optional[str] = None,  # "INTRA_STATE" or "INTER_STATE"
        recorded_components: Optional[Dict[str, Any]] = None,
        expected_components: Optional[Dict[str, Any]] = None,
    ) -> FinancialImpact:
        """
        Calculate potential tax exposure from rate discrepancies.
        """
        taxable_dec = parse_decimal_safe(taxable_value)
        rec_rate_dec = parse_tax_rate(recorded_rate)
        exp_rate_dec = parse_tax_rate(expected_rate)

        # 1. Missing data handling
        required_missing: List[str] = []
        if taxable_dec is None or taxable_dec <= Decimal("0.00"):
            required_missing.append("taxable_value")
        if rec_rate_dec is None:
            required_missing.append("recorded_tax_rate")
        if exp_rate_dec is None:
            required_missing.append("expected_tax_rate")

        if required_missing:
            return FinancialImpact(
                impact_id=f"IMP-{invoice_id}-{rule_id}",
                invoice_id=invoice_id,
                invoice_date=invoice_date,
                counterparty_id=counterparty_id,
                counterparty_name=counterparty_name,
                rule_id=rule_id,
                rule_category=rule_category,
                impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
                calculation_status=CalculationStatus.UNDETERMINED,
                direction=ImpactDirection.NOT_APPLICABLE,
                taxable_value=taxable_dec,
                recorded_rate=rec_rate_dec,
                expected_rate=exp_rate_dec,
                potential_exposure=None,
                currency="INR",
                calculation_basis="Calculation aborted due to missing prerequisite financial data.",
                reason=f"Prerequisite inputs missing: {', '.join(required_missing)}.",
                required_data=required_missing,
                evidence={
                    "invoice_id": invoice_id,
                    "taxable_value": float(taxable_dec) if taxable_dec else None,
                    "recorded_rate": float(rec_rate_dec) if rec_rate_dec else None,
                    "expected_rate": float(exp_rate_dec) if exp_rate_dec else None,
                    "missing_fields": required_missing,
                },
            )

        # 2. Rate and Tax Calculation
        rec_tax = round_monetary(taxable_dec * (rec_rate_dec / Decimal("100.00")))
        exp_tax = round_monetary(taxable_dec * (exp_rate_dec / Decimal("100.00")))
        tax_diff = abs(rec_tax - exp_tax)
        potential_exposure = tax_diff

        # 3. Direction of Impact
        if rec_rate_dec > exp_rate_dec:
            direction = ImpactDirection.OVERCHARGED_TAX
            dir_desc = f"Tax was overcharged by {rec_rate_dec - exp_rate_dec}% (Recorded {rec_rate_dec}% vs Expected {exp_rate_dec}%)."
        elif rec_rate_dec < exp_rate_dec:
            direction = ImpactDirection.UNDERCHARGED_TAX
            dir_desc = f"Tax was undercharged by {exp_rate_dec - rec_rate_dec}% (Recorded {rec_rate_dec}% vs Expected {exp_rate_dec}%)."
        else:
            direction = ImpactDirection.NO_TAX_DIFFERENCE
            dir_desc = "Recorded rate matches expected statutory rate (0% delta)."
            potential_exposure = Decimal("0.00")

        calc_basis = (
            f"Taxable Value INR {taxable_dec:,.2f} × |{rec_rate_dec}% - {exp_rate_dec}%| "
            f"= INR {tax_diff:,.2f} ({direction.value})"
        )

        # 4. Component-Level Split (if applicable)
        is_interstate = (tax_type == "INTER_STATE") or (
            recorded_components and parse_tax_rate(recorded_components.get("igst"))
        )
        is_ut_intra = (tax_type in ("UT_INTRA_STATE", "INTRA_UT")) or (
            recorded_components and parse_tax_rate(recorded_components.get("utgst") or recorded_components.get("ugst"))
        )

        rec_cgst, exp_cgst, cgst_diff = None, None, None
        rec_sgst, exp_sgst, sgst_diff = None, None, None
        rec_utgst, exp_utgst, utgst_diff = None, None, None
        rec_igst, exp_igst, igst_diff = None, None, None

        if is_interstate:
            rec_igst = rec_tax
            exp_igst = exp_tax
            igst_diff = tax_diff
        elif is_ut_intra:
            # Intra-UT: 50% CGST + 50% UTGST
            rec_cgst = round_monetary(rec_tax / Decimal("2.00"))
            rec_utgst = rec_tax - rec_cgst
            exp_cgst = round_monetary(exp_tax / Decimal("2.00"))
            exp_utgst = exp_tax - exp_cgst
            cgst_diff = abs(rec_cgst - exp_cgst)
            utgst_diff = abs(rec_utgst - exp_utgst)
        else:
            # Intra-state: 50% CGST + 50% SGST
            rec_cgst = round_monetary(rec_tax / Decimal("2.00"))
            rec_sgst = rec_tax - rec_cgst
            exp_cgst = round_monetary(exp_tax / Decimal("2.00"))
            exp_sgst = exp_tax - exp_cgst
            cgst_diff = abs(rec_cgst - exp_cgst)
            sgst_diff = abs(rec_sgst - exp_sgst)

        evidence = {
            "invoice_id": invoice_id,
            "taxable_value": float(taxable_dec),
            "recorded_rate": float(rec_rate_dec),
            "expected_rate": float(exp_rate_dec),
            "recorded_tax": float(rec_tax),
            "expected_tax": float(exp_tax),
            "tax_difference": float(tax_diff),
            "direction": direction.value,
            "direction_description": dir_desc,
            "is_interstate": bool(is_interstate),
            "is_ut_intra": bool(is_ut_intra),
            "formula": calc_basis,
        }

        return FinancialImpact(
            impact_id=f"IMP-{invoice_id}-{rule_id}",
            invoice_id=invoice_id,
            invoice_date=invoice_date,
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            rule_id=rule_id,
            rule_category=rule_category,
            impact_type=FinancialImpactType.TAX_RATE_DIFFERENCE,
            calculation_status=CalculationStatus.CALCULATED,
            direction=direction,
            taxable_value=taxable_dec,
            recorded_rate=rec_rate_dec,
            expected_rate=exp_rate_dec,
            recorded_tax=rec_tax,
            expected_tax=exp_tax,
            tax_difference=tax_diff,
            potential_exposure=potential_exposure,
            recorded_cgst=rec_cgst,
            expected_cgst=exp_cgst,
            cgst_difference=cgst_diff,
            recorded_sgst=rec_sgst,
            expected_sgst=exp_sgst,
            sgst_difference=sgst_diff,
            recorded_utgst=rec_utgst,
            expected_utgst=exp_utgst,
            utgst_difference=utgst_diff,
            recorded_igst=rec_igst,
            expected_igst=exp_igst,
            igst_difference=igst_diff,
            currency="INR",
            calculation_basis=calc_basis,
            confidence=1.0,
            evidence=evidence,
        )

    def calculate_tax_difference(
        self,
        taxable_value: Optional[Union[Decimal, float, str, int]],
        recorded_rate: Optional[Any],
        expected_rate: Optional[Any],
        is_interstate: bool = False,
    ) -> Dict[str, Any]:
        """
        Convenience method returning calculation details as a dictionary.
        """
        impact = self.calculate(
            invoice_id="TEMP",
            taxable_value=taxable_value,
            recorded_rate=recorded_rate,
            expected_rate=expected_rate,
            tax_type="INTER_STATE" if is_interstate else "INTRA_STATE",
        )
        return {
            "calculation_status": impact.calculation_status,
            "direction": impact.direction,
            "potential_exposure": impact.potential_exposure or Decimal("0.00"),
            "rate_difference_pct": impact.rate_difference_pct or Decimal("0.00"),
            "recorded_tax_amount": impact.recorded_tax,
            "expected_tax_amount": impact.expected_tax,
            "required_data": impact.required_data,
            "components": {
                "cgst_difference": impact.cgst_difference or Decimal("0.00"),
                "sgst_difference": impact.sgst_difference or Decimal("0.00"),
                "utgst_difference": impact.utgst_difference or Decimal("0.00"),
                "ugst_difference": impact.utgst_difference or Decimal("0.00"),
                "igst_difference": impact.igst_difference or Decimal("0.00"),
            },
            "impact": impact,
        }
