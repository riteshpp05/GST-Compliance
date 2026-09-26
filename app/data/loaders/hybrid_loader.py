"""
UC15 GST Compliance Agent — Hybrid Invoice Loader
Combines live SAP S/4HANA OData V4 ERP records with statutory sandbox edge-cases
to achieve complete 10-scenario compliance verification without corrupting ERP master data.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional

from app.data.loaders.base import BaseInvoiceLoader
from app.data.loaders.s4hana_odata_loader import S4HanaODataInvoiceLoader
from app.data.loaders.csv_loader import CSVInvoiceLoader
from app.data.loaders.excel_loader import ExcelInvoiceLoader
from app.domain.models.ingestion import IngestionBatchResult, IngestionRecordResult
from app.domain.models.tax import HSNMaster
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class HybridInvoiceLoader(BaseInvoiceLoader):
    """
    Combines live SAP S/4HANA OData records with external statutory sandbox scenarios.
    Ensures complete coverage of all 6 compliance gates while anchoring on live ERP data.
    """

    def __init__(
        self,
        sap_loader: Optional[S4HanaODataInvoiceLoader] = None,
        statutory_loader: Optional[BaseInvoiceLoader] = None,
        statutory_file: Optional[str] = None,
    ):
        self.sap_loader = sap_loader or S4HanaODataInvoiceLoader()
        
        if statutory_loader:
            self.statutory_loader = statutory_loader
        else:
            default_csv = os.path.join("data", "UC15_GSTCompliance_100_Invoices.csv")
            default_xlsx = os.path.join("data", "UC15_GSTCompliance_Dataset.xlsx")
            target = statutory_file or (default_csv if os.path.exists(default_csv) else default_xlsx)
            
            if target.endswith(".csv"):
                self.statutory_loader = CSVInvoiceLoader(target)
            else:
                self.statutory_loader = ExcelInvoiceLoader(target)

    def load(self) -> IngestionBatchResult:
        logger.info("Executing Hybrid Ingestion: 1. SAP S/4HANA OData V4 + 2. Statutory Sandbox Dataset...")

        # 1. Load SAP records
        sap_batch = self.sap_loader.load()
        logger.info(f"Hybrid: Loaded {len(sap_batch.records)} records from SAP S/4HANA.")

        # 2. Load Statutory sandbox records
        statutory_batch = self.statutory_loader.load()
        logger.info(f"Hybrid: Loaded {len(statutory_batch.records)} records from Statutory Sandbox.")

        combined_records: List[IngestionRecordResult] = []
        idx = 0

        # Add SAP records
        for r in sap_batch.records:
            r.record_index = idx
            idx += 1
            combined_records.append(r)

        # Add Statutory sandbox records
        for r in statutory_batch.records:
            r.record_index = idx
            idx += 1
            combined_records.append(r)

        return IngestionBatchResult(
            source_name="Hybrid (SAP S/4HANA OData + Statutory Sandbox)",
            total_records=len(combined_records),
            records=combined_records,
        )

    def load_hsn_master(self) -> Dict[str, HSNMaster]:
        return self.statutory_loader.load_hsn_master()

    def load_state_codes(self) -> Dict[str, str]:
        return self.statutory_loader.load_state_codes()
