"""
UC15 GST Compliance Agent — Central Deterministic GST Tax Treatment Engine
Single Source of Truth for GST Jurisdiction, Tax Treatment, Component Heads, Rates, Amounts, and Validations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


# -----------------------------------------------------------------------------
# Canonical Enumerations
# -----------------------------------------------------------------------------

class TaxJurisdiction(str, Enum):
    """Statutory Tax Jurisdiction classification."""
    INTRA_STATE = "INTRA_STATE"              # Normal State / UT with legislature intra-supply (CGST + SGST)
    UT_INTRA_STATE = "UT_INTRA_STATE"        # Union Territory without legislature intra-supply (CGST + UTGST)
    INTER_STATE = "INTER_STATE"              # Different States / UTs inter-supply (IGST)
    EXPORT = "EXPORT"                        # Outward supply outside India (Zero-rated / IGST)
    IMPORT = "IMPORT"                        # Inward supply from outside India (IGST / Customs)
    SEZ = "SEZ"                              # Special Economic Zone supply (Deemed Inter-State / Zero-rated)
    ZERO_RATED = "ZERO_RATED"                # Statutory zero-rated supply
    REVIEW = "REVIEW"                        # Insufficient / contradictory information; requires manual review
    UNKNOWN = "UNKNOWN"                      # Cannot determine jurisdiction


class TaxTreatmentType(str, Enum):
    """Statutory Tax Head Treatment structure."""
    CGST_SGST = "CGST_SGST"                  # CGST + SGST
    CGST_UTGST = "CGST_UTGST"                # CGST + UTGST
    IGST = "IGST"                            # IGST
    ZERO_RATED = "ZERO_RATED"                # Legitimate Zero-rated supply (0% tax or refund mechanism)
    EXEMPT = "EXEMPT"                        # Exempt / Nil-rated supply
    REVERSE_CHARGE = "REVERSE_CHARGE"        # Recipient liable to discharge tax under Section 9(3)/9(4)
    REVIEW = "REVIEW"                        # Under review
    UNKNOWN = "UNKNOWN"


class TaxMismatchType(str, Enum):
    """Categorized tax discrepancy classifications."""
    RATE_MISMATCH = "RATE_MISMATCH"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    TAX_HEAD_MISMATCH = "TAX_HEAD_MISMATCH"
    TAX_CALCULATION_MISMATCH = "TAX_CALCULATION_MISMATCH"
    INVOICE_TOTAL_MISMATCH = "INVOICE_TOTAL_MISMATCH"
    INVALID_TAX_COMBINATION = "INVALID_TAX_COMBINATION"
    UTGST_MISSING = "UTGST_MISSING"
    IGST_APPLIED_INTRA_STATE = "IGST_APPLIED_INTRA_STATE"
    CGST_SGST_APPLIED_INTER_STATE = "CGST_SGST_APPLIED_INTER_STATE"
    SGST_APPLIED_WHEN_UTGST_REQUIRED = "SGST_APPLIED_WHEN_UTGST_REQUIRED"
    POS_DATA_INSUFFICIENT = "POS_DATA_INSUFFICIENT"


# -----------------------------------------------------------------------------
# Precision Decimal Utilities
# -----------------------------------------------------------------------------

def round_monetary(val: Decimal) -> Decimal:
    """Round to 2 decimal places using standard statutory ROUND_HALF_UP."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_decimal_safe(val: Any, default: Decimal = Decimal("0.00")) -> Decimal:
    """Safely parse arbitrary input into Decimal, returning default on invalid input."""
    if val is None or val == "":
        return default
    if isinstance(val, Decimal):
        return val
    try:
        clean_str = str(val).strip().replace(",", "").replace("₹", "").replace("INR", "").replace("Rs.", "").strip()
        if not clean_str or clean_str in ("-", "null", "none", "nan", "nil"):
            return default
        return Decimal(clean_str)
    except (InvalidOperation, ValueError):
        return default


def parse_rate_percentage(val: Any) -> Decimal:
    """
    Safely parse rate representation into a canonical percentage Decimal.
    9 -> Decimal("9.00")
    9% -> Decimal("9.00")
    0.09 -> Decimal("9.00") (fraction)
    0.0900 -> Decimal("9.00")
    18.0 -> Decimal("18.00")
    """
    if val is None or val == "":
        return Decimal("0.00")
    if isinstance(val, (int, float, Decimal, str)):
        clean_str = str(val).strip().replace("%", "").strip()
        d = parse_decimal_safe(clean_str)
        # If expressed as fraction (e.g. 0.05, 0.09, 0.12, 0.18, 0.28)
        if Decimal("0.00") < d <= Decimal("1.00"):
            return round_monetary(d * Decimal("100.00"))
        return round_monetary(d)
    return Decimal("0.00")


# -----------------------------------------------------------------------------
# Comprehensive Official State & UT Master Catalog
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class StateJurisdictionInfo:
    code: str
    name: str
    state_or_ut: str     # "STATE" | "UT"
    has_legislature: bool

    @property
    def is_ut_without_legislature(self) -> bool:
        return self.state_or_ut == "UT" and not self.has_legislature


