"""
app.data.sources.json_source
============================
JSON Data Source Adapter for UC15 (Sprint 17).
Supports reading from file path, JSON string/bytes, or in-memory dict list.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Union

from app.data.sources.base import DataSource, DataSourceMetadata, DataSourceType


class JSONDataSource(DataSource):
    """Concrete JSON Data Source Adapter."""

    def __init__(
        self,
        source_id: str,
        source_name: str,
        file_path: Optional[str] = None,
        json_content: Optional[Union[str, bytes, List[Dict[str, Any]]]] = None,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.file_path = file_path
        self.json_content = json_content
        self._connected = False

    def connect(self) -> bool:
        if self.file_path:
            import os
            self._connected = os.path.exists(self.file_path)
            return self._connected
        elif self.json_content is not None:
            self._connected = True
            return True
        return False

    def fetch_records(self) -> List[Dict[str, Any]]:
        if not self._connected and not self.connect():
            raise ValueError(f"JSONDataSource '{self.source_name}' is not connected or accessible.")

        if self.file_path:
            with open(self.file_path, mode="r", encoding="utf-8") as f:
                data = json.load(f)
        elif isinstance(self.json_content, list):
            data = self.json_content
        elif isinstance(self.json_content, (str, bytes)):
            content_str = (
                self.json_content.decode("utf-8")
                if isinstance(self.json_content, bytes)
                else self.json_content
            )
            data = json.loads(content_str)
        else:
            return []

        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict)]
        elif isinstance(data, dict):
            if "invoices" in data and isinstance(data["invoices"], list):
                return [d for d in data["invoices"] if isinstance(d, dict)]
            elif "records" in data and isinstance(data["records"], list):
                return [d for d in data["records"] if isinstance(d, dict)]
            return [data]
        return []

    def metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            source_id=self.source_id,
            source_type=DataSourceType.JSON if self.file_path else DataSourceType.DICT_LIST,
            source_name=self.source_name,
            source_location=self.file_path or "IN_MEMORY_JSON",
        )
