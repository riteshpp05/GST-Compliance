"""
UC15 GST Compliance Agent — CSV Data Loader (v2.0)
Robust CSV ingestion supporting encoding fallbacks, blank row skipping, duplicate tracking, and batch result reporting.
"""
from __future__ import annotations

import csv
import os
from typing import Dict, List, Optional, Set

from app.data.loaders.base import BaseInvoiceLoader
from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.domain.exceptions import DataLoadError
from app.domain.models.ingestion import (
    IngestionBatchResult,
    IngestionRecordResult,
    IngestionStatus,
    SourceMetadata,
)
from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CSVInvoiceLoader(BaseInvoiceLoader):
    """Loads invoices from standard delimited CSV files with rich error recovery."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path

    def load(self) -> IngestionBatchResult:
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        records: List[IngestionRecordResult] = []
        seen_invoice_ids: Set[str] = set()

        # Try multiple encodings
        encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
        content = None
        for enc in encodings:
            try:
                with open(self.csv_path, mode="r", encoding=enc) as f:
                    content = f.readlines()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            raise DataLoadError(f"Failed to decode CSV file with any supported encoding: {self.csv_path}")

        # Parse CSV lines
        reader = csv.DictReader(content)
        row_idx = 0
        for row in reader:
            row_idx += 1
            # Skip fully blank rows
            if not any(bool(v and str(v).strip()) for v in row.values()):
                continue

            inv_no = str(
                row.get("invoice_no")
                or row.get("invoice_number")
                or row.get("invoice_id")
                or row.get("Invoice")
                or ""
            ).strip()

            meta = SourceMetadata(
                source_type="csv",
                source_name=f"CSV:{os.path.basename(self.csv_path)}",
                source_file=self.csv_path,
                source_record_id=inv_no or f"row_{row_idx}",
            )

            rec_res = InvoiceNormalizer.normalize_record(row, source_metadata=meta, record_index=row_idx)

            # Duplicate check
            if inv_no:
                if inv_no in seen_invoice_ids:
                    rec_res.warnings.append(f"Duplicate invoice number '{inv_no}' encountered in CSV batch")
                    if rec_res.status == IngestionStatus.VALID:
                        rec_res.status = IngestionStatus.DATA_QUALITY_WARNING
                else:
                    seen_invoice_ids.add(inv_no)

            records.append(rec_res)

        batch_result = IngestionBatchResult(
            source_name=f"CSV:{os.path.basename(self.csv_path)}",
            total_records=len(records),
            records=records,
        )

        logger.info(
            f"Ingested CSV {self.csv_path}: {batch_result.valid_count}/{batch_result.total_records} "
            f"valid records ({batch_result.warning_count} warnings, {batch_result.invalid_count} rejected)."
        )
        return batch_result

    def load_invoices(self) -> List[Invoice]:
        return self.load().valid_invoices

    def load_hsn_master(self) -> Dict[str, HSNMaster]:
        return {}

    def load_state_codes(self) -> Dict[str, str]:
        return {}
