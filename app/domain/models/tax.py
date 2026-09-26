"""
UC15 GST Compliance Agent — Tax & Master Reference Models
"""
from __future__ import annotations

from decimal import Decimal
from pydantic import BaseModel, Field


class HSNMaster(BaseModel):
    """HSN/SAC official tax master record."""
    hsn_code: str
    description: str
    correct_cgst_rate: Decimal
    correct_sgst_rate: Decimal
    correct_igst_rate: Decimal
    mandatory_digits: int = Field(default=4)
    is_ewaste: bool = Field(default=False)
    is_scrap: bool = Field(default=False)
    is_rcm: bool = Field(default=False)
    sap_condition_type: str = Field(default="JOIC/JOIS/JOII")

    @classmethod
    def from_raw(
        cls,
        hsn_code: str,
        description: str,
        correct_cgst_rate: float | str | Decimal,
        correct_sgst_rate: float | str | Decimal,
        correct_igst_rate: float | str | Decimal,
        mandatory_digits: int = 4,
        is_ewaste: bool = False,
        is_scrap: bool = False,
        is_rcm: bool = False,
        sap_condition_type: str = "JOIC/JOIS/JOII",
    ) -> "HSNMaster":
        code_str = str(hsn_code).strip()
        # E-Waste HSN 8548/8549 or 8-digit requirement
        if code_str.startswith(("8548", "8549")):
            is_ewaste = True
            mandatory_digits = 8
        elif code_str.startswith("7204"):
            is_scrap = True
            is_rcm = True
            mandatory_digits = 8

        return cls(
            hsn_code=code_str,
            description=str(description).strip(),
            correct_cgst_rate=Decimal(str(correct_cgst_rate)),
            correct_sgst_rate=Decimal(str(correct_sgst_rate)),
            correct_igst_rate=Decimal(str(correct_igst_rate)),
            mandatory_digits=mandatory_digits,
            is_ewaste=is_ewaste,
            is_scrap=is_scrap,
            is_rcm=is_rcm,
            sap_condition_type=sap_condition_type,
        )


class StateCodeRef(BaseModel):
    """GSTIN 2-digit state prefix to official state name reference."""
    state_code: str
    state_name: str


class TaxBreakdown(BaseModel):
    """Detailed tax amounts and rates breakdown for an invoice."""
    taxable_value: Decimal = Field(default=Decimal("0.00"))
    cgst_rate: Decimal = Field(default=Decimal("0.00"))
    sgst_rate: Decimal = Field(default=Decimal("0.00"))
    igst_rate: Decimal = Field(default=Decimal("0.00"))
    cgst_amount: Decimal = Field(default=Decimal("0.00"))
    sgst_amount: Decimal = Field(default=Decimal("0.00"))
    igst_amount: Decimal = Field(default=Decimal("0.00"))
    cess_amount: Decimal = Field(default=Decimal("0.00"))
    total_tax: Decimal = Field(default=Decimal("0.00"))
    total_amount: Decimal = Field(default=Decimal("0.00"))
