"""
app.data.sources.erp_source
===========================
ERP/SAP File Export Data Source Adapter for UC15 (Sprint 17).

CRITICAL RULE:
ERP/SAP = FILE/DATA EXPORT ADAPTER ONLY.
No live SAP integration, OData, RFC, BAPI, or mutation calls.
"""

from __future__ import annotations

import csv
import json
from typing import Any, Dict, List, Optional, Union

from app.data.sources.base import DataSource, DataSourceMetadata, DataSourceType


class ERPExportDataSource(DataSource):
    """
    Adapter for parsing exported ERP/SAP files (CSV, JSON, XML-converted dicts).
    Treats ERP data as passive export snapshots for ingestion.
    """

    def __init__(
        self,
        source_id: str,
        source_name: str,
        system_type: str = "SAP_S4HANA_EXPORT",
        export_file_path: Optional[str] = None,
        raw_export_data: Optional[Union[str, List[Dict[str, Any]]]] = None,
    ):
        self.source_id = source_id
        self.source_name = source_name
        self.system_type = system_type
        self.export_file_path = export_file_path
        self.raw_export_data = raw_export_data
        self._connected = False

    def connect(self) -> bool:
        if self.export_file_path:
            import os
            self._connected = os.path.exists(self.export_file_path)
            return self._connected
        elif self.raw_export_data is not None:
            self._connected = True
            return True
        return False

    def fetch_records(self) -> List[Dict[str, Any]]:
        if not self._connected and not self.connect():
            raise ValueError(f"ERPExportDataSource '{self.source_name}' is not accessible.")

        if self.raw_export_data is not None:
            if isinstance(self.raw_export_data, list):
                return self.raw_export_data
            elif isinstance(self.raw_export_data, str):
                try:
                    parsed = json.loads(self.raw_export_data)
                    return parsed if isinstance(parsed, list) else [parsed]
                except json.JSONDecodeError:
                    lines = self.raw_export_data.strip().split("\n")
                    reader = csv.DictReader(lines)
                    return [dict(r) for r in reader]

        if self.export_file_path:
            if self.export_file_path.endswith(".json"):
                with open(self.export_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, list) else [data]
            else:
                with open(self.export_file_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    return [dict(r) for r in reader]

        return []

    def metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            source_id=self.source_id,
            source_type=DataSourceType.ERP_EXPORT,
            source_name=self.source_name,
            source_location=self.export_file_path or "ERP_EXPORT_PAYLOAD",
            additional_info={"system_type": self.system_type},
        )
