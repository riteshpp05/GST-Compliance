"""
UC15 GST Compliance Agent — Data Ingestion & Source Metadata Models
Defines result structures for multi-source data ingestion, error tracking, and audit lineage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice


class IngestionStatus(str, Enum):
    """Lifecycle status of a record during ingestion and normalization."""
    VALID = "VALID"                       # Successfully parsed into canonical Invoice
    INVALID = "INVALID"                   # Corrupted or unparseable record
    INCOMPLETE = "INCOMPLETE"             # Required core fields missing
    UNSUPPORTED = "UNSUPPORTED"           # Source format or schema unsupported
    DATA_QUALITY_WARNING = "WARNING"      # Parseable, but has non-fatal data anomalies


@dataclass
class SourceMetadata:
    """Audit lineage and provenance for ingested records."""
    source_type: str = "unknown"          # excel | csv | json | mock | sap | datasphere | api
    source_name: str = ""
    source_file: Optional[str] = None
    source_sheet: Optional[str] = None
    source_record_id: Optional[str] = None
    source_location: Optional[str] = None
    additional_info: Dict[str, Any] = field(default_factory=dict)
    ingestion_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "source_file": self.source_file,
            "source_sheet": self.source_sheet,
            "source_record_id": self.source_record_id,
            "source_location": self.source_location,
            "additional_info": self.additional_info,
            "ingestion_timestamp": self.ingestion_timestamp,
        }


@dataclass
class IngestionRecordResult:
    """Result of attempting to ingest and normalize a single raw record."""
    record_index: int
    source_metadata: SourceMetadata
    status: IngestionStatus
    raw_data: Dict[str, Any] = field(default_factory=dict)
    invoice: Optional[Any] = None         # Canonical Invoice if valid
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.status in (IngestionStatus.VALID, IngestionStatus.DATA_QUALITY_WARNING) and self.invoice is not None


@dataclass
class IngestionBatchResult:
    """Aggregated outcome of an ingestion batch across all records."""
    source_name: str
    total_records: int = 0
    records: List[IngestionRecordResult] = field(default_factory=list)

    @property
    def valid_invoices(self) -> List[Any]:
        return [r.invoice for r in self.records if r.is_valid]

    @property
    def valid_count(self) -> int:
        return sum(1 for r in self.records if r.status == IngestionStatus.VALID)

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.records if r.status == IngestionStatus.DATA_QUALITY_WARNING)

    @property
    def invalid_count(self) -> int:
        return sum(1 for r in self.records if r.status in (IngestionStatus.INVALID, IngestionStatus.INCOMPLETE, IngestionStatus.UNSUPPORTED))

    @property
    def rejected_records(self) -> List[IngestionRecordResult]:
        return [r for r in self.records if not r.is_valid]

    def summary(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "total_records": self.total_records,
            "valid_count": self.valid_count,
            "warning_count": self.warning_count,
            "invalid_count": self.invalid_count,
            "success_rate": f"{(self.valid_count / self.total_records * 100):.1f}%" if self.total_records else "0%",
        }
