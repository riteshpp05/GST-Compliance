"""
app.data.validation.schema_validator
====================================
Structural & Schema Validation Engine for raw GST records (Sprint 17).
Distinguishes structural/type errors from GST business logic rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional


@dataclass
class StructuralValidationResult:
    """Result of structural schema validation for a raw record."""
    is_valid: bool
    record_index: int
    missing_required_fields: List[str] = field(default_factory=list)
    malformed_fields: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "record_index": self.record_index,
            "missing_required_fields": self.missing_required_fields,
            "malformed_fields": self.malformed_fields,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class SchemaValidator:
    """
    Validates structural integrity of incoming raw GST invoice records before normalization.
    Core Required Structural Fields:
    - invoice_id or invoice_number / invoice_no
    - gstin or supplier_gstin or counterparty_gstin
    - taxable_value or taxable_amount
    """

    REQUIRED_FIELD_GROUPS = [
        ["invoice_id", "invoice_number", "invoice_no", "inv_num"],
        ["gstin", "supplier_gstin", "counterparty_gstin", "seller_gstin"],
        ["taxable_value", "taxable_value_inr", "taxable_amount", "base_amount"],
    ]

    @classmethod
    def validate_structure(cls, record: Dict[str, Any], record_index: int = 0) -> StructuralValidationResult:
        missing_fields: List[str] = []
        malformed_fields: List[str] = []
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(record, dict):
            return StructuralValidationResult(
                is_valid=False,
                record_index=record_index,
                errors=["Record is not a valid dictionary structure."],
            )

        # 1. Check Required Field Groups
        for group in cls.REQUIRED_FIELD_GROUPS:
            found = False
            for f in group:
                if f in record and record[f] is not None and str(record[f]).strip() != "":
                    found = True
                    break
            if not found:
                field_name = group[0]
                missing_fields.append(field_name)
                errors.append(f"Missing required structural field (expected one of: {group}).")

        # 2. Check Numeric Field Syntax (Taxable Value & Total Amount if present)
        for tax_key in ("taxable_value", "taxable_value_inr", "taxable_amount", "total_amount", "total_amt", "cgst", "sgst", "igst"):
            if tax_key in record and record[tax_key] is not None:
                val = str(record[tax_key]).strip().replace(",", "").replace("₹", "").replace("Rs.", "")
                if val and val.lower() not in ("", "none", "null", "nan", "n/a", "-"):
                    try:
                        dec_val = Decimal(val)
                        if dec_val < 0 and tax_key in ("taxable_value", "taxable_value_inr", "taxable_amount"):
                            warnings.append(f"Field '{tax_key}' contains negative value {val}.")
                    except InvalidOperation:
                        malformed_fields.append(tax_key)
                        errors.append(f"Field '{tax_key}' contains non-numeric value '{record[tax_key]}'.")

        # 3. Check Date Field Syntax if present
        for date_key in ("invoice_date", "inv_date", "date"):
            if date_key in record and record[date_key] is not None:
                d_str = str(record[date_key]).strip()
                if d_str and d_str.lower() not in ("", "none", "null", "nan", "n/a", "-"):
                    if not cls._is_parseable_date(d_str):
                        malformed_fields.append(date_key)
                        errors.append(f"Field '{date_key}' contains malformed date string '{d_str}'.")

        is_valid = len(errors) == 0
        return StructuralValidationResult(
            is_valid=is_valid,
            record_index=record_index,
            missing_required_fields=missing_fields,
            malformed_fields=malformed_fields,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _is_parseable_date(val: Any) -> bool:
        import datetime
        if isinstance(val, (datetime.date, datetime.datetime, int, float)):
            return True
        s = str(val).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d.%m.%Y", "%m/%d/%Y", "%Y%m%d", "%d %b %Y", "%d-%b-%Y"):
            try:
                datetime.datetime.strptime(s, fmt)
                return True
            except ValueError:
                continue
        return False
