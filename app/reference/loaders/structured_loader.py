"""
UC15 GST Compliance Agent — Structured Reference Loader
Loads, validates, and indexes externalized reference datasets from JSON/YAML sources.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import json
import os
from typing import Any, Dict, List, Optional

from app.infrastructure.logging import get_logger
from app.reference.models.base import BaseReferenceRecord
from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.repositories.in_memory import InMemoryReferenceRepository

logger = get_logger(__name__)


def _parse_date(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if not s or s.lower() == "null" or s.lower() == "none":
        return None
    # Parse ISO YYYY-MM-DD or DD/MM/YYYY
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: '{val}'")


class StructuredReferenceLoader:
    """
    Validating loader for statutory reference datasets.
    Guarantees structural schema compliance, date validation, and duplicate detection.
    """

    def __init__(self, repository: Optional[InMemoryReferenceRepository] = None):
        self.repository = repository or InMemoryReferenceRepository()
        self.validation_errors: List[str] = []

    def load_from_directory(self, base_dir: str) -> Dict[str, int]:
        """Load all reference subdirectories from base directory."""
        counts = {
            "hsn": 0,
            "tax_rates": 0,
            "states": 0,
            "ewb_policies": 0,
            "itc_policies": 0,
        }

        # 1. HSN Master
        hsn_path = os.path.join(base_dir, "hsn", "hsn_master.json")
        if os.path.exists(hsn_path):
            counts["hsn"] = self.load_hsn_file(hsn_path)

        # 2. Tax Rates
        tax_path = os.path.join(base_dir, "tax", "tax_rates.json")
        if os.path.exists(tax_path):
            counts["tax_rates"] = self.load_tax_rates_file(tax_path)

        # 3. States
        states_path = os.path.join(base_dir, "states", "states.json")
        if os.path.exists(states_path):
            counts["states"] = self.load_states_file(states_path)

        # 4. EWB Policies
        ewb_path = os.path.join(base_dir, "ewb", "ewb_policies.json")
        if os.path.exists(ewb_path):
            counts["ewb_policies"] = self.load_ewb_policies_file(ewb_path)

        # 5. ITC Policies
        itc_path = os.path.join(base_dir, "itc", "itc_policies.json")
        if os.path.exists(itc_path):
            counts["itc_policies"] = self.load_itc_policies_file(itc_path)

        logger.info(f"Loaded statutory reference catalog from {base_dir}: {counts}")
        return counts

    def load_hsn_file(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("hsn_records", data) if isinstance(data, dict) else data
        count = 0
        seen_ids = set()
        for idx, item in enumerate(records):
            ref_id = item.get("reference_id", f"HSN_AUTO_{idx}")
            if ref_id in seen_ids:
                raise ValueError(f"Duplicate reference_id detected in HSN file: {ref_id}")
            seen_ids.add(ref_id)

            rec = HSNReference(
                reference_id=ref_id,
                reference_type="HSN",
                version=item.get("version", "1.0"),
                effective_from=_parse_date(item.get("effective_from", "2017-07-01")),
                effective_to=_parse_date(item.get("effective_to")),
                status=item.get("status", "ACTIVE"),
                source=item.get("source", "OFFICIAL_GST"),
                source_reference=item.get("source_reference"),
                code=str(item.get("code", "")).strip(),
                description=str(item.get("description", "")).strip(),
                code_type=item.get("code_type", "HSN"),
                chapter=item.get("chapter"),
                heading=item.get("heading"),
                subheading=item.get("subheading"),
                tariff_item=item.get("tariff_item"),
                default_cgst_rate=Decimal(str(item["default_cgst_rate"])) if "default_cgst_rate" in item and item["default_cgst_rate"] is not None else None,
                default_sgst_rate=Decimal(str(item["default_sgst_rate"])) if "default_sgst_rate" in item and item["default_sgst_rate"] is not None else None,
                default_igst_rate=Decimal(str(item["default_igst_rate"])) if "default_igst_rate" in item and item["default_igst_rate"] is not None else None,
            )
            issues = rec.validate_integrity()
            if issues:
                raise ValueError(f"Integrity failure in HSN reference: {issues}")
            self.repository.add_hsn(rec)
            count += 1
        return count

    def load_tax_rates_file(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("tax_rate_records", data) if isinstance(data, dict) else data
        count = 0
        seen_ids = set()
        for idx, item in enumerate(records):
            ref_id = item.get("reference_id", f"TAX_AUTO_{idx}")
            if ref_id in seen_ids:
                raise ValueError(f"Duplicate reference_id in Tax Rates file: {ref_id}")
            seen_ids.add(ref_id)

            rec = TaxRateReference(
                reference_id=ref_id,
                reference_type="TAX_RATE",
                version=item.get("version", "1.0"),
                effective_from=_parse_date(item.get("effective_from", "2017-07-01")),
                effective_to=_parse_date(item.get("effective_to")),
                status=item.get("status", "ACTIVE"),
                source=item.get("source", "OFFICIAL_GST"),
                source_reference=item.get("source_reference"),
                hsn_code=str(item.get("hsn_code", "")).strip(),
                cgst_rate=Decimal(str(item.get("cgst_rate", "0.0"))),
                sgst_rate=Decimal(str(item.get("sgst_rate", "0.0"))),
                igst_rate=Decimal(str(item.get("igst_rate", "0.0"))),
                cess_rate=Decimal(str(item.get("cess_rate", "0.0"))),
                rate_type=item.get("rate_type", "STANDARD"),
                notification_no=item.get("notification_no"),
                description=item.get("description"),
            )
            issues = rec.validate_integrity()
            if issues:
                raise ValueError(f"Integrity failure in Tax Rate reference: {issues}")
            self.repository.add_tax_rate(rec)
            count += 1
        return count

    def load_states_file(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("state_records", data) if isinstance(data, dict) else data
        count = 0
        seen_ids = set()
        for idx, item in enumerate(records):
            ref_id = item.get("reference_id", f"STATE_AUTO_{idx}")
            if ref_id in seen_ids:
                raise ValueError(f"Duplicate reference_id in States file: {ref_id}")
            seen_ids.add(ref_id)

            rec = StateReference(
                reference_id=ref_id,
                reference_type="STATE",
                version=item.get("version", "1.0"),
                effective_from=_parse_date(item.get("effective_from", "2017-07-01")),
                effective_to=_parse_date(item.get("effective_to")),
                status=item.get("status", "ACTIVE"),
                source=item.get("source", "OFFICIAL_GST"),
                source_reference=item.get("source_reference"),
                state_code=str(item.get("state_code", "")).strip(),
                state_name=str(item.get("state_name", "")).strip(),
                state_or_ut=item.get("state_or_ut", "STATE"),
                tin_prefix=item.get("tin_prefix"),
            )
            issues = rec.validate_integrity()
            if issues:
                raise ValueError(f"Integrity failure in State reference: {issues}")
            self.repository.add_state(rec)
            count += 1
        return count

    def load_ewb_policies_file(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("ewb_policies", data) if isinstance(data, dict) else data
        count = 0
        seen_ids = set()
        for idx, item in enumerate(records):
            ref_id = item.get("policy_id", f"EWB_AUTO_{idx}")
            if ref_id in seen_ids:
                raise ValueError(f"Duplicate policy_id in EWB file: {ref_id}")
            seen_ids.add(ref_id)

            rec = EWBPolicyReference(
                reference_id=ref_id,
                policy_id=ref_id,
                reference_type="EWB_POLICY",
                version=item.get("version", "1.0"),
                effective_from=_parse_date(item.get("effective_from", "2018-04-01")),
                effective_to=_parse_date(item.get("effective_to")),
                status=item.get("status", "ACTIVE"),
                source=item.get("source", "OFFICIAL_GST"),
                source_reference=item.get("source_reference"),
                name=item.get("name", "National E-Way Bill Movement Policy"),
                threshold=Decimal(str(item.get("threshold", "50000.00"))),
                state_code=item.get("state_code"),
                interstate_threshold=Decimal(str(item["interstate_threshold"])) if "interstate_threshold" in item and item["interstate_threshold"] is not None else None,
                intrastate_threshold=Decimal(str(item["intrastate_threshold"])) if "intrastate_threshold" in item and item["intrastate_threshold"] is not None else None,
                exempted_hsn=item.get("exempted_hsn", []),
                description=item.get("description"),
            )
            issues = rec.validate_integrity()
            if issues:
                raise ValueError(f"Integrity failure in EWB policy: {issues}")
            self.repository.add_ewb_policy(rec)
            count += 1
        return count

    def load_itc_policies_file(self, file_path: str) -> int:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("itc_policies", data) if isinstance(data, dict) else data
        count = 0
        seen_ids = set()
        for idx, item in enumerate(records):
            ref_id = item.get("policy_id", f"ITC_AUTO_{idx}")
            if ref_id in seen_ids:
                raise ValueError(f"Duplicate policy_id in ITC file: {ref_id}")
            seen_ids.add(ref_id)

            rec = ITCPolicyReference(
                reference_id=ref_id,
                policy_id=ref_id,
                reference_type="ITC_POLICY",
                version=item.get("version", "1.0"),
                effective_from=_parse_date(item.get("effective_from", "2017-07-01")),
                effective_to=_parse_date(item.get("effective_to")),
                status=item.get("status", "ACTIVE"),
                source=item.get("source", "OFFICIAL_GST"),
                source_reference=item.get("source_reference", "Section 17(5) CGST Act"),
                category=item.get("category", "GENERAL"),
                blocked_keywords=item.get("blocked_keywords", []),
                is_blocked_17_5=item.get("is_blocked_17_5", False),
                blocked_reason=item.get("blocked_reason"),
                requires_2b_reconciliation=item.get("requires_2b_reconciliation", True),
                description=item.get("description"),
            )
            issues = rec.validate_integrity()
            if issues:
                raise ValueError(f"Integrity failure in ITC policy: {issues}")
            self.repository.add_itc_policy(rec)
            count += 1
        return count
