"""
UC15 GST Compliance Agent — Canonical SAP FI/SD Financial Document Models
Standardized representations for SAP BSEG/BKPF Accounting Documents and VBRP/VBRK Billing Documents.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class SAPAccountingDocument(BaseModel):
    """
    Canonical representation of an SAP FI Accounting Document (BKPF/BSEG).
    """
    company_code: str = "1000"  # BUKRS
    fiscal_year: str = "2025"   # GJAHR
    document_number: str       # BELNR
    document_type: str = "KR"  # BLART (KR: Vendor Invoice, DR: Customer Invoice, KG: Credit Memo)
    posting_date: Union[date, str]
    document_date: Union[date, str]
    reference: Optional[str] = None  # XBLNR (Vendor Invoice Number)

    # Line Item Details (BSEG)
    line_item: int = 1
    vendor: Optional[str] = None     # LIFNR
    customer: Optional[str] = None   # KUNNR
    gl_account: Optional[str] = None # HKONT

    # Tax & Financials
    tax_code: str  # MWSKZ (V1, V2, A1, O1, V3)
    currency: str = "INR"
    amount_in_doc_curr: Decimal = Field(default=Decimal("0.00")) # WRBTR
    tax_amount: Decimal = Field(default=Decimal("0.00"))        # WMWST
    tax_base_amount: Decimal = Field(default=Decimal("0.00"))   # FWBAS

    # Clearing / Payment Details
    clearing_document: Optional[str] = None  # AUGBL
    clearing_date: Optional[Union[date, str]] = None  # AUGDT
    payment_status: str = "UNPAID"  # UNPAID | PARTIAL | PAID | OVERDUE_180
    due_date: Optional[Union[date, str]] = None

    # GST Regulatory Integrations
    irn: Optional[str] = None
    eway_bill_no: Optional[str] = None

    # Source Lineage & Provenance
    source_system: str = "SAP_S4HANA"  # LIVE | SIMULATED | MOCK | UNAVAILABLE
    raw_sap_data: Dict[str, Any] = Field(default_factory=dict)


class SAPBillingDocument(BaseModel):
    """
    Canonical representation of an SAP SD Billing Document (VBRK/VBRP).
    """
    billing_document: str  # VBELN
    billing_item: int = 10 # POSNR
    billing_type: str = "F2" # FKART (F2: Invoice, G2: Credit Memo, L2: Debit Memo)
    billing_date: Union[date, str]
    company_code: str = "1000"

    customer: str  # KUNNR
    hsn_sac: str   # STEUC
    material: Optional[str] = None # MATNR

    taxable_value: Decimal = Field(default=Decimal("0.00"))
    tax_amount: Decimal = Field(default=Decimal("0.00"))
    tax_code: str  # MWSKZ

    pricing_condition_type: Optional[str] = None # KSCHL (JOIC, JOIS, JOII, JOCP)
    pricing_condition_value: Decimal = Field(default=Decimal("0.00"))

    irn: Optional[str] = None
    eway_bill_no: Optional[str] = None
    source_system: str = "SAP_S4HANA"
