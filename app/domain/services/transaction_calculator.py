"""
UC15 GST Compliance Agent — Canonical Transaction Calculator & Sanitizer Service
Provides unified calculation logic for total_tax, invoice_total, effective_tax_rate,
and E-Way Bill status sanitization across all data layers.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Tuple, Any

VALID_EWAY_STATUSES = {
    "GENERATED",
    "NOT_GENERATED",
    "NOT_REQUIRED",
    "UNKNOWN",
    "PENDING",
    "CANCELLED",
    "EXPIRED",
    "ACTIVE",
    "IN_TRANSIT",
}

def parse_decimal_safe(val: Any) -> Decimal:
    """Safely parse input to Decimal, defaulting to Decimal('0.00')."""
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, Decimal):
        return val
    try:
        cleaned = str(val).strip().replace(",", "")
        if not cleaned or cleaned == "-":
            return Decimal("0.00")
        return Decimal(cleaned)
    except Exception:
        return Decimal("0.00")


def sanitize_eway_bill_status(raw_status: Any, taxable_value: Decimal = Decimal("0.00"), threshold: Decimal = Decimal("50000.00")) -> str:
    """
    Sanitize eway_bill_status string.
    Normalizes numeric status leaks to 'UNKNOWN' and valid status classifications.
    Does NOT decide statutory threshold applicability (left to G5 rule engine).
    """
    status, _ = sanitize_eway_bill_status_with_issue(raw_status)
    return status


def sanitize_eway_bill_status_with_issue(raw_status: Any) -> Tuple[str, Optional[str]]:
    """
    Sanitize eway_bill_status string and return (normalized_status, data_quality_issue).
    """
    if raw_status is None:
        return ("", None)

    raw_str = str(raw_status).strip().upper()
    cleaned_num = raw_str.replace(",", "").replace(".", "", 1)
    if cleaned_num.isdigit() or (cleaned_num.startswith("-") and cleaned_num[1:].isdigit()):
        return ("UNKNOWN", "NUMERIC_EWB_STATUS")

    if raw_str in VALID_EWAY_STATUSES:
        return (raw_str, None)

    if "GEN" in raw_str:
        return ("GENERATED", None)
    if "PEND" in raw_str or "MISS" in raw_str:
        return ("PENDING", None)
    if "CANCEL" in raw_str:
        return ("CANCELLED", None)
    if "EXP" in raw_str:
        return ("EXPIRED", None)

    if raw_str in ("NONE", "NO", "FALSE", "N/A", ""):
        return ("", None)

    return ("UNKNOWN", "INVALID_EWB_STATUS_STRING")


def compute_canonical_financials(
    taxable_value: Any,
    cgst_rate: Any = Decimal("0.00"),
    sgst_rate: Any = Decimal("0.00"),
    utgst_rate: Any = Decimal("0.00"),
    igst_rate: Any = Decimal("0.00"),
    cess_rate: Any = Decimal("0.00"),
    cgst_amount: Optional[Any] = None,
    sgst_amount: Optional[Any] = None,
    utgst_amount: Optional[Any] = None,
    igst_amount: Optional[Any] = None,
    cess_amount: Optional[Any] = None,
    total_tax: Optional[Any] = None,
    total_amount: Optional[Any] = None,
    expected_tax_rate: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Computes normalized financial amounts and rates using canonical rules:
    - cgst_amount = taxable_value * (cgst_rate / 100) if not provided
    - sgst_amount = taxable_value * (sgst_rate / 100) if not provided
    - utgst_amount = taxable_value * (utgst_rate / 100) if not provided
    - igst_amount = taxable_value * (igst_rate / 100) if not provided
    - cess_amount = taxable_value * (cess_rate / 100) if not provided
    - total_tax = cgst_amount + sgst_amount + utgst_amount + igst_amount + cess_amount
    - invoice_total = taxable_value + total_tax
    - effective_tax_rate = (total_tax / taxable_value) * 100 when taxable_value > 0
    - expected_tax = taxable_value * (expected_tax_rate / 100) when expected_tax_rate provided
    - tax_difference = abs(total_tax - expected_tax)
    """
    taxable_dec = max(Decimal("0.00"), parse_decimal_safe(taxable_value))
    cgst_r = max(Decimal("0.00"), parse_decimal_safe(cgst_rate))
    sgst_r = max(Decimal("0.00"), parse_decimal_safe(sgst_rate))
    utgst_r = max(Decimal("0.00"), parse_decimal_safe(utgst_rate))
    igst_r = max(Decimal("0.00"), parse_decimal_safe(igst_rate))
    cess_r = max(Decimal("0.00"), parse_decimal_safe(cess_rate))

    # Derive component tax amounts if not explicitly given
    if cgst_amount is not None and parse_decimal_safe(cgst_amount) > Decimal("0.00"):
        cgst_a = parse_decimal_safe(cgst_amount)
    else:
        cgst_a = (taxable_dec * cgst_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if sgst_amount is not None and parse_decimal_safe(sgst_amount) > Decimal("0.00"):
        sgst_a = parse_decimal_safe(sgst_amount)
    else:
        sgst_a = (taxable_dec * sgst_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if utgst_amount is not None and parse_decimal_safe(utgst_amount) > Decimal("0.00"):
        utgst_a = parse_decimal_safe(utgst_amount)
    else:
        utgst_a = (taxable_dec * utgst_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if igst_amount is not None and parse_decimal_safe(igst_amount) > Decimal("0.00"):
        igst_a = parse_decimal_safe(igst_amount)
    else:
        igst_a = (taxable_dec * igst_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if cess_amount is not None and parse_decimal_safe(cess_amount) > Decimal("0.00"):
        cess_a = parse_decimal_safe(cess_amount)
    else:
        cess_a = (taxable_dec * cess_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Compute component tax sum
    component_tax_sum = cgst_a + sgst_a + utgst_a + igst_a + cess_a

    # Evaluate total tax passed vs component sum
    passed_tax = parse_decimal_safe(total_tax) if total_tax is not None else None
    passed_total = parse_decimal_safe(total_amount) if total_amount is not None else None

    # Handle cases where total_amount passed was actually less than taxable_value (passed tax instead of grand total)
    if passed_total is not None and passed_total > Decimal("0.00") and passed_total < taxable_dec:
        # passed_total was actually tax amount!
        actual_total_tax = passed_total
    elif passed_tax is not None and passed_tax > Decimal("0.00"):
        actual_total_tax = passed_tax
    elif component_tax_sum > Decimal("0.00"):
        actual_total_tax = component_tax_sum
    elif passed_total is not None and passed_total >= taxable_dec:
        actual_total_tax = passed_total - taxable_dec
    else:
        actual_total_tax = Decimal("0.00")

    # Final grand total is ALWAYS taxable_value + actual_total_tax
    actual_invoice_total = taxable_dec + actual_total_tax

    # Effective tax rate
    if taxable_dec > Decimal("0.00"):
        effective_tax_rate = ((actual_total_tax / taxable_dec) * Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        effective_tax_rate = Decimal("0.00")

    # Expected tax computation if expected_tax_rate provided
    if expected_tax_rate is not None:
        expected_r = max(Decimal("0.00"), parse_decimal_safe(expected_tax_rate))
        expected_tax = (taxable_dec * expected_r / Decimal("100.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tax_difference = abs(actual_total_tax - expected_tax)
    else:
        expected_r = None
        expected_tax = None
        tax_difference = None

    return {
        "taxable_value": taxable_dec,
        "cgst_rate": cgst_r,
        "sgst_rate": sgst_r,
        "utgst_rate": utgst_r,
        "ugst_rate": utgst_r,
        "igst_rate": igst_r,
        "cess_rate": cess_r,
        "cgst_amount": cgst_a,
        "sgst_amount": sgst_a,
        "utgst_amount": utgst_a,
        "ugst_amount": utgst_a,
        "igst_amount": igst_a,
        "cess_amount": cess_a,
        "total_tax": actual_total_tax,
        "invoice_total": actual_invoice_total,
        "reported_total_tax": passed_tax,
        "reported_total_amount": passed_total,
        "effective_tax_rate": effective_tax_rate,
        "expected_tax_rate": expected_r,
        "expected_tax": expected_tax,
        "tax_difference": tax_difference,
    }

