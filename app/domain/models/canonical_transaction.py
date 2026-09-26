"""
UC15 GST Compliance Agent — Canonical Transaction & Lineage Model (Phase 1)
Defines normalized finance transaction schema with explicit data lineage tracking.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional
from pydantic import BaseModel, Field

from app.domain.models.invoice import Invoice


class DataLineage(BaseModel):
    """Tracks origin and transformation history of a transaction field."""
    source_system: str = Field(default="ERP_INGESTION")
    source_object: str = Field(default="INVOICE_HEADER")
    source_field: str = Field(default="UNKNOWN")
    source_record: Optional[str] = None
    retrieved_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    transformation: Optional[str] = "NORMALIZED"


class CanonicalTransaction(BaseModel):
    """
    Normalized Finance Transaction Model.
    Decouples source-specific ERP/Excel formats from statutory compliance rules.
    """

    # Identifiers
    transaction_id: str
    document_number: str
    document_type: str = Field(default="INV")  # INV, DEL, CRN, DRN, BOE

    # Supplier (AP / Vendor)
    supplier_name: Optional[str] = None
    supplier_gstin: Optional[str] = None
    supplier_state: Optional[str] = None
    supplier_registration_type: str = Field(default="REGULAR")  # REGULAR, COMPOSITION, SEZ, UNREGISTERED
    supplier_sez_status: bool = Field(default=False)

    # Buyer (AR / Customer)
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    buyer_state: Optional[str] = None
    buyer_registration_type: str = Field(default="REGULAR")
    buyer_sez_status: bool = Field(default=False)

    # Dates
    invoice_date: Optional[date] = None
    supply_date: Optional[date] = None

    # Classification & Financial Values
    supply_type: str = Field(default="B2B")  # B2B, B2C, EXPORT, SEZ, DEEMED_EXPORT
    transaction_type: str = Field(default="INWARD_AP")  # INWARD_AP, OUTWARD_AR
    taxable_value: Decimal = Field(default=Decimal("0.00"))
    cgst_amount: Decimal = Field(default=Decimal("0.00"))
    sgst_amount: Decimal = Field(default=Decimal("0.00"))
    igst_amount: Decimal = Field(default=Decimal("0.00"))
    cess_amount: Decimal = Field(default=Decimal("0.00"))
    tax_rate: Decimal = Field(default=Decimal("0.00"))

    # Statutory Codes
    hsn_code: Optional[str] = None
    sac_code: Optional[str] = None
    place_of_supply: Optional[str] = None

    # Reverse Charge & E-Invoice
    rcm_applicable: bool = Field(default=False)
    rcm_status: str = Field(default="FORWARD_CHARGE")
    e_invoice_applicable: bool = Field(default=False)
    irn: Optional[str] = None
    irn_status: Optional[str] = None

    # E-Way Bill
    eway_bill_applicable: bool = Field(default=False)
    eway_bill_number: Optional[str] = None
    eway_bill_status: Optional[str] = None
    eway_bill_date: Optional[date] = None

    # Payment & Returns
    payment_status: str = Field(default="UNPAID")  # PAID, UNPAID, CLEARED, OVERDUE
    payment_date: Optional[date] = None
    clearing_date: Optional[date] = None
    original_invoice_no: Optional[str] = None
    is_credit_debit_note: bool = Field(default=False)

    return_period: Optional[str] = None
    gstr1_status: Optional[str] = None
    gstr2b_status: Optional[str] = None
    gstr3b_status: Optional[str] = None

    # Field-level Lineage
    lineage: Dict[str, DataLineage] = Field(default_factory=dict)

    @classmethod
    def from_raw(cls, **data) -> "CanonicalTransaction":
        return cls(**data)

    @classmethod
    def from_invoice(cls, invoice: Invoice, source_system: str = "EXCEL_LOADER") -> "CanonicalTransaction":
        """Backwards-compatible converter from existing Invoice domain model."""
        inv_id = str(getattr(invoice, "invoice_id", getattr(invoice, "id", "1")))
        inv_no = invoice.invoice_number or f"INV-{inv_id}"
        is_ar = getattr(invoice, "direction", "AP").upper() == "AR"
        trans_type = "OUTWARD_AR" if is_ar else "INWARD_AP"

        c_gstin = getattr(invoice, "gstin", getattr(invoice, "counterparty_gstin", ""))
        c_name = getattr(invoice, "counterparty_name", "")

        supplier_gstin = c_gstin if not is_ar else getattr(invoice, "seller_gstin", c_gstin)
        buyer_gstin = getattr(invoice, "buyer_gstin", c_gstin) if not is_ar else c_gstin

        supplier_state = supplier_gstin[:2] if supplier_gstin and len(supplier_gstin) >= 2 else None
        buyer_state = buyer_gstin[:2] if buyer_gstin and len(buyer_gstin) >= 2 else None

        lineage_map = {
            "taxable_value": DataLineage(source_system=source_system, source_field="taxable_value"),
            "invoice_number": DataLineage(source_system=source_system, source_field="invoice_number"),
            "gstin": DataLineage(source_system=source_system, source_field="gstin"),
        }

        # Handle invoice date
        inv_d = None
        if isinstance(invoice.invoice_date, date):
            inv_d = invoice.invoice_date
        elif isinstance(invoice.invoice_date, str):
            try:
                inv_d = datetime.strptime(invoice.invoice_date.strip(), "%Y-%m-%d").date()
            except ValueError:
                inv_d = date(2026, 1, 1)

        from app.domain.services.transaction_calculator import sanitize_eway_bill_status

        hsn_val = getattr(invoice, "hsn_sac", getattr(invoice, "hsn_code", ""))
        tax_r = getattr(invoice, "cgst_rate", Decimal("0.0")) + getattr(invoice, "sgst_rate", Decimal("0.0")) + getattr(invoice, "igst_rate", Decimal("0.0"))
        sanitized_ewb = sanitize_eway_bill_status(invoice.eway_bill, Decimal(str(invoice.taxable_value)))

        return cls(
            transaction_id=inv_id,
            document_number=inv_no,
            supplier_name=c_name if not is_ar else "My Company",
            supplier_gstin=supplier_gstin,
            supplier_state=supplier_state,
            buyer_name="My Company" if not is_ar else c_name,
            buyer_gstin=buyer_gstin,
            buyer_state=buyer_state,
            invoice_date=inv_d,
            transaction_type=trans_type,
            taxable_value=Decimal(str(invoice.taxable_value)),
            cgst_amount=Decimal(str(getattr(invoice, "cgst_amount", 0.0))),
            sgst_amount=Decimal(str(getattr(invoice, "sgst_amount", 0.0))),
            igst_amount=Decimal(str(getattr(invoice, "igst_amount", 0.0))),
            tax_rate=Decimal(str(tax_r)),
            hsn_code=hsn_val,
            sac_code=hsn_val,
            place_of_supply=invoice.place_of_supply,
            eway_bill_number=invoice.eway_bill_number,
            eway_bill_status=sanitized_ewb,
            irn=invoice.irn,
            lineage=lineage_map,
        )

    def to_invoice(self) -> Invoice:
        """Backwards-compatible converter back to Invoice domain model."""
        c_name = self.supplier_name if self.transaction_type == "INWARD_AP" else self.buyer_name
        c_gstin = self.supplier_gstin if self.transaction_type == "INWARD_AP" else self.buyer_gstin

        return Invoice(
            invoice_id=self.transaction_id,
            invoice_number=self.document_number,
            invoice_date=str(self.invoice_date or date(2026, 1, 1)),
            direction="AP" if self.transaction_type == "INWARD_AP" else "AR",
            counterparty_name=c_name or "Counterparty",
            gstin=c_gstin or "27AAACA1234A1Z5",
            place_of_supply=self.place_of_supply or "Maharashtra",
            hsn_sac=self.hsn_code or "8471",
            taxable_value=Decimal(str(self.taxable_value)),
            cgst_amount=Decimal(str(self.cgst_amount)),
            sgst_amount=Decimal(str(self.sgst_amount)),
            igst_amount=Decimal(str(self.igst_amount)),
            eway_bill_number=self.eway_bill_number,
            eway_bill=self.eway_bill_status,
            irn=self.irn,
        )