OFFICIAL_STATE_CATALOG: Dict[str, StateJurisdictionInfo] = {
    "01": StateJurisdictionInfo("01", "Jammu and Kashmir", "UT", True),
    "02": StateJurisdictionInfo("02", "Himachal Pradesh", "STATE", True),
    "03": StateJurisdictionInfo("03", "Punjab", "STATE", True),
    "04": StateJurisdictionInfo("04", "Chandigarh", "UT", False),
    "05": StateJurisdictionInfo("05", "Uttarakhand", "STATE", True),
    "06": StateJurisdictionInfo("06", "Haryana", "STATE", True),
    "07": StateJurisdictionInfo("07", "Delhi", "UT", True),
    "08": StateJurisdictionInfo("08", "Rajasthan", "STATE", True),
    "09": StateJurisdictionInfo("09", "Uttar Pradesh", "STATE", True),
    "10": StateJurisdictionInfo("10", "Bihar", "STATE", True),
    "11": StateJurisdictionInfo("11", "Sikkim", "STATE", True),
    "12": StateJurisdictionInfo("12", "Arunachal Pradesh", "STATE", True),
    "13": StateJurisdictionInfo("13", "Nagaland", "STATE", True),
    "14": StateJurisdictionInfo("14", "Manipur", "STATE", True),
    "15": StateJurisdictionInfo("15", "Mizoram", "STATE", True),
    "16": StateJurisdictionInfo("16", "Tripura", "STATE", True),
    "17": StateJurisdictionInfo("17", "Meghalaya", "STATE", True),
    "18": StateJurisdictionInfo("18", "Assam", "STATE", True),
    "19": StateJurisdictionInfo("19", "West Bengal", "STATE", True),
    "20": StateJurisdictionInfo("20", "Jharkhand", "STATE", True),
    "21": StateJurisdictionInfo("21", "Odisha", "STATE", True),
    "22": StateJurisdictionInfo("22", "Chhattisgarh", "STATE", True),
    "23": StateJurisdictionInfo("23", "Madhya Pradesh", "STATE", True),
    "24": StateJurisdictionInfo("24", "Gujarat", "STATE", True),
    "26": StateJurisdictionInfo("26", "Dadra and Nagar Haveli and Daman and Diu", "UT", False),
    "27": StateJurisdictionInfo("27", "Maharashtra", "STATE", True),
    "29": StateJurisdictionInfo("29", "Karnataka", "STATE", True),
    "30": StateJurisdictionInfo("30", "Goa", "STATE", True),
    "31": StateJurisdictionInfo("31", "Lakshadweep", "UT", False),
    "32": StateJurisdictionInfo("32", "Kerala", "STATE", True),
    "33": StateJurisdictionInfo("33", "Tamil Nadu", "STATE", True),
    "34": StateJurisdictionInfo("34", "Puducherry", "UT", True),
    "35": StateJurisdictionInfo("35", "Andaman and Nicobar Islands", "UT", False),
    "36": StateJurisdictionInfo("36", "Telangana", "STATE", True),
    "37": StateJurisdictionInfo("37", "Andhra Pradesh", "STATE", True),
    "38": StateJurisdictionInfo("38", "Ladakh", "UT", False),
    "97": StateJurisdictionInfo("97", "Other Territory", "UT", False),
}


def lookup_state_info(val: Optional[str]) -> Optional[StateJurisdictionInfo]:
    """Look up StateJurisdictionInfo by 2-digit code or state name."""
    if not val:
        return None
    s = str(val).strip()
    if s.isdigit() and len(s) <= 2:
        code = s.zfill(2)
        return OFFICIAL_STATE_CATALOG.get(code)

    # Check if string starts with 2-digit code
    if len(s) >= 2 and s[:2].isdigit():
        code = s[:2]
        if code in OFFICIAL_STATE_CATALOG:
            return OFFICIAL_STATE_CATALOG[code]

    # Name lookup (case-insensitive substring match)
    s_lower = s.lower().replace("sez unit", "").replace("sez developer", "").replace("sez", "").strip()
    for info in OFFICIAL_STATE_CATALOG.values():
        if info.name.lower() == s_lower:
            return info
    for info in OFFICIAL_STATE_CATALOG.values():
        if info.name.lower() in s_lower or s_lower in info.name.lower():
            return info
    return None


# -----------------------------------------------------------------------------
# Structured Tax Treatment Result Contract
# -----------------------------------------------------------------------------

