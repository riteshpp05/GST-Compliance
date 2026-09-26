"""
UC15 GST Compliance Agent — Mock Data Provider
Generates controlled, deterministic test invoices representing all compliance and data-quality scenarios.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.data.loaders.base import BaseInvoiceLoader
from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.domain.models.ingestion import IngestionBatchResult, IngestionRecordResult, SourceMetadata
from app.domain.models.invoice import Invoice
from app.domain.models.tax import HSNMaster


class MockInvoiceLoader(BaseInvoiceLoader):
    """
    Mock source adapter providing deterministic compliance test scenarios.
    Source-agnostic adapter for unit testing, CI pipelines, and demo verification.
    """

    def __init__(self, scenario_filter: Optional[List[str]] = None):
        self.scenario_filter = scenario_filter

    def _generate_mock_records(self) -> List[Dict[str, Any]]:
        try:
            from scripts.generate_100_invoices_dataset import generate_100_records
            recs = generate_100_records()
            # map keys for compatibility
            mapped = []
            for r in recs:
                r_copy = dict(r)
                r_copy["scenario"] = r_copy.get("test_category", "MOCK")
                mapped.append(r_copy)
            if self.scenario_filter:
                return [s for s in mapped if s.get("scenario") in self.scenario_filter]
            return mapped
        except Exception:
            # Fallback legacy 12 scenarios if script import fails
            scenarios = [
                {
                    "scenario": "CLEAN_AR",
                    "invoice_no": "INV-MOCK-001",
                    "invoice_date": "2026-03-01",
                    "direction": "AR",
                    "counterparty_gstin": "27AAACB1234A1ZJ",
                    "counterparty_name": "Bosch India Ltd",
                    "place_of_supply": "Maharashtra",
                    "hsn_code": "8409",
                    "item_desc": "Engine parts supply per contract",
                    "taxable_value_inr": 35000.0,
                    "cgst_rate": 9.0,
                    "sgst_rate": 9.0,
                    "igst_rate": 0.0,
                    "total_amt": 41300.0,
                    "eway_bill_status": "",
                    "gstr2b_reflected": True,
                },
                {
                    "scenario": "CLEAN_AP",
                    "invoice_no": "INV-MOCK-002",
                    "invoice_date": "2026-03-02",
                    "direction": "AP",
                    "counterparty_gstin": "07AAACH8901C1Z1",
                    "counterparty_name": "Hero MotoCorp Ltd",
                    "place_of_supply": "Delhi",
                    "hsn_code": "8409",
                    "item_desc": "Transmission components",
                    "taxable_value_inr": 45000.0,
                    "cgst_rate": 0.0,
                    "sgst_rate": 0.0,
                    "igst_rate": 18.0,
                    "total_amt": 53100.0,
                    "eway_bill_status": "",
                    "gstr2b_reflected": True,
                }
            ]
            if self.scenario_filter:
                return [s for s in scenarios if s.get("scenario") in self.scenario_filter]
            return scenarios

    def load(self) -> IngestionBatchResult:
        raw_list = self._generate_mock_records()
        records: List[IngestionRecordResult] = []

        for idx, item in enumerate(raw_list, start=1):
            inv_no = item.get("invoice_no") or f"mock_{idx}"
            meta = SourceMetadata(
                source_type="mock",
                source_name="MockDataProvider",
                source_record_id=inv_no,
            )
            rec_res = InvoiceNormalizer.normalize_record(item, source_metadata=meta, record_index=idx)
            records.append(rec_res)

        return IngestionBatchResult(
            source_name="MockInvoiceLoader",
            total_records=len(records),
            records=records,
        )

    def load_invoices(self) -> List[Invoice]:
        return self.load().valid_invoices

    def load_hsn_master(self) -> Dict[str, HSNMaster]:
        return {
            "8409": HSNMaster.from_raw("8409", "Parts for Internal Combustion Engines", 9, 9, 18),
            "8483": HSNMaster.from_raw("8483", "Transmission Shafts & Cranks", 9, 9, 18),
            "8708": HSNMaster.from_raw("8708", "Motor Vehicle Parts & Accessories", 14, 14, 28),
            "8536": HSNMaster.from_raw("8536", "Electrical Switches & Connectors", 9, 9, 18),
            "7318": HSNMaster.from_raw("7318", "Screws, Bolts, Nuts (Iron/Steel)", 9, 9, 18),
            "3926": HSNMaster.from_raw("3926", "Plastic Articles NES", 9, 9, 18),
            "8501": HSNMaster.from_raw("8501", "Electric Motors & Generators", 9, 9, 18),
            "4819": HSNMaster.from_raw("4819", "Cartons, Boxes, Cases (Paper)", 6, 6, 12),
            "9983": HSNMaster.from_raw("9983", "Other Professional/Technical Services", 9, 9, 18),
            "9954": HSNMaster.from_raw("9954", "Construction Services", 9, 9, 18),
        }

    def load_state_codes(self) -> Dict[str, str]:
        return {
            "27": "Maharashtra",
            "07": "Delhi",
            "29": "Karnataka",
            "33": "Tamil Nadu",
            "06": "Haryana",
            "24": "Gujarat",
            "09": "Uttar Pradesh",
            "19": "West Bengal",
            "36": "Telangana",
            "32": "Kerala",
            "23": "Madhya Pradesh",
            "21": "Odisha",
        }
