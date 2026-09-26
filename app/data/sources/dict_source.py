"""
app.data.sources.dict_source
============================
In-Memory Dict List Data Source Adapter for UC15 (Sprint 17).
Allows feeding raw dictionary records directly into the ingestion pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.sources.base import DataSource, DataSourceMetadata, DataSourceType


class DictListDataSource(DataSource):
    """Concrete Dict List Data Source Adapter for in-memory dictionaries."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        records: Optional[List[Dict[str, Any]]] = None,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.raw_records = records or []
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def fetch_records(self) -> List[Dict[str, Any]]:
        return self.raw_records

    def metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            source_id=self.source_id,
            source_type=DataSourceType.DICT_LIST,
            source_name=self.source_name,
            source_location="in_memory_dict_list",
            additional_info={"record_count": len(self.raw_records)},
        )
