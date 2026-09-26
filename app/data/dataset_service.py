"""
UC15 GST Compliance Agent — Dataset Management Service
Handles registration, validation, storage, registry persistence, and active dataset switching.
Supports Excel (.xlsx, .xls), CSV (.csv), and JSON (.json) format datasets.
"""
from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.data.loaders.base import BaseInvoiceLoader
from app.data.loaders.csv_loader import CSVInvoiceLoader
from app.data.loaders.excel_loader import ExcelInvoiceLoader
from app.data.loaders.json_loader import JSONInvoiceLoader
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEFAULT_DATASET_ID = "DS-SYNTHETIC-DEFAULT"
DEFAULT_DATASET_PATH = os.path.join("data", "UC15_GSTCompliance_Dataset.xlsx")


class DatasetService:
    """
    Manages invoice datasets in the platform.
    Persists registry state in data/datasets/registry.json.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.root_dir = base_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.datasets_dir = os.path.join(self.root_dir, "data", "datasets")
        self.uploads_dir = os.path.join(self.root_dir, "data", "uploads")
        self.registry_file = os.path.join(self.datasets_dir, "registry.json")

        os.makedirs(self.datasets_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)

        self._ensure_registry_exists()

    def _ensure_registry_exists(self) -> None:
        """Initializes default registry if not present."""
        if not os.path.exists(self.registry_file):
            default_entry = {
                "id": DEFAULT_DATASET_ID,
                "name": "Synthetic GST Benchmark Dataset (100 Invoices)",
                "file_name": "UC15_GSTCompliance_Dataset.xlsx",
                "file_path": DEFAULT_DATASET_PATH,
                "file_format": "EXCEL",
                "size_bytes": os.path.getsize(os.path.join(self.root_dir, DEFAULT_DATASET_PATH))
                if os.path.exists(os.path.join(self.root_dir, DEFAULT_DATASET_PATH))
                else 0,
                "upload_timestamp": datetime.now(timezone.utc).isoformat(),
                "uploaded_by": "System Benchmark",
                "invoice_count": 99,
                "hsn_master_count": 10,
                "state_code_count": 12,
                "status": "VALIDATED",
                "is_active": True,
                "is_deletable": False,
            }
            self._save_registry([default_entry])

    def _load_registry(self) -> List[Dict[str, Any]]:
        """Reads datasets from registry file."""
        if not os.path.exists(self.registry_file):
            self._ensure_registry_exists()
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read dataset registry: {e}")
            self._ensure_registry_exists()
            return []

    def _save_registry(self, datasets: List[Dict[str, Any]]) -> None:
        """Writes dataset list to registry file."""
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(datasets, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save dataset registry: {e}")

    def list_datasets(self) -> List[Dict[str, Any]]:
        """List all registered datasets."""
        datasets = self._load_registry()
        # Ensure relative/absolute paths resolve properly
        for d in datasets:
            d["exists_on_disk"] = os.path.exists(os.path.join(self.root_dir, d["file_path"]))
        return datasets

    def get_active_dataset(self) -> Dict[str, Any]:
        """Get the currently active dataset."""
        datasets = self.list_datasets()
        for d in datasets:
            if d.get("is_active"):
                return d
        # Fallback to default if no active dataset found
        if datasets:
            datasets[0]["is_active"] = True
            self._save_registry(datasets)
            return datasets[0]
        return {}

    def get_active_file_path(self) -> str:
        """Get full absolute or relative file path for the active dataset."""
        active = self.get_active_dataset()
        rel_path = active.get("file_path", DEFAULT_DATASET_PATH)
        full_path = os.path.join(self.root_dir, rel_path)
        if os.path.exists(full_path):
            return full_path
        # Return fallback if active missing
        return os.path.join(self.root_dir, DEFAULT_DATASET_PATH)

    def set_active_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """Sets target dataset as active and deactivates others."""
        datasets = self._load_registry()
        target = None
        for d in datasets:
            if d["id"] == dataset_id:
                d["is_active"] = True
                target = d
            else:
                d["is_active"] = False

        if not target:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        self._save_registry(datasets)
        logger.info(f"Active dataset switched to '{target['name']}' ({target['id']})")
        return target

    def validate_and_register_file(
        self,
        file_path: str,
        original_filename: str,
        custom_name: Optional[str] = None,
        uploaded_by: str = "User",
        set_active: bool = True,
    ) -> Dict[str, Any]:
        """
        Runs ingestion dry-run on a file, extracts validation metrics,
        and registers dataset in storage.
        """
        ext = os.path.splitext(original_filename)[1].lower()
        if ext in [".xlsx", ".xls"]:
            format_name = "EXCEL"
            loader: BaseInvoiceLoader = ExcelInvoiceLoader(excel_path=file_path)
        elif ext == ".csv":
            format_name = "CSV"
            loader = CSVInvoiceLoader(file_path)
        elif ext == ".json":
            format_name = "JSON"
            loader = JSONInvoiceLoader(file_path)
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Must be .csv, .xlsx, .xls, or .json")

        # Perform dry run load
        try:
            batch_result = loader.load()
            hsn_master = loader.load_hsn_master()
            state_codes = loader.load_state_codes()
        except Exception as e:
            logger.error(f"Ingestion dry-run failed for '{original_filename}': {e}")
            raise ValueError(f"Failed to parse and validate file contents: {str(e)}") from e

        if not batch_result.valid_invoices and not batch_result.rejected_records:
            raise ValueError(f"File '{original_filename}' contains no recognizable invoice records.")

        dataset_id = f"DS-UP-{uuid.uuid4().hex[:8].upper()}"
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

        rel_path = os.path.relpath(file_path, self.root_dir)

        new_dataset = {
            "id": dataset_id,
            "name": custom_name or original_filename,
            "file_name": original_filename,
            "file_path": rel_path,
            "file_format": format_name,
            "size_bytes": file_size,
            "upload_timestamp": datetime.now(timezone.utc).isoformat(),
            "uploaded_by": uploaded_by,
            "invoice_count": len(batch_result.valid_invoices),
            "hsn_master_count": len(hsn_master),
            "state_code_count": len(state_codes),
            "warnings_count": batch_result.warning_count,
            "rejected_count": len(batch_result.rejected_records),
            "status": "VALIDATED" if not batch_result.rejected_records else "PARTIAL_VALIDATED",
            "is_active": False,
            "is_deletable": True,
        }

        datasets = self._load_registry()
        datasets.append(new_dataset)
        self._save_registry(datasets)

        if set_active:
            self.set_active_dataset(dataset_id)
            new_dataset["is_active"] = True

        return new_dataset

    def delete_dataset(self, dataset_id: str) -> bool:
        """Deletes a custom uploaded dataset and cleans up disk file."""
        datasets = self._load_registry()
        target = None
        remaining = []

        for d in datasets:
            if d["id"] == dataset_id:
                target = d
            else:
                remaining.append(d)

        if not target:
            raise ValueError(f"Dataset '{dataset_id}' not found.")

        if not target.get("is_deletable", True) or target["id"] == DEFAULT_DATASET_ID:
            raise ValueError("The default benchmark dataset cannot be deleted.")

        # Remove file if inside uploads directory
        full_path = os.path.join(self.root_dir, target["file_path"])
        if os.path.exists(full_path) and "uploads" in full_path:
            try:
                os.remove(full_path)
            except Exception as e:
                logger.warning(f"Failed to remove file '{full_path}': {e}")

        # If deleted dataset was active, make default active
        was_active = target.get("is_active", False)
        if was_active:
            for r in remaining:
                if r["id"] == DEFAULT_DATASET_ID:
                    r["is_active"] = True

        self._save_registry(remaining)
        logger.info(f"Deleted dataset '{target['name']}' ({dataset_id})")
        return True