@dataclass
class TaxTreatmentResult:
    """Authoritative, deterministic GST tax treatment and validation output."""
    # Identification & Facts
    invoice_id: str
    taxable_value: Decimal
    jurisdiction: TaxJurisdiction
    treatment: TaxTreatmentType
    expected_tax_head: str                   # "CGST_SGST" | "CGST_UTGST" | "IGST" | "ZERO_RATED" | "REVIEW"

    # Expected Rates
    expected_cgst_rate: Decimal
    expected_sgst_rate: Decimal
    expected_utgst_rate: Decimal
    expected_igst_rate: Decimal
    expected_cess_rate: Decimal
    expected_total_rate: Decimal

    # Expected Amounts
    expected_cgst_amount: Decimal
    expected_sgst_amount: Decimal
    expected_utgst_amount: Decimal
    expected_igst_amount: Decimal
    expected_cess_amount: Decimal
    expected_total_tax: Decimal
    expected_invoice_total: Decimal

    # Applied Rates
    applied_cgst_rate: Decimal
    applied_sgst_rate: Decimal
    applied_utgst_rate: Decimal
    applied_igst_rate: Decimal
    applied_cess_rate: Decimal
    applied_total_rate: Decimal

    # Applied / Reported Amounts
    applied_cgst_amount: Decimal
    applied_sgst_amount: Decimal
    applied_utgst_amount: Decimal
    applied_igst_amount: Decimal
    applied_cess_amount: Decimal
    applied_total_tax: Decimal
    reported_invoice_total: Decimal

    # Differences & Compliance
    tax_difference: Decimal
    cgst_diff: Decimal
    sgst_diff: Decimal
    utgst_diff: Decimal
    igst_diff: Decimal
    cess_diff: Decimal

    is_compliant: bool
    rate_mismatch: bool
    amount_mismatch: bool
    tax_head_mismatch: bool
    tax_calculation_mismatch: bool
    invoice_total_mismatch: bool
    invalid_combination: bool
    mismatches: List[str] = field(default_factory=list)

    # Contextual Facts
    supplier_state: Optional[str] = None
    supplier_state_code: Optional[str] = None
    recipient_state: Optional[str] = None
    recipient_state_code: Optional[str] = None
    place_of_supply: str = ""
    pos_state_code: Optional[str] = None

    # Reverse Charge & Scope
    is_rcm: bool = False
    rcm_applicable: bool = False
    rcm_reason: Optional[str] = None
    tax_bearing_party: Optional[str] = None

    # Evidence & Explainability
    rationale: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    resolution_suggestion: Dict[str, Any] = field(default_factory=dict)

    # Backward Compatibility Aliases for UTGST / UGST
    @property
    def expected_ugst_rate(self) -> Decimal:
        return self.expected_utgst_rate

    @property
    def expected_ugst_amount(self) -> Decimal:
        return self.expected_utgst_amount

    @property
    def applied_ugst_rate(self) -> Decimal:
        return self.applied_utgst_rate

    @property
    def applied_ugst_amount(self) -> Decimal:
        return self.applied_utgst_amount

    @property
    def ugst_diff(self) -> Decimal:
        return self.utgst_diff

    @property
    def is_math_correct(self) -> bool:
        return not self.tax_calculation_mismatch

    @property
    def is_rate_correct(self) -> bool:
        return not self.rate_mismatch

    @property
    def is_invoice_total_correct(self) -> bool:
        return not self.invoice_total_mismatch

    @property
    def tax_jurisdiction(self) -> TaxJurisdiction:
        return self.jurisdiction

    @property
    def tax_treatment(self) -> TaxTreatmentType:
        return self.treatment

    @property
    def reported_total_amount(self) -> Decimal:
        return self.reported_invoice_total

    def to_dict(self) -> Dict[str, Any]:
        """Serialize into clean dictionary for API / UI / Case dossier consumption."""
        return {
            "invoice_id": self.invoice_id,
            "taxable_value": float(self.taxable_value),
            "jurisdiction": self.jurisdiction.value,
            "treatment": self.treatment.value,
            "expected_tax_head": self.expected_tax_head,
            "expected_rates": {
                "cgst": float(self.expected_cgst_rate),
                "sgst": float(self.expected_sgst_rate),
                "utgst": float(self.expected_utgst_rate),
                "ugst": float(self.expected_utgst_rate),
                "igst": float(self.expected_igst_rate),
                "cess": float(self.expected_cess_rate),
                "total": float(self.expected_total_rate),
            },
            "expected_amounts": {
                "cgst": float(self.expected_cgst_amount),
                "sgst": float(self.expected_sgst_amount),
                "utgst": float(self.expected_utgst_amount),
                "ugst": float(self.expected_utgst_amount),
                "igst": float(self.expected_igst_amount),
                "cess": float(self.expected_cess_amount),
                "total_tax": float(self.expected_total_tax),
                "invoice_total": float(self.expected_invoice_total),
            },
            "applied_rates": {
                "cgst": float(self.applied_cgst_rate),
                "sgst": float(self.applied_sgst_rate),
                "utgst": float(self.applied_utgst_rate),
                "ugst": float(self.applied_utgst_rate),
                "igst": float(self.applied_igst_rate),
                "cess": float(self.applied_cess_rate),
                "total": float(self.applied_total_rate),
            },
            "applied_amounts": {
                "cgst": float(self.applied_cgst_amount),
                "sgst": float(self.applied_sgst_amount),
                "utgst": float(self.applied_utgst_amount),
                "ugst": float(self.applied_utgst_amount),
                "igst": float(self.applied_igst_amount),
                "cess": float(self.applied_cess_amount),
                "total_tax": float(self.applied_total_tax),
                "invoice_total": float(self.reported_invoice_total),
            },
            "tax_difference": float(self.tax_difference),
            "component_differences": {
                "cgst": float(self.cgst_diff),
                "sgst": float(self.sgst_diff),
                "utgst": float(self.utgst_diff),
                "ugst": float(self.utgst_diff),
                "igst": float(self.igst_diff),
                "cess": float(self.cess_diff),
            },
            "is_compliant": self.is_compliant,
            "rate_mismatch": self.rate_mismatch,
            "amount_mismatch": self.amount_mismatch,
            "tax_head_mismatch": self.tax_head_mismatch,
            "tax_calculation_mismatch": self.tax_calculation_mismatch,
            "invoice_total_mismatch": self.invoice_total_mismatch,
            "invalid_combination": self.invalid_combination,
            "mismatches": self.mismatches,
            "supplier_state": self.supplier_state,
            "recipient_state": self.recipient_state,
            "place_of_supply": self.place_of_supply,
            "is_rcm": self.is_rcm,
            "rcm_applicable": self.rcm_applicable,
            "rcm_reason": self.rcm_reason,
            "tax_bearing_party": self.tax_bearing_party,
            "rationale": self.rationale,
            "evidence": self.evidence,
            "resolution_suggestion": self.resolution_suggestion,
        }


