"""
app.data.sources
================
Data Source Abstractions & Concrete Source Adapters for UC15 (Sprint 17).
Supports CSV, Excel, JSON, Dict List, and ERP/SAP File Export sources.
"""

from app.data.sources.base import DataSource, DataSourceMetadata, DataSourceType
from app.data.sources.csv_source import CSVDataSource
from app.data.sources.excel_source import ExcelDataSource
from app.data.sources.json_source import JSONDataSource
from app.data.sources.erp_source import ERPExportDataSource
from app.data.sources.dict_source import DictListDataSource

__all__ = [
    "DataSource",
    "DataSourceMetadata",
    "DataSourceType",
    "CSVDataSource",
    "ExcelDataSource",
    "JSONDataSource",
    "ERPExportDataSource",
    "DictListDataSource",
]
