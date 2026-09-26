"""
UC15 GST Compliance Agent — Tax Rate Reference Model
Temporal tax rate schedule mapping HSN/SAC classifications to statutory CGST, SGST, IGST, and Cess rates.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.reference.models.base import BaseReferenceRecord


@dataclass
class TaxRateReference(BaseReferenceRecord):
    """
    Statutory GST rate entry for a specific HSN/SAC code valid over an effective date window.
    """
    hsn_code: str = ""
    cgst_rate: Decimal = Decimal("0.0")                     # e.g. 0.09 for 9%
    sgst_rate: Decimal = Decimal("0.0")                     # e.g. 0.09 for 9%
    igst_rate: Decimal = Decimal("0.0")                     # e.g. 0.18 for 18%
    cess_rate: Decimal = Decimal("0.0")
    rate_type: str = "STANDARD"                             # STANDARD | CONCESSIONAL | EXEMPT | NIL_RATED
    notification_no: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        self.reference_type = "TAX_RATE"
        self.hsn_code = str(self.hsn_code or "").strip()
        # Convert numeric or float inputs to Decimal if needed
        if not isinstance(self.cgst_rate, Decimal):
            self.cgst_rate = Decimal(str(self.cgst_rate))
        if not isinstance(self.sgst_rate, Decimal):
            self.sgst_rate = Decimal(str(self.sgst_rate))
        if not isinstance(self.igst_rate, Decimal):
            self.igst_rate = Decimal(str(self.igst_rate))
        if not isinstance(self.cess_rate, Decimal):
            self.cess_rate = Decimal(str(self.cess_rate))

    @property
    def total_intra_rate(self) -> Decimal:
        """Combined CGST + SGST percentage."""
        return self.cgst_rate + self.sgst_rate

    def validate_integrity(self) -> list[str]:
        """Perform data quality validation on statutory tax rates."""
        issues = super().validate_integrity()
        if not self.hsn_code:
            issues.append(f"[{self.reference_id}] Missing hsn_code")
        if self.cgst_rate < Decimal("0.0"):
            issues.append(f"[{self.reference_id}] cgst_rate cannot be negative: {self.cgst_rate}")
        if self.sgst_rate < Decimal("0.0"):
            issues.append(f"[{self.reference_id}] sgst_rate cannot be negative: {self.sgst_rate}")
        if self.igst_rate < Decimal("0.0"):
            issues.append(f"[{self.reference_id}] igst_rate cannot be negative: {self.igst_rate}")
        if self.cess_rate < Decimal("0.0"):
            issues.append(f"[{self.reference_id}] cess_rate cannot be negative: {self.cess_rate}")
        return issues
