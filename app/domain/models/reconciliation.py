"""
UC15 GST Compliance Agent — Canonical GST Return Reconciliation Models
Models for multi-way reconciliation across SAP Books, GST Invoices, GSTR-1, GSTR-2B, GSTR-3B, and DRC-01C risk monitoring.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReconciliationStatus(str, Enum):
    EXACT = "EXACT"
    PROBABLE = "PROBABLE"
    PARTIAL = "PARTIAL"
    UNMATCHED = "UNMATCHED"
    BOOKS_ONLY = "BOOKS_ONLY"
    GST_ONLY = "GST_ONLY"
    GSTR2B_ONLY = "GSTR2B_ONLY"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DRC01CRiskLevel(str, Enum):
    NO_MISMATCH = "NO_MISMATCH"
    WITHIN_THRESHOLD = "WITHIN_THRESHOLD"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    HIGH_RISK = "HIGH_RISK"


class InvoiceReconciliationRecord(BaseModel):
    """
    Detailed reconciliation record for a single invoice across books and GST filings.
    """
    invoice_number: str
    supplier_gstin: str
    recipient_gstin: str
    invoice_date: str

    # Value Comparisons
    books_taxable_value: Decimal = Field(default=Decimal("0.00"))
    books_total_tax: Decimal = Field(default=Decimal("0.00"))

    gstr2b_taxable_value: Optional[Decimal] = None
    gstr2b_total_tax: Optional[Decimal] = None

    gstr1_taxable_value: Optional[Decimal] = None
    gstr1_total_tax: Optional[Decimal] = None

    # Mismatch Variance
    taxable_variance: Decimal = Field(default=Decimal("0.00"))
    tax_variance: Decimal = Field(default=Decimal("0.00"))

    match_status: ReconciliationStatus = ReconciliationStatus.UNMATCHED
    mismatch_reasons: List[str] = Field(default_factory=list)


class DRC01CRiskReport(BaseModel):
    """
    DRC-01C Monitoring Report evaluating 2B vs 3B ITC claim variance.
    """
    tax_period: str
    gstr2b_itc_available: Decimal = Field(default=Decimal("0.00"))
    gstr3b_itc_claimed: Decimal = Field(default=Decimal("0.00"))
    excess_itc_claimed: Decimal = Field(default=Decimal("0.00"))
    variance_percentage: Decimal = Field(default=Decimal("0.00"))

    risk_level: DRC01CRiskLevel = DRC01CRiskLevel.NO_MISMATCH
    threshold_percentage: Decimal = Field(default=Decimal("10.00")) # DRC-01C 10% threshold
    action_required: str = "NO_ACTION"
    evidence: Dict[str, Any] = Field(default_factory=dict)