# -----------------------------------------------------------------------------
# Central Deterministic Engine Implementation
# -----------------------------------------------------------------------------

class TaxTreatmentEngine:
    """
    Deterministic engine evaluating transaction facts to establish statutory GST treatment,
    applicable tax heads, rates, expected amounts, and discrepancy classifications.
    Single Source of Truth consumed across G3, G4, Decision Engine, UI, and AI layers.
    """

    @classmethod
    def evaluate_transaction(
        cls,
        invoice_id: str = "",
        taxable_value: Union[Decimal, float, str, int] = Decimal("0.00"),
        applicable_gst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applicable_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_cgst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_sgst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_utgst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_ugst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_igst_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_cess_rate: Optional[Union[Decimal, float, str, int]] = None,
        applied_cgst_amount: Optional[Union[Decimal, float, str, int]] = None,
        applied_sgst_amount: Optional[Union[Decimal, float, str, int]] = None,
        applied_utgst_amount: Optional[Union[Decimal, float, str, int]] = None,
        applied_ugst_amount: Optional[Union[Decimal, float, str, int]] = None,
        applied_igst_amount: Optional[Union[Decimal, float, str, int]] = None,
        applied_cess_amount: Optional[Union[Decimal, float, str, int]] = None,
        reported_total_tax: Optional[Union[Decimal, float, str, int]] = None,
        reported_invoice_total: Optional[Union[Decimal, float, str, int]] = None,
        reported_total_amount: Optional[Union[Decimal, float, str, int]] = None,
        supplier_gstin: Optional[str] = None,
        supplier_state: Optional[str] = None,
        recipient_gstin: Optional[str] = None,
        recipient_state: Optional[str] = None,
        place_of_supply: Optional[str] = None,
        direction: str = "AR",
        invoice_type: str = "B2B",
        is_rcm: Optional[bool] = None,
        is_foreign_supplier: bool = False,
        is_foreign_buyer: bool = False,
        reference_service: Optional[Any] = None,
        tolerance_rate: Decimal = Decimal("0.01"),
        tolerance_amount: Decimal = Decimal("0.05"),
        **kwargs: Any,
    ) -> TaxTreatmentResult:
        """
        Evaluate full transaction facts and return deterministic TaxTreatmentResult.
        """
        if "tolerance" in kwargs and kwargs["tolerance"] is not None:
            tolerance_rate = parse_decimal_safe(kwargs["tolerance"])

        eff_applicable_rate = applicable_gst_rate if applicable_gst_rate is not None else applicable_rate
        eff_reported_total = reported_invoice_total if reported_invoice_total is not None else reported_total_amount
        taxable_dec = round_monetary(max(Decimal("0.00"), parse_decimal_safe(taxable_value)))

        # Clean Rates
        cgst_r = parse_rate_percentage(applied_cgst_rate)
        sgst_r = parse_rate_percentage(applied_sgst_rate)
        # Handle utgst with ugst alias
        raw_utgst = applied_utgst_rate if applied_utgst_rate is not None else applied_ugst_rate
        utgst_r = parse_rate_percentage(raw_utgst)
        igst_r = parse_rate_percentage(applied_igst_rate)
        cess_r = parse_rate_percentage(applied_cess_rate)
        applied_total_r = cgst_r + sgst_r + utgst_r + igst_r + cess_r

        # Clean Amounts
        cgst_a = round_monetary(parse_decimal_safe(applied_cgst_amount)) if applied_cgst_amount is not None else round_monetary(taxable_dec * cgst_r / Decimal("100.00"))
        sgst_a = round_monetary(parse_decimal_safe(applied_sgst_amount)) if applied_sgst_amount is not None else round_monetary(taxable_dec * sgst_r / Decimal("100.00"))
        raw_ut_a = applied_utgst_amount if applied_utgst_amount is not None else applied_ugst_amount
        utgst_a = round_monetary(parse_decimal_safe(raw_ut_a)) if raw_ut_a is not None else round_monetary(taxable_dec * utgst_r / Decimal("100.00"))
        igst_a = round_monetary(parse_decimal_safe(applied_igst_amount)) if applied_igst_amount is not None else round_monetary(taxable_dec * igst_r / Decimal("100.00"))
        cess_a = round_monetary(parse_decimal_safe(applied_cess_amount)) if applied_cess_amount is not None else round_monetary(taxable_dec * cess_r / Decimal("100.00"))

        computed_component_tax = cgst_a + sgst_a + utgst_a + igst_a + cess_a

        if reported_total_tax is not None and str(reported_total_tax).strip() != "":
            actual_total_tax = round_monetary(parse_decimal_safe(reported_total_tax))
        else:
            actual_total_tax = computed_component_tax

        if eff_reported_total is not None and str(eff_reported_total).strip() != "":
            actual_invoice_total = round_monetary(parse_decimal_safe(eff_reported_total))
        else:
            actual_invoice_total = taxable_dec + actual_total_tax

        # ---------------------------------------------------------------------
        # 1. Resolve Parties and Jurisdictions
        # ---------------------------------------------------------------------
        dir_clean = str(direction or "AR").strip().upper()
        inv_type_clean = str(invoice_type or "B2B").strip().upper()

        supp_g = str(supplier_gstin or "").strip().upper()
        rec_g = str(recipient_gstin or "").strip().upper()
        pos_raw = str(place_of_supply or "").strip()

        # Derive State Info
        supp_info = lookup_state_info(supp_g[:2]) if (len(supp_g) >= 2 and supp_g[:2].isdigit()) else lookup_state_info(supplier_state)
        rec_info = lookup_state_info(rec_g[:2]) if (len(rec_g) >= 2 and rec_g[:2].isdigit()) else lookup_state_info(recipient_state)
        pos_info = lookup_state_info(pos_raw)

        # Fallback for entity's own state if omitted: default our company location to Maharashtra (27)
        if not supp_info and dir_clean == "AR":
            supp_info = OFFICIAL_STATE_CATALOG["27"]
        if not rec_info and dir_clean == "AP":
            rec_info = OFFICIAL_STATE_CATALOG["27"]

        supp_state_name = supp_info.name if supp_info else (supplier_state or "")
        supp_state_code = supp_info.code if supp_info else (supp_g[:2] if len(supp_g) >= 2 and supp_g[:2].isdigit() else None)

        rec_state_name = rec_info.name if rec_info else (recipient_state or "")
        rec_state_code = rec_info.code if rec_info else (rec_g[:2] if len(rec_g) >= 2 and rec_g[:2].isdigit() else None)

        pos_state_name = pos_info.name if pos_info else pos_raw
        pos_state_code = pos_info.code if pos_info else None

        # ---------------------------------------------------------------------
        # 2. Determine Jurisdiction and Scope
        # ---------------------------------------------------------------------
        mismatches: List[str] = []
        is_sez = inv_type_clean in ("SEZ", "SEZ_DEVELOPER", "SEZ_UNIT") or "SEZ" in pos_raw.upper()
        is_export = is_foreign_buyer or inv_type_clean in ("EXPORT", "DEEMED_EXPORT")
        is_import = is_foreign_supplier or inv_type_clean == "IMPORT"

        jurisdiction = TaxJurisdiction.UNKNOWN
        treatment = TaxTreatmentType.UNKNOWN
        expected_head = "REVIEW"

        if not pos_raw or pos_raw.lower() in ("unknown", "null", "none", "", "-"):
            jurisdiction = TaxJurisdiction.REVIEW
            treatment = TaxTreatmentType.REVIEW
            expected_head = "REVIEW"
            mismatches.append(TaxMismatchType.POS_DATA_INSUFFICIENT.value)
            rationale = "Place of Supply is missing or unresolvable; cannot deduce statutory tax jurisdiction without fabricating facts."
        elif is_export:
            jurisdiction = TaxJurisdiction.EXPORT
            treatment = TaxTreatmentType.ZERO_RATED
            expected_head = "ZERO_RATED"
            rationale = f"Export transaction outside India to recipient in {rec_state_name or 'foreign destination'}: zero-rated inter-state supply."
        elif is_import:
            jurisdiction = TaxJurisdiction.IMPORT
            treatment = TaxTreatmentType.IGST
            expected_head = "IGST"
            rationale = f"Import of goods/services from foreign supplier into {pos_state_name}: subject to IGST under Section 7(2) IGST Act."
        elif is_sez:
            # Under Section 7(5)(b) of the IGST Act, 2017, supply to or by an SEZ is deemed Inter-State
            jurisdiction = TaxJurisdiction.SEZ
            treatment = TaxTreatmentType.IGST
            expected_head = "IGST"
            rationale = f"Supply to/by Special Economic Zone (SEZ) in {pos_state_name}: deemed inter-state supply under Section 7(5)(b) of IGST Act."
        else:
            # Domestic Supply
            # Statutory Rule: Compare Supplier State with Place of Supply (NOT Recipient State!)
            if not supp_info or not pos_info:
                # One of the states could not be resolved reliably
                # If text names match exactly:
                if supp_state_name and pos_state_name and supp_state_name.strip().lower() == pos_state_name.strip().lower():
                    is_same_jurisdiction = True
                    target_info = supp_info or pos_info
                else:
                    jurisdiction = TaxJurisdiction.REVIEW
                    treatment = TaxTreatmentType.REVIEW
                    expected_head = "REVIEW"
                    mismatches.append(TaxMismatchType.POS_DATA_INSUFFICIENT.value)
                    rationale = f"Could not verify state master record for Supplier ('{supp_state_name}') or Place of Supply ('{pos_state_name}')."
                    target_info = None
                    is_same_jurisdiction = False
            else:
                is_same_jurisdiction = supp_info.code == pos_info.code
                target_info = pos_info

            if jurisdiction != TaxJurisdiction.REVIEW:
                if is_same_jurisdiction and target_info:
                    # Intra-Jurisdiction Supply
                    if target_info.is_ut_without_legislature:
                        jurisdiction = TaxJurisdiction.UT_INTRA_STATE
                        treatment = TaxTreatmentType.CGST_UTGST
                        expected_head = "CGST_UTGST"
                        rationale = (
                            f"Supplier State ({supp_info.name if supp_info else supp_state_name}) and Place of Supply ({pos_info.name}) "
                            f"are within Union Territory of {target_info.name} (without legislative assembly). "
                            f"Statutory treatment under UTGST Act is CGST + UTGST."
                        )
                    else:
                        jurisdiction = TaxJurisdiction.INTRA_STATE
                        treatment = TaxTreatmentType.CGST_SGST
                        expected_head = "CGST_SGST"
                        legislature_note = f" (UT with legislative assembly under SGST Act)" if target_info.state_or_ut == "UT" else ""
                        rationale = (
                            f"Supplier State ({supp_info.name if supp_info else supp_state_name}) and Place of Supply ({pos_info.name}) "
                            f"are in the same state/UT{legislature_note}. "
                            f"Statutory treatment under CGST/SGST Acts is CGST + SGST."
                        )
                else:
                    # Inter-State Supply (Section 7 IGST Act)
                    jurisdiction = TaxJurisdiction.INTER_STATE
                    treatment = TaxTreatmentType.IGST
                    expected_head = "IGST"
                    s_name = supp_info.name if supp_info else supp_state_name
                    p_name = pos_info.name if pos_info else pos_state_name
                    rationale = (
                        f"Supplier State ({s_name}) differs from Place of Supply ({p_name}). "
                        f"Statutory treatment under Section 7 of IGST Act is Inter-State IGST."
                    )

        # ---------------------------------------------------------------------
        # 3. Applicable Rates and Expected Tax Breakdown
        # ---------------------------------------------------------------------
        if eff_applicable_rate is not None and str(eff_applicable_rate).strip() != "":
            app_rate_dec = parse_rate_percentage(eff_applicable_rate)
        else:
            # Fallback to sum of applied rates if not explicitly passed
            app_rate_dec = applied_total_r

        # Determine Expected Components
        exp_cgst_r = Decimal("0.00")
        exp_sgst_r = Decimal("0.00")
        exp_utgst_r = Decimal("0.00")
        exp_igst_r = Decimal("0.00")
        exp_cess_r = cess_r  # Cess preserved

        if treatment == TaxTreatmentType.CGST_SGST:
            exp_cgst_r = round_monetary(app_rate_dec / Decimal("2.00"))
            exp_sgst_r = app_rate_dec - exp_cgst_r
        elif treatment == TaxTreatmentType.CGST_UTGST:
            exp_cgst_r = round_monetary(app_rate_dec / Decimal("2.00"))
            exp_utgst_r = app_rate_dec - exp_cgst_r
        elif treatment in (TaxTreatmentType.IGST, TaxTreatmentType.ZERO_RATED):
            if treatment == TaxTreatmentType.ZERO_RATED and (cgst_r == 0 and sgst_r == 0 and igst_r == 0):
                exp_igst_r = Decimal("0.00")
            else:
                exp_igst_r = app_rate_dec
        elif treatment == TaxTreatmentType.REVIEW:
            # Under review: mirror applied to avoid false precision
            exp_cgst_r = cgst_r
            exp_sgst_r = sgst_r
            exp_utgst_r = utgst_r
            exp_igst_r = igst_r

        exp_total_r = exp_cgst_r + exp_sgst_r + exp_utgst_r + exp_igst_r + exp_cess_r

        # Calculate Expected Amounts with high-precision Decimal
        exp_cgst_a = round_monetary(taxable_dec * exp_cgst_r / Decimal("100.00"))
        exp_sgst_a = round_monetary(taxable_dec * exp_sgst_r / Decimal("100.00"))
        exp_utgst_a = round_monetary(taxable_dec * exp_utgst_r / Decimal("100.00"))
        exp_igst_a = round_monetary(taxable_dec * exp_igst_r / Decimal("100.00"))
        exp_cess_a = round_monetary(taxable_dec * exp_cess_r / Decimal("100.00"))

        exp_total_tax = exp_cgst_a + exp_sgst_a + exp_utgst_a + exp_igst_a + exp_cess_a
        exp_invoice_total = taxable_dec + exp_total_tax

        # ---------------------------------------------------------------------
        # 4. Incompatible Component Combination Validation
        # ---------------------------------------------------------------------
        has_cgst = cgst_r > Decimal("0.00") or cgst_a > Decimal("0.00")
        has_sgst = sgst_r > Decimal("0.00") or sgst_a > Decimal("0.00")
        has_utgst = utgst_r > Decimal("0.00") or utgst_a > Decimal("0.00")
        has_igst = igst_r > Decimal("0.00") or igst_a > Decimal("0.00")

        invalid_combination = False
        # Case 1: IGST with local taxes (CGST/SGST/UTGST)
        if has_igst and (has_cgst or has_sgst or has_utgst):
            invalid_combination = True
            mismatches.append(TaxMismatchType.INVALID_TAX_COMBINATION.value)
        # Case 2: SGST + UTGST together (only one local component is legally permitted)
        if has_sgst and has_utgst:
            invalid_combination = True
            mismatches.append(TaxMismatchType.INVALID_TAX_COMBINATION.value)
        # Case 3: CGST alone without local counterpart in intra-state
        if jurisdiction in (TaxJurisdiction.INTRA_STATE, TaxJurisdiction.UT_INTRA_STATE) and has_cgst and not (has_sgst or has_utgst):
            invalid_combination = True
            mismatches.append(TaxMismatchType.INVALID_TAX_COMBINATION.value)

        # ---------------------------------------------------------------------
        # 5. Tax Head & Structure Mismatch Detection
        # ---------------------------------------------------------------------
        tax_head_mismatch = False
        if jurisdiction == TaxJurisdiction.INTRA_STATE:
            if has_igst and not (has_cgst and has_sgst):
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.IGST_APPLIED_INTRA_STATE.value)
            elif not (has_cgst and has_sgst) and not (cgst_r == 0 and sgst_r == 0 and igst_r == 0 and taxable_dec == 0):
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.TAX_HEAD_MISMATCH.value)
        elif jurisdiction == TaxJurisdiction.UT_INTRA_STATE:
            if has_sgst and not has_utgst:
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.SGST_APPLIED_WHEN_UTGST_REQUIRED.value)
            elif not (has_cgst and has_utgst) and not (cgst_r == 0 and utgst_r == 0 and taxable_dec == 0):
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.UTGST_MISSING.value)
        elif jurisdiction in (TaxJurisdiction.INTER_STATE, TaxJurisdiction.SEZ, TaxJurisdiction.IMPORT):
            if (has_cgst or has_sgst or has_utgst) and not has_igst:
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.CGST_SGST_APPLIED_INTER_STATE.value)
            elif not has_igst and not (cgst_r == 0 and sgst_r == 0 and igst_r == 0 and taxable_dec == 0):
                tax_head_mismatch = True
                mismatches.append(TaxMismatchType.TAX_HEAD_MISMATCH.value)

        # ---------------------------------------------------------------------
        # 6. Rate vs Amount vs Calculation Mismatch Verification
        # ---------------------------------------------------------------------
        # A. Rate Mismatch
        rate_diff = abs(applied_total_r - exp_total_r)
        rate_mismatch = rate_diff > tolerance_rate
        if rate_mismatch:
            mismatches.append(TaxMismatchType.RATE_MISMATCH.value)

        # B. Mathematical Tax Calculation Mismatch: (taxable * applied_rate) vs actual_total_tax
        math_tax_expected = round_monetary(taxable_dec * applied_total_r / Decimal("100.00"))
        calc_diff = abs(actual_total_tax - math_tax_expected)
        tax_calculation_mismatch = calc_diff > tolerance_amount
        if tax_calculation_mismatch:
            mismatches.append(TaxMismatchType.TAX_CALCULATION_MISMATCH.value)

        # C. Total Amount Mismatch: actual_total_tax vs exp_total_tax
        amount_diff = abs(actual_total_tax - exp_total_tax)
        amount_mismatch = amount_diff > tolerance_amount
        if amount_mismatch and not rate_mismatch and not tax_calculation_mismatch:
            mismatches.append(TaxMismatchType.AMOUNT_MISMATCH.value)

        # D. Invoice Total Mismatch: reported_invoice_total vs expected_invoice_total
        inv_tot_diff = abs(actual_invoice_total - exp_invoice_total)
        # Also check internal consistency: taxable + actual_total_tax vs actual_invoice_total
        internal_tot_diff = abs((taxable_dec + actual_total_tax) - actual_invoice_total)
        invoice_total_mismatch = (inv_tot_diff > tolerance_amount) or (internal_tot_diff > tolerance_amount)
        if invoice_total_mismatch and not (rate_mismatch or amount_mismatch or tax_calculation_mismatch):
            mismatches.append(TaxMismatchType.INVOICE_TOTAL_MISMATCH.value)

        # Component Differences
        cgst_diff = abs(cgst_a - exp_cgst_a)
        sgst_diff = abs(sgst_a - exp_sgst_a)
        utgst_diff = abs(utgst_a - exp_utgst_a)
        igst_diff = abs(igst_a - exp_igst_a)
        cess_diff = abs(cess_a - exp_cess_a)

        tax_difference = amount_diff if amount_diff > Decimal("0.00") else (calc_diff if calc_diff > Decimal("0.00") else Decimal("0.00"))

        # Zero Tax Handling: Check if legitimate or requires review
        if taxable_dec > 0 and applied_total_r == 0 and actual_total_tax == 0:
            if inv_type_clean not in ("EXEMPT", "NIL_RATED", "ZERO_RATED", "NON_GST", "EXPORT") and not is_rcm:
                if jurisdiction != TaxJurisdiction.REVIEW:
                    mismatches.append("ZERO_TAX_UNEXPLAINED")

        # ---------------------------------------------------------------------
        # 7. Resolution Suggestion Formulation
        # ---------------------------------------------------------------------
        resolution: Dict[str, Any] = {}
        if mismatches:
            primary_issue = mismatches[0]
            if primary_issue == TaxMismatchType.IGST_APPLIED_INTRA_STATE.value:
                action = f"Amend tax head from IGST ({igst_r}%) to Intra-State CGST ({exp_cgst_r}%) + SGST ({exp_sgst_r}%)."
            elif primary_issue == TaxMismatchType.SGST_APPLIED_WHEN_UTGST_REQUIRED.value:
                action = f"Replace SGST ({sgst_r}%) with UTGST ({exp_utgst_r}%) as {pos_state_name} is a Union Territory without legislature."
            elif primary_issue == TaxMismatchType.UTGST_MISSING.value:
                action = f"Apply UTGST ({exp_utgst_r}%) alongside CGST ({exp_cgst_r}%) for supply within {pos_state_name}."
            elif primary_issue == TaxMismatchType.CGST_SGST_APPLIED_INTER_STATE.value:
                action = f"Amend tax heads from CGST+SGST to Inter-State IGST ({exp_igst_r}%)."
            elif primary_issue == TaxMismatchType.RATE_MISMATCH.value:
                action = f"Reclassify tax rate from {applied_total_r}% to statutory HSN rate schedule {exp_total_r}%."
            elif primary_issue == TaxMismatchType.TAX_CALCULATION_MISMATCH.value:
                action = f"Recalculate invoice tax: Taxable INR {taxable_dec:,.2f} × {applied_total_r}% = INR {math_tax_expected:,.2f} (reported INR {actual_total_tax:,.2f})."
            elif primary_issue == TaxMismatchType.INVOICE_TOTAL_MISMATCH.value:
                action = f"Correct invoice grand total: Taxable INR {taxable_dec:,.2f} + Tax INR {actual_total_tax:,.2f} = INR {exp_invoice_total:,.2f} (reported INR {actual_invoice_total:,.2f})."
            elif primary_issue == TaxMismatchType.INVALID_TAX_COMBINATION.value:
                action = "Remove incompatible tax heads; domestic transactions must strictly use either (CGST + SGST) or (CGST + UTGST) or (IGST)."
            else:
                action = "Review transaction classification and state master records with finance lead."

            resolution = {
                "issue": primary_issue,
                "current_treatment": f"CGST: {cgst_r}% · SGST: {sgst_r}% · UTGST: {utgst_r}% · IGST: {igst_r}%",
                "expected_treatment": f"CGST: {exp_cgst_r}% · SGST: {exp_sgst_r}% · UTGST: {exp_utgst_r}% · IGST: {exp_igst_r}%",
                "tax_difference": float(tax_difference),
                "suggested_action": action,
                "required_approval": "FINANCE_LEAD_L3",
            }

        is_compliant = len(mismatches) == 0 and jurisdiction != TaxJurisdiction.REVIEW

        # Build Rich Evidence
        evidence = {
            "invoice_id": invoice_id,
            "direction": dir_clean,
            "invoice_type": inv_type_clean,
            "supplier_gstin": supp_g,
            "supplier_state": supp_state_name,
            "supplier_state_code": supp_state_code,
            "recipient_gstin": rec_g,
            "recipient_state": rec_state_name,
            "recipient_state_code": rec_state_code,
            "place_of_supply": pos_state_name,
            "pos_state_code": pos_state_code,
            "taxable_value": float(taxable_dec),
            "applied_rates": {"cgst": float(cgst_r), "sgst": float(sgst_r), "utgst": float(utgst_r), "ugst": float(utgst_r), "igst": float(igst_r), "cess": float(cess_r)},
            "expected_rates": {"cgst": float(exp_cgst_r), "sgst": float(exp_sgst_r), "utgst": float(exp_utgst_r), "ugst": float(exp_utgst_r), "igst": float(exp_igst_r), "cess": float(exp_cess_r)},
            "applied_amounts": {"cgst": float(cgst_a), "sgst": float(sgst_a), "utgst": float(utgst_a), "ugst": float(utgst_a), "igst": float(igst_a), "cess": float(cess_a), "total_tax": float(actual_total_tax), "invoice_total": float(actual_invoice_total)},
            "expected_amounts": {"cgst": float(exp_cgst_a), "sgst": float(exp_sgst_a), "utgst": float(exp_utgst_a), "ugst": float(exp_utgst_a), "igst": float(exp_igst_a), "cess": float(exp_cess_a), "total_tax": float(exp_total_tax), "invoice_total": float(exp_invoice_total)},
            "mismatches": mismatches,
            "resolution": resolution,
        }

        return TaxTreatmentResult(
            invoice_id=invoice_id,
            taxable_value=taxable_dec,
            jurisdiction=jurisdiction,
            treatment=treatment,
            expected_tax_head=expected_head,
            expected_cgst_rate=exp_cgst_r,
            expected_sgst_rate=exp_sgst_r,
            expected_utgst_rate=exp_utgst_r,
            expected_igst_rate=exp_igst_r,
            expected_cess_rate=exp_cess_r,
            expected_total_rate=exp_total_r,
            expected_cgst_amount=exp_cgst_a,
            expected_sgst_amount=exp_sgst_a,
            expected_utgst_amount=exp_utgst_a,
            expected_igst_amount=exp_igst_a,
            expected_cess_amount=exp_cess_a,
            expected_total_tax=exp_total_tax,
            expected_invoice_total=exp_invoice_total,
            applied_cgst_rate=cgst_r,
            applied_sgst_rate=sgst_r,
            applied_utgst_rate=utgst_r,
            applied_igst_rate=igst_r,
            applied_cess_rate=cess_r,
            applied_total_rate=applied_total_r,
            applied_cgst_amount=cgst_a,
            applied_sgst_amount=sgst_a,
            applied_utgst_amount=utgst_a,
            applied_igst_amount=igst_a,
            applied_cess_amount=cess_a,
            applied_total_tax=actual_total_tax,
            reported_invoice_total=actual_invoice_total,
            tax_difference=tax_difference,
            cgst_diff=cgst_diff,
            sgst_diff=sgst_diff,
            utgst_diff=utgst_diff,
            igst_diff=igst_diff,
            cess_diff=cess_diff,
            is_compliant=is_compliant,
            rate_mismatch=rate_mismatch,
            amount_mismatch=amount_mismatch,
            tax_head_mismatch=tax_head_mismatch,
            tax_calculation_mismatch=tax_calculation_mismatch,
            invoice_total_mismatch=invoice_total_mismatch,
            invalid_combination=invalid_combination,
            mismatches=mismatches,
            supplier_state=supp_state_name,
            supplier_state_code=supp_state_code,
            recipient_state=rec_state_name,
            recipient_state_code=rec_state_code,
            place_of_supply=pos_state_name,
            pos_state_code=pos_state_code,
            is_rcm=bool(is_rcm),
            rcm_applicable=bool(is_rcm),
            rcm_reason="Section 9(3) / 9(4) reverse charge notification" if is_rcm else None,
            tax_bearing_party="RECIPIENT" if is_rcm else "SUPPLIER",
            rationale=rationale,
            evidence=evidence,
            resolution_suggestion=resolution,
        )
