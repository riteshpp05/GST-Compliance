"""
app.data.deduplication.deduplication_engine
===========================================
Deterministic Deduplication Engine for GST records (Sprint 17).
Generates exact and potential identity fingerprints to detect duplicates.

CRITICAL RULE:
POTENTIAL_DUPLICATE is a review signal for human/system investigation, NEVER automatic deletion or hard rejection.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class DuplicateStatus(str, Enum):
    """Classification of record duplicate status."""
    UNIQUE = "UNIQUE"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"


@dataclass
class DuplicateCheckResult:
    """Outcome of duplicate check for a single canonical GST record."""
    status: DuplicateStatus
    exact_fingerprint: str
    potential_fingerprint: str
    matched_record_id: Optional[str] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "exact_fingerprint": self.exact_fingerprint,
            "potential_fingerprint": self.potential_fingerprint,
            "matched_record_id": self.matched_record_id,
            "description": self.description,
        }


class DeduplicationEngine:
    """
    Computes deterministic record fingerprints and maintains in-batch and cross-batch
    deduplication state.
    """

    @staticmethod
    def compute_exact_fingerprint(
        supplier_gstin: str,
        invoice_number: str,
        invoice_date: str,
        taxable_value: Any,
        recipient_gstin: str = "",
    ) -> str:
        """
        Exact Fingerprint: SHA-256 hash of (supplier_gstin | recipient_gstin | invoice_number | invoice_date | taxable_value).
        """
        s_gstin = str(supplier_gstin or "").strip().upper()
        r_gstin = str(recipient_gstin or "").strip().upper()
        inv_no = str(invoice_number or "").strip().upper()
        inv_dt = str(invoice_date or "").strip()
        t_val = f"{float(taxable_value or 0.0):.2f}"

        raw_key = f"{s_gstin}|{r_gstin}|{inv_no}|{inv_dt}|{t_val}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_potential_fingerprint(
        supplier_gstin: str,
        invoice_number: str,
        invoice_date: str,
    ) -> str:
        """
        Potential Fingerprint: SHA-256 hash of (supplier_gstin | invoice_number | invoice_date).
        Identifies potential duplicates where amounts or tax values slightly differ.
        """
        s_gstin = str(supplier_gstin or "").strip().upper()
        inv_no = str(invoice_number or "").strip().upper()
        inv_dt = str(invoice_date or "").strip()

        raw_key = f"{s_gstin}|{inv_no}|{inv_dt}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def evaluate_record(
        cls,
        supplier_gstin: str,
        invoice_number: str,
        invoice_date: str,
        taxable_value: Any,
        recipient_gstin: str = "",
        existing_exact_fps: Optional[Dict[str, str]] = None,
        existing_potential_fps: Optional[Dict[str, str]] = None,
    ) -> DuplicateCheckResult:
        """
        Evaluates record against existing fingerprint registries.
        `existing_exact_fps`: map of exact_fingerprint -> record_id
        `existing_potential_fps`: map of potential_fingerprint -> record_id
        """
        exact_fp = cls.compute_exact_fingerprint(
            supplier_gstin=supplier_gstin,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            taxable_value=taxable_value,
            recipient_gstin=recipient_gstin,
        )

        potential_fp = cls.compute_potential_fingerprint(
            supplier_gstin=supplier_gstin,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
        )

        exact_map = existing_exact_fps or {}
        potential_map = existing_potential_fps or {}

        if exact_fp in exact_map:
            matched_id = exact_map[exact_fp]
            return DuplicateCheckResult(
                status=DuplicateStatus.EXACT_DUPLICATE,
                exact_fingerprint=exact_fp,
                potential_fingerprint=potential_fp,
                matched_record_id=matched_id,
                description=f"Exact duplicate of record '{matched_id}' (identical supplier, invoice number, date, and taxable value).",
            )

        if potential_fp in potential_map:
            matched_id = potential_map[potential_fp]
            return DuplicateCheckResult(
                status=DuplicateStatus.POTENTIAL_DUPLICATE,
                exact_fingerprint=exact_fp,
                potential_fingerprint=potential_fp,
                matched_record_id=matched_id,
                description=f"Potential duplicate of record '{matched_id}' (matching supplier, invoice number, and date; verify amounts). Flagged for review.",
            )

        return DuplicateCheckResult(
            status=DuplicateStatus.UNIQUE,
            exact_fingerprint=exact_fp,
            potential_fingerprint=potential_fp,
            matched_record_id=None,
            description="Unique GST record.",
        )
