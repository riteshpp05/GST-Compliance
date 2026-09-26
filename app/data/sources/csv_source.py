"""
app.data.sources.csv_source
===========================
CSV Data Source Adapter for UC15 (Sprint 17).
Supports reading from file path, StringIO buffer, or raw CSV text.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, List, Optional, Union

from app.data.sources.base import DataSource, DataSourceMetadata, DataSourceType


class CSVDataSource(DataSource):
    """Concrete CSV Data Source Adapter."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        file_path: Optional[str] = None,
        csv_content: Optional[Union[str, bytes]] = None,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.file_path = file_path
        self.csv_content = csv_content
        self._connected = False

    def connect(self) -> bool:
        if self.file_path:
            import os
            self._connected = os.path.exists(self.file_path)
            return self._connected
        elif self.csv_content is not None:
            self._connected = True
            return True
        return False

    def fetch_records(self) -> List[Dict[str, Any]]:
        if not self._connected and not self.connect():
            raise ValueError(f"CSVDataSource '{self.source_name}' is not connected or accessible.")

        records: List[Dict[str, Any]] = []
        if self.file_path:
            with open(self.file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                records = [dict(row) for row in reader]
        elif self.csv_content is not None:
            content_str = (
                self.csv_content.decode("utf-8-sig")
                if isinstance(self.csv_content, bytes)
                else self.csv_content
            )
            f = io.StringIO(content_str)
            reader = csv.DictReader(f)
            records = [dict(row) for row in reader]

        return records

    def metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            source_id=self.source_id,
            source_type=DataSourceType.CSV,
            source_name=self.source_name,
            source_location=self.file_path or "IN_MEMORY_CSV",
        )
