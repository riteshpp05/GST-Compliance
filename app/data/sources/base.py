"""
app.data.sources.base
=====================
Abstract Data Source Interface and Metadata contracts for UC15 (Sprint 17).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class DataSourceType(str, Enum):
    """Supported GST data source types."""
    CSV = "CSV"
    EXCEL = "EXCEL"
    JSON = "JSON"
    DICT_LIST = "DICT_LIST"
    ERP_EXPORT = "ERP_EXPORT"  # Export adapter only (e.g. SAP file export)


@dataclass
class DataSourceMetadata:
    """provenance metadata for a data source connection."""
    source_id: str
    source_type: DataSourceType
    source_name: str
    source_location: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    additional_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type.value,
            "source_name": self.source_name,
            "source_location": self.source_location,
            "created_at": self.created_at,
            "additional_info": self.additional_info,
        }


class DataSource(ABC):
    """
    Abstract Base Class for all GST Data Sources.
    Defines unified contract for connecting, fetching raw records, and capturing provenance.
    """

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection or validate readability of data source."""
        pass

    @abstractmethod
    def fetch_records(self) -> List[Dict[str, Any]]:
        """Fetch raw un-normalized records as a list of dictionaries."""
        pass

    @abstractmethod
    def metadata(self) -> DataSourceMetadata:
        """Return provenance metadata describing the data source."""
        pass
