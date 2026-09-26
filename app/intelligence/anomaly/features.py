"""
app.intelligence.anomaly.features
=================================
Feature extraction layer for Anomaly Intelligence (Sprint 7).
Extracts typed numerical and categorical feature vectors without mutating canonical invoices.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.intelligence.duplicate.fingerprint import (
    extract_parties,
    normalize_date,
    parse_decimal_safe,
)


@dataclass(frozen=True)
class InvoiceFeature:
    """Immutable feature vector representing a single invoice for statistical anomaly analysis."""
    invoice_id: str
    counterparty_id: str
    counterparty_name: str
    invoice_date: str
    taxable_value: float
    total_tax: float
    total_amount: float
    effective_tax_rate: float
    hsn_code: str
    direction: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "counterparty_id": self.counterparty_id,
            "counterparty_name": self.counterparty_name,
            "invoice_date": self.invoice_date,
            "taxable_value": self.taxable_value,
            "total_tax": self.total_tax,
            "total_amount": self.total_amount,
            "effective_tax_rate": round(self.effective_tax_rate, 2),
            "hsn_code": self.hsn_code,
            "direction": self.direction,
        }


class InvoiceFeatureExtractor:
    """Extracts immutable statistical feature vectors from canonical Invoice objects."""

    @staticmethod
    def extract(inv: Invoice) -> InvoiceFeature:
        inv_id = getattr(inv, "invoice_id", None) or getattr(inv, "invoice_number", "UNKNOWN")
        supplier, _ = extract_parties(inv)
        counterparty_id = getattr(inv, "gstin", None) or supplier or getattr(inv, "counterparty_name", "UNKNOWN")
        counterparty_name = getattr(inv, "counterparty_name", "") or counterparty_id

        inv_date = normalize_date(getattr(inv, "invoice_date", None)) or "2023-01-01"

        from app.domain.services.transaction_calculator import compute_canonical_financials

        taxable_val_raw = parse_decimal_safe(getattr(inv, "taxable_value", None))
        cgst_r = parse_decimal_safe(getattr(inv, "cgst_rate", None))
        sgst_r = parse_decimal_safe(getattr(inv, "sgst_rate", None))
        igst_r = parse_decimal_safe(getattr(inv, "igst_rate", None))
        total_tax_raw = parse_decimal_safe(getattr(inv, "total_tax", None))
        total_amt_raw = parse_decimal_safe(getattr(inv, "total_amount", None))

        fin = compute_canonical_financials(
            taxable_value=taxable_val_raw,
            cgst_rate=cgst_r,
            sgst_rate=sgst_r,
            igst_rate=igst_r,
            total_tax=total_tax_raw,
            total_amount=total_amt_raw,
        )

        taxable_val = float(fin["taxable_value"])
        total_tax = float(fin["total_tax"])
        total_amt = float(fin["invoice_total"])
        eff_rate = float(fin["effective_tax_rate"])

        hsn = str(getattr(inv, "hsn_sac", None) or getattr(inv, "hsn_code", "") or "").strip()
        direction = str(getattr(inv, "direction", "AP") or "AP").upper()

        return InvoiceFeature(
            invoice_id=inv_id,
            counterparty_id=counterparty_id,
            counterparty_name=counterparty_name,
            invoice_date=inv_date,
            taxable_value=taxable_val,
            total_tax=total_tax,
            total_amount=total_amt,
            effective_tax_rate=eff_rate,
            hsn_code=hsn,
            direction=direction,
        )

    @classmethod
    def extract_batch(cls, invoices: List[Invoice]) -> List[InvoiceFeature]:
        return [cls.extract(inv) for inv in invoices]
