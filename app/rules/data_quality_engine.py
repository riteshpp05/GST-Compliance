"""
UC15 GST Compliance Agent — Data Quality Engine (Phase 2)
Evaluates transaction data usability prior to statutory validation.
Distinguishes missing/unavailable data from statutory non-compliance.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.domain.enums.data_quality_status import DataQualityStatus
from app.domain.models.canonical_transaction import CanonicalTransaction


class DataQualityAssessment(BaseModel):
    """Result of Data Quality usability evaluation for a transaction."""
    overall_status: DataQualityStatus = DataQualityStatus.VALID
    field_statuses: Dict[str, DataQualityStatus] = Field(default_factory=dict)
    usable_for_statutory_check: bool = True
    rejection_reasons: List[str] = Field(default_factory=list)


class DataQualityEngine:
    """
    Data Quality Engine.
    Pre-checks data integrity (GSTIN, Invoice No, Taxable Value, POS) before statutory rule execution.
    """

    @staticmethod
    def evaluate(tx: CanonicalTransaction) -> DataQualityAssessment:
        field_statuses: Dict[str, DataQualityStatus] = {}
        reasons: List[str] = []

        # 1. Invoice Number Check
        if not tx.document_number or not tx.document_number.strip():
            field_statuses["document_number"] = DataQualityStatus.MISSING
            reasons.append("Document number is missing.")
        else:
            field_statuses["document_number"] = DataQualityStatus.VALID

        # 2. GSTIN Usability Check
        counterparty_gstin = tx.supplier_gstin if tx.transaction_type == "INWARD_AP" else tx.buyer_gstin
        if not counterparty_gstin or not counterparty_gstin.strip():
            field_statuses["counterparty_gstin"] = DataQualityStatus.MISSING
            reasons.append("Counterparty GSTIN is missing.")
        elif len(counterparty_gstin.strip()) != 15:
            field_statuses["counterparty_gstin"] = DataQualityStatus.INVALID
            reasons.append(f"Counterparty GSTIN '{counterparty_gstin}' has invalid length.")
        else:
            field_statuses["counterparty_gstin"] = DataQualityStatus.VALID

        # 3. Taxable Value Check
        if tx.taxable_value is None:
            field_statuses["taxable_value"] = DataQualityStatus.MISSING
            reasons.append("Taxable value is missing.")
        elif tx.taxable_value < 0 and not tx.is_credit_debit_note:
            field_statuses["taxable_value"] = DataQualityStatus.INVALID
            reasons.append("Negative taxable value on standard invoice.")
        else:
            field_statuses["taxable_value"] = DataQualityStatus.VALID

        # 4. E-Way Bill Usability vs Missing Data
        if tx.eway_bill_applicable and not tx.eway_bill_number:
            field_statuses["eway_bill_number"] = DataQualityStatus.UNAVAILABLE
        else:
            field_statuses["eway_bill_number"] = DataQualityStatus.VALID

        # Overall Status Determination
        has_invalid = any(s == DataQualityStatus.INVALID for s in field_statuses.values())
        has_missing = any(s in (DataQualityStatus.MISSING, DataQualityStatus.UNAVAILABLE) for s in field_statuses.values())

        if has_invalid:
            overall = DataQualityStatus.INVALID
        elif has_missing:
            overall = DataQualityStatus.MISSING
        else:
            overall = DataQualityStatus.VALID

        usable = not has_invalid and "document_number" not in [k for k, v in field_statuses.items() if v != DataQualityStatus.VALID]

        return DataQualityAssessment(
            overall_status=overall,
            field_statuses=field_statuses,
            usable_for_statutory_check=usable,
            rejection_reasons=reasons,
        )
