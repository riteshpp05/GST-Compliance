"""
UC15 GST Compliance Agent — Base Invoice Loader Interface (v2.0)
Defines unified loader contract returning structured IngestionBatchResult across all source adapters.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.domain.models.ingestion import IngestionBatchResult
from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster


class BaseInvoiceLoader(ABC):
    """
    Abstract base loader for all source adapters (Excel, CSV, JSON, Mock, SAP, DataSphere).
    Ensures unified contract and non-crashing batch ingestion.
    """

    @abstractmethod
    def load(self) -> IngestionBatchResult:
        """
        Execute ingestion and normalization for the source.
        Returns an IngestionBatchResult detailing valid invoices, warnings, and rejected records.
        """

    def load_invoices(self) -> List[Invoice]:
        """
        Convenience method returning valid canonical invoices.
        Maintains backward compatibility with Sprint 1.
        """
        return self.load().valid_invoices

    def load_hsn_master(self) -> Dict[str, HSNMaster]:
        """Load official HSN master data if available from this source."""
        return {}

    def load_state_codes(self) -> Dict[str, str]:
        """Load GSTIN state code reference if available from this source."""
        return {}
