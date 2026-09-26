"""
UC15 GST Compliance Agent — JSON Data Loader (v2.0)
Loads invoices from JSON payloads, files, or API outputs supporting multiple document structures.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

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


class JSONInvoiceLoader(BaseInvoiceLoader):
    """Loads invoices from JSON files or raw JSON strings."""

    def __init__(self, json_path_or_content: str, is_content: bool = False):
        self.json_path_or_content = json_path_or_content
        self.is_content = is_content

    def load(self) -> IngestionBatchResult:
        if self.is_content:
            raw_text = self.json_path_or_content
            source_label = "JSON:raw_string"
        else:
            if not os.path.exists(self.json_path_or_content):
                raise FileNotFoundError(f"JSON file not found: {self.json_path_or_content}")
            source_label = f"JSON:{os.path.basename(self.json_path_or_content)}"
            try:
                with open(self.json_path_or_content, mode="r", encoding="utf-8") as f:
                    raw_text = f.read()
            except Exception as e:
                raise DataLoadError(f"Failed to read JSON file {self.json_path_or_content}: {e}") from e

        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise DataLoadError(f"Malformed JSON syntax: {e}") from e

        if isinstance(parsed, list):
            raw_items = parsed
        elif isinstance(parsed, dict):
            raw_items = parsed.get("invoices") or parsed.get("data") or parsed.get("records") or [parsed]
        else:
            raise DataLoadError(f"Unsupported JSON structure: expected list or object, got {type(parsed).__name__}")

        records: List[IngestionRecordResult] = []
        for idx, item in enumerate(raw_items, start=1):
            if not isinstance(item, dict):
                records.append(
                    IngestionRecordResult(
                        record_index=idx,
                        source_metadata=SourceMetadata(source_type="json", source_name=source_label),
                        status=IngestionStatus.UNSUPPORTED,
                        raw_data={"raw_item": str(item)},
                        errors=[f"Expected JSON object for record, got {type(item).__name__}"],
                    )
                )
                continue

            inv_id = str(item.get("invoice_no") or item.get("invoice_number") or f"json_rec_{idx}")
            meta = SourceMetadata(
                source_type="json",
                source_name=source_label,
                source_file=None if self.is_content else self.json_path_or_content,
                source_record_id=inv_id,
            )

            rec_res = InvoiceNormalizer.normalize_record(item, source_metadata=meta, record_index=idx)
            records.append(rec_res)

        batch_res = IngestionBatchResult(
            source_name=source_label,
            total_records=len(records),
            records=records,
        )

        logger.info(
            f"Ingested JSON ({source_label}): {batch_res.valid_count}/{batch_res.total_records} "
            f"valid records ({batch_res.warning_count} warnings, {batch_res.invalid_count} rejected)."
        )
        return batch_res

    def load_invoices(self) -> List[Invoice]:
        return self.load().valid_invoices

    def load_hsn_master(self) -> Dict[str, HSNMaster]:
        return {}

    def load_state_codes(self) -> Dict[str, str]:
        return {}
