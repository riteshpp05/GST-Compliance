"""
UC15 GST Compliance Agent — In-Memory Reference Repository
High-performance in-memory repository with indexed candidate lookups.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
class InMemoryReferenceRepository:
    """
    Thread-safe in-memory store for reference records.
    Provides fast indexed queries by entity code or classification key.
    """

    def __init__(self):
        self._hsn_by_code: Dict[str, List[HSNReference]] = {}
        self._tax_by_hsn: Dict[str, List[TaxRateReference]] = {}
        self._states_by_code: Dict[str, List[StateReference]] = {}
        self._ewb_policies: List[EWBPolicyReference] = []
        self._itc_policies: List[ITCPolicyReference] = []

    def add_hsn(self, record: HSNReference) -> None:
        code = str(record.code).strip()
        self._hsn_by_code.setdefault(code, []).append(record)

    def add_tax_rate(self, record: TaxRateReference) -> None:
        hsn = str(record.hsn_code).strip()
        self._tax_by_hsn.setdefault(hsn, []).append(record)

    def add_state(self, record: StateReference) -> None:
        code = str(record.state_code).strip().zfill(2)
        self._states_by_code.setdefault(code, []).append(record)

    def add_ewb_policy(self, record: EWBPolicyReference) -> None:
        self._ewb_policies.append(record)

    def add_itc_policy(self, record: ITCPolicyReference) -> None:
        self._itc_policies.append(record)

    def get_hsn_candidates(self, code: str) -> List[HSNReference]:
        clean_code = str(code).strip()
        # Direct exact match
        if clean_code in self._hsn_by_code:
            return list(self._hsn_by_code[clean_code])
        # Hierarchical prefix match (e.g. 8-digit tariff item falling back to 4-digit heading)
        for length in (6, 4, 2):
            if len(clean_code) > length:
                prefix = clean_code[:length]
                if prefix in self._hsn_by_code:
                    return list(self._hsn_by_code[prefix])
        return []

    def get_tax_rate_candidates(self, hsn_code: str) -> List[TaxRateReference]:
        clean_code = str(hsn_code).strip()
        if clean_code in self._tax_by_hsn:
            return list(self._tax_by_hsn[clean_code])
        # Hierarchical fallback for rates
        for length in (6, 4, 2):
            if len(clean_code) > length:
                prefix = clean_code[:length]
                if prefix in self._tax_by_hsn:
                    return list(self._tax_by_hsn[prefix])
        return []

    def get_state_candidates(self, state_code: str) -> List[StateReference]:
        clean = str(state_code).strip().zfill(2)
        return list(self._states_by_code.get(clean, []))

    def get_ewb_policy_candidates(self, state_code: Optional[str] = None) -> List[EWBPolicyReference]:
        if state_code:
            clean_state = str(state_code).strip().zfill(2)
            if clean_state:
                state_specific = [p for p in self._ewb_policies if p.state_code and str(p.state_code).strip().zfill(2) == clean_state]
                national = self.get_national_ewb_policies()
                return state_specific + national
        # Default to national policies
        return self.get_national_ewb_policies()

    def get_state_ewb_policies(self, state_code: str) -> List[EWBPolicyReference]:
        clean_state = str(state_code).strip().zfill(2)
        return [p for p in self._ewb_policies if p.state_code and str(p.state_code).strip().zfill(2) == clean_state]

    def get_national_ewb_policies(self) -> List[EWBPolicyReference]:
        return [
            p for p in self._ewb_policies
            if p.state_code is None or str(p.state_code).strip().upper() in ("NATIONAL", "ALL", "")
        ]

    def add_legacy_hsn(self, record: HSNReference) -> None:
        """Add legacy HSN record without overriding existing official statutory records."""
        code = str(record.code).strip()
        existing = self._hsn_by_code.get(code, [])
        if not any(r.source == "OFFICIAL_GST" for r in existing):
            self._hsn_by_code.setdefault(code, []).append(record)

    def add_legacy_tax_rate(self, record: TaxRateReference) -> None:
        """Add legacy tax rate record without overriding existing official statutory records."""
        hsn = str(record.hsn_code).strip()
        existing = self._tax_by_hsn.get(hsn, [])
        if not any(r.source == "OFFICIAL_GST" for r in existing):
            self._tax_by_hsn.setdefault(hsn, []).append(record)

    def add_legacy_state(self, record: StateReference) -> None:
        """Add legacy state record without overriding existing official statutory records."""
        code = str(record.state_code).strip().zfill(2)
        existing = self._states_by_code.get(code, [])
        if not any(r.source == "OFFICIAL_GST" for r in existing):
            self._states_by_code.setdefault(code, []).append(record)

    def set_hsn_override(self, record: HSNReference) -> None:
        code = str(record.code).strip()
        self._hsn_by_code[code] = [record]

    def set_tax_rate_override(self, record: TaxRateReference) -> None:
        hsn = str(record.hsn_code).strip()
        self._tax_by_hsn[hsn] = [record]

    def set_state_override(self, record: StateReference) -> None:
        code = str(record.state_code).strip().zfill(2)
        self._states_by_code[code] = [record]

    def get_itc_policy_candidates(self) -> List[ITCPolicyReference]:
        return list(self._itc_policies)

    def get_itc_policies(self) -> List[ITCPolicyReference]:
        return list(self._itc_policies)

    def list_all_hsn(self) -> List[HSNReference]:
        records: List[HSNReference] = []
        for lst in self._hsn_by_code.values():
            records.extend(lst)
        return records

    def list_all_states(self) -> List[StateReference]:
        records: List[StateReference] = []
        for lst in self._states_by_code.values():
            records.extend(lst)
        return records

    def clear(self) -> None:
        self._hsn_by_code.clear()
        self._tax_by_hsn.clear()
        self._states_by_code.clear()
        self._ewb_policies.clear()
        self._itc_policies.clear()

