"""
UC15 GST Compliance Agent — Canonical Invoice Domain Model (v2.0)
Unified canonical schema supporting multi-source ingestion (Excel, CSV, JSON, Mock, SAP, DataSphere).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator

from app.domain.models.vendor import Counterparty


class Invoice(BaseModel):
    """
    Canonical strongly-typed GST Invoice model.
    Uses Decimal for all monetary and tax figures to avoid floating-point drift.
    Source-agnostic contract for all compliance validation.
    """
    invoice_id: str
    invoice_number: str
    invoice_date: Union[date, str]
    direction: str = "AR"  # "AR" (outward / sales) | "AP" (inward / purchases)
    invoice_type: str = "B2B"  # B2B | B2C | EXPORT | SEZ | DEEMED_EXPORT
    currency: str = "INR"

    # Parties (Strongly typed)
    vendor: Optional[Counterparty] = None
    customer: Optional[Counterparty] = None
    counterparty_name: str
    gstin: str  # Counterparty GSTIN

    # Canonical GSTINs and States
    seller_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    seller_state: Optional[str] = None
    buyer_state: Optional[str] = None
    place_of_supply: str  # Declared state of supply

    # Classification & Line Items
    hsn_sac: str
    item_desc: str = ""
    quantity: Optional[Decimal] = None
    unit: Optional[str] = None

    # Financial & Tax details (Decimal precision)
    taxable_value: Decimal = Field(default=Decimal("0.00"))
    cgst_rate: Decimal = Field(default=Decimal("0.00"))
    sgst_rate: Decimal = Field(default=Decimal("0.00"))
    utgst_rate: Decimal = Field(default=Decimal("0.00"))  # Canonical field for UTGST / UGST
    igst_rate: Decimal = Field(default=Decimal("0.00"))
    cess_rate: Decimal = Field(default=Decimal("0.00"))

    reported_total_tax: Optional[Decimal] = None
    total_tax: Decimal = Field(default=Decimal("0.00"))
    reported_total_amount: Optional[Decimal] = None
    total_amount: Decimal = Field(default=Decimal("0.00"))

    # Tax Treatment and Classification Metadata
    tax_type: Optional[str] = None
    tax_treatment: Optional[str] = None
    tax_jurisdiction: Optional[str] = None

    # Regulatory & Statutory attributes
    eway_bill: Optional[str] = ""  # Lifecycle state: GENERATED | PENDING | CANCELLED | EXPIRED
    eway_bill_number: Optional[str] = None
    eway_bill_date: Optional[str] = None
    irn: Optional[str] = None  # e-Invoice Invoice Reference Number
    irn_date: Optional[str] = None
    gstr2b_reflected: bool = True   # Whether supplier reported invoice in GSTR-2B
    itc_eligible: Optional[bool] = None

    # SAP FI/SD Tax Attributes
    sap_tax_code: Optional[str] = None  # V1, V2, A1, O1, V3
    sap_condition_type: Optional[str] = None  # JOIC, JOIS, JOII, JOCP
    gl_account: Optional[str] = None
    material_group: Optional[str] = None
    asset_class: Optional[str] = None
    cost_center: Optional[str] = None

    # RCM & Payment / 180-Day Attributes
    is_rcm: Optional[bool] = None
    payment_status: Optional[str] = None  # UNPAID | PARTIAL | PAID | OVERDUE_180
    payment_date: Optional[Union[date, str]] = None
    payment_clearing_date: Optional[Union[date, str]] = None
    clearing_document: Optional[str] = None
    paid_amount: Decimal = Field(default=Decimal("0.00"))
    unpaid_amount: Decimal = Field(default=Decimal("0.00"))
    itc_reversal_amount: Decimal = Field(default=Decimal("0.00"))
    rcm_liability: Decimal = Field(default=Decimal("0.00"))
    interest_amount: Decimal = Field(default=Decimal("0.00"))

    # Credit/Debit Notes
    original_invoice_no: Optional[str] = None
    credit_debit_note_type: Optional[str] = None  # CREDIT_NOTE | DEBIT_NOTE | AMENDMENT

    # Extended E-Invoice & E-Way Bill Attributes
    irn_status: Optional[str] = None  # ACTIVE | CANCELLED | DUPLICATE | INVALID
    irn_cancellation_status: Optional[str] = None
    eway_bill_no: Optional[str] = None
    eway_generation_datetime: Optional[str] = None
    eway_valid_until: Optional[str] = None
    distance_km: Optional[Decimal] = None
    movement_mode: str = "ROAD"  # ROAD | RAIL | AIR | SHIP
    is_odc: bool = False  # Over-dimensional cargo

    # Registration & Return Reconciliation Attributes
    supplier_registration_type: str = "REGULAR"  # REGULAR | COMPOSITION | UNREGISTERED | SEZ | UIN
    recipient_registration_type: str = "REGULAR"
    turnover: Optional[Decimal] = None
    hsn_digits_required: Optional[int] = None
    gstr2b_match_status: str = "EXACT"  # EXACT | PROBABLE | PARTIAL | UNMATCHED | BOOKS_ONLY | GSTR2B_ONLY
    gstr1_status: Optional[str] = None
    gstr3b_status: Optional[str] = None

    # Ingestion provenance and extensible ERP metadata
    source_metadata: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # -- Backward compatibility properties matching original InvoiceRecord ----
    @property
    def invoice_no(self) -> str:
        return self.invoice_number

    @property
    def counterparty_gstin(self) -> str:
        return self.gstin

    @property
    def hsn_code(self) -> str:
        return self.hsn_sac

    @property
    def taxable_value_inr(self) -> float:
        return float(self.taxable_value)

    @property
    def total_amt(self) -> float:
        return float(self.total_amount)

    @property
    def eway_bill_status(self) -> str:
        return self.eway_bill or ""

    @property
    def cgst_rate_float(self) -> float:
        return float(self.cgst_rate)

    @property
    def sgst_rate_float(self) -> float:
        return float(self.sgst_rate)

    @property
    def igst_rate_float(self) -> float:
        return float(self.igst_rate)

    @property
    def utgst_rate_float(self) -> float:
        return float(self.utgst_rate)

    @property
    def ugst_rate_float(self) -> float:
        return float(self.utgst_rate)

    @property
    def ugst_rate(self) -> Decimal:
        return self.utgst_rate

    @property
    def supplier_gstin(self) -> str:
        return self.seller_gstin or (self.gstin if self.direction == "AP" else "")

    @property
    def recipient_gstin(self) -> str:
        return self.buyer_gstin or (self.gstin if self.direction == "AR" else "")

    @property
    def cgst_amount(self) -> Decimal:
        return round((self.taxable_value * self.cgst_rate) / Decimal("100.00"), 2)

    @property
    def sgst_amount(self) -> Decimal:
        return round((self.taxable_value * self.sgst_rate) / Decimal("100.00"), 2)

    @property
    def utgst_amount(self) -> Decimal:
        return round((self.taxable_value * self.utgst_rate) / Decimal("100.00"), 2)

    @property
    def ugst_amount(self) -> Decimal:
        return self.utgst_amount

    @property
    def igst_amount(self) -> Decimal:
        return round((self.taxable_value * self.igst_rate) / Decimal("100.00"), 2)

    @property
    def cess_amount(self) -> Decimal:
        return round((self.taxable_value * self.cess_rate) / Decimal("100.00"), 2)

    @property
    def is_gstr2b_matched(self) -> bool:
        return getattr(self, "gstr2b_reflected", True)

    @property
    def is_paid(self) -> bool:
        return bool(self.metadata.get("is_paid", False))

    @field_validator(
        "taxable_value", "cgst_rate", "sgst_rate", "utgst_rate", "igst_rate", "cess_rate",
        "total_tax", "total_amount", "quantity", "paid_amount", "unpaid_amount",
        "itc_reversal_amount", "rcm_liability", "interest_amount", "distance_km", "turnover",
        mode="before"
    )
    @classmethod
    def parse_decimal(cls, v: Any) -> Optional[Decimal]:
        if v is None or v == "":
            return Decimal("0.00")
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v).strip().replace(",", ""))

    @field_validator("reported_total_tax", "reported_total_amount", mode="before")
    @classmethod
    def parse_optional_decimal(cls, v: Any) -> Optional[Decimal]:
        if v is None or str(v).strip() == "":
            return None
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v).strip().replace(",", ""))


    @field_validator("direction", mode="before")
    @classmethod
    def parse_direction(cls, v: Any) -> str:
        s = str(v or "AR").strip().upper()
        return "AP" if s == "AP" else "AR"

    @classmethod
    def from_record(
        cls,
        invoice_no: str,
        invoice_date: str,
        direction: str,
        counterparty_gstin: str,
        counterparty_name: str,
        place_of_supply: str,
        hsn_code: str,
        item_desc: str,
        taxable_value_inr: float | Decimal | str,
        cgst_rate: float | Decimal | str,
        sgst_rate: float | Decimal | str,
        igst_rate: float | Decimal | str,
        total_amt: float | Decimal | str,
        eway_bill_status: str = "",
        gstr2b_reflected: bool = True,
        invoice_type: str = "B2B",
        eway_bill_number: Optional[str] = None,
        irn: Optional[str] = None,
        seller_gstin: Optional[str] = None,
        buyer_gstin: Optional[str] = None,
        source_metadata: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        invoice_id: Optional[str] = None,
        utgst_rate: float | Decimal | str = 0.0,
        ugst_rate: Optional[float | Decimal | str] = None,
        cess_rate: float | Decimal | str = 0.0,
        total_tax: Optional[float | Decimal | str] = None,
        tax_type: Optional[str] = None,
        tax_treatment: Optional[str] = None,
        tax_jurisdiction: Optional[str] = None,
        seller_state: Optional[str] = None,
        buyer_state: Optional[str] = None,
    ) -> "Invoice":
        from app.domain.services.transaction_calculator import compute_canonical_financials, sanitize_eway_bill_status

        # Effective UTGST / UGST rate
        eff_utgst = utgst_rate if (ugst_rate is None or float(utgst_rate or 0) > 0) else ugst_rate

        fin = compute_canonical_financials(
            taxable_value=taxable_value_inr,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            utgst_rate=eff_utgst,
            igst_rate=igst_rate,
            cess_rate=cess_rate,
            total_tax=total_tax,
            total_amount=total_amt,
        )

        taxable_dec = fin["taxable_value"]
        cgst_dec = fin["cgst_rate"]
        sgst_dec = fin["sgst_rate"]
        utgst_dec = fin.get("utgst_rate", Decimal("0.00"))
        igst_dec = fin["igst_rate"]
        cess_dec = fin.get("cess_rate", Decimal("0.00"))
        total_tax_dec = fin["total_tax"]
        total_amt_dec = fin["invoice_total"]
        reported_tot_amt = fin.get("reported_total_amount")
        reported_tot_tax = fin.get("reported_total_tax")

        sanitized_ewb_status = sanitize_eway_bill_status(
            raw_status=eway_bill_status,
            taxable_value=taxable_dec,
        )

        cparty_clean_gstin = str(counterparty_gstin or "").strip().upper()
        cparty_state_code = cparty_clean_gstin[:2] if len(cparty_clean_gstin) >= 2 else None

        from app.rules.tax_treatment import lookup_state_info
        cparty_state_info = lookup_state_info(cparty_state_code)
        cparty_state_name = cparty_state_info.name if cparty_state_info else str(place_of_supply).strip()

        cparty = Counterparty(
            name=str(counterparty_name).strip(),
            gstin=cparty_clean_gstin,
            state_code=cparty_state_code,
            state_name=cparty_state_name,
        )

        is_ap = str(direction).strip().upper() == "AP"
        final_seller = str(seller_gstin).strip().upper() if seller_gstin else (cparty_clean_gstin if is_ap else None)
        final_buyer = str(buyer_gstin).strip().upper() if buyer_gstin else (None if is_ap else cparty_clean_gstin)

        seller_state_from_gstin = None
        if final_seller and len(final_seller) >= 2:
            s_info = lookup_state_info(final_seller[:2])
            if s_info:
                seller_state_from_gstin = s_info.name

        buyer_state_from_gstin = None
        if final_buyer and len(final_buyer) >= 2:
            b_info = lookup_state_info(final_buyer[:2])
            if b_info:
                buyer_state_from_gstin = b_info.name

        # Distinguish supplier state vs recipient state vs place of supply
        derived_seller_state = seller_state or seller_state_from_gstin or (cparty_state_name if is_ap else "Maharashtra")
        derived_buyer_state = buyer_state or buyer_state_from_gstin or ("Maharashtra" if is_ap else cparty_state_name)

        return cls(
            invoice_id=str(invoice_id or invoice_no).strip(),
            invoice_number=str(invoice_no).strip(),
            invoice_date=invoice_date,
            direction="AP" if is_ap else "AR",
            invoice_type=invoice_type,
            vendor=cparty if is_ap else None,
            customer=None if is_ap else cparty,
            counterparty_name=str(counterparty_name).strip(),
            gstin=cparty_clean_gstin,
            seller_gstin=final_seller,
            buyer_gstin=final_buyer,
            place_of_supply=str(place_of_supply).strip(),
            buyer_state=derived_buyer_state,
            seller_state=derived_seller_state,
            hsn_sac=str(hsn_code).strip(),
            item_desc=str(item_desc or "").strip(),
            taxable_value=taxable_dec,
            cgst_rate=cgst_dec,
            sgst_rate=sgst_dec,
            utgst_rate=utgst_dec,
            igst_rate=igst_dec,
            cess_rate=cess_dec,
            reported_total_tax=reported_tot_tax,
            total_tax=total_tax_dec,
            reported_total_amount=reported_tot_amt,
            total_amount=total_amt_dec,
            tax_type=tax_type,
            tax_treatment=tax_treatment,
            tax_jurisdiction=tax_jurisdiction,
            eway_bill=sanitized_ewb_status,
            eway_bill_number=eway_bill_number,
            irn=irn,
            gstr2b_reflected=bool(gstr2b_reflected),
            source_metadata=source_metadata,
            metadata=metadata or {},
        )

