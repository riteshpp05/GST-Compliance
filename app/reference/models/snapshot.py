"""
UC15 GST Compliance Agent — Reference Snapshot Model
Captures the immutable snapshot of reference versions and records used to validate an invoice.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class FrozenSnapshotError(RuntimeError):
    """Raised when attempting to modify a frozen ReferenceSnapshot."""
    pass


class _FrozenDict(dict):
    """Dict wrapper that raises FrozenSnapshotError on modification."""
    def __setitem__(self, key: Any, value: Any) -> None:
        raise FrozenSnapshotError("Cannot modify dictionary of a frozen ReferenceSnapshot.")

    def __delitem__(self, key: Any) -> None:
        raise FrozenSnapshotError("Cannot delete items from dictionary of a frozen ReferenceSnapshot.")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise FrozenSnapshotError("Cannot pop items from dictionary of a frozen ReferenceSnapshot.")

    def popitem(self) -> Any:
        raise FrozenSnapshotError("Cannot pop items from dictionary of a frozen ReferenceSnapshot.")

    def clear(self) -> None:
        raise FrozenSnapshotError("Cannot clear dictionary of a frozen ReferenceSnapshot.")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise FrozenSnapshotError("Cannot update dictionary of a frozen ReferenceSnapshot.")

    def setdefault(self, key: Any, default: Any = None) -> Any:
        raise FrozenSnapshotError("Cannot setdefault on dictionary of a frozen ReferenceSnapshot.")


def _deep_freeze(obj: Any) -> Any:
    """Recursively freeze dictionaries into _FrozenDict instances."""
    if isinstance(obj, dict):
        return _FrozenDict({k: _deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(_deep_freeze(item) for item in obj)
    return obj


@dataclass
class ReferenceSnapshot:
    """
    Audit snapshot capturing the exact reference versions, IDs, and provenance utilized
    during compliance evaluation of an invoice.
    Enforces deep immutability once frozen.
    """
    invoice_id: str = "UNKNOWN"
    transaction_date: str = "2023-01-01"
    applicability_reason: Optional[str] = None
    source: Optional[str] = "OFFICIAL_GST"
    
    # Version tags of active references
    hsn_reference_version: Optional[str] = None
    hsn_reference_id: Optional[str] = None
    
    tax_rate_reference_version: Optional[str] = None
    tax_rate_reference_id: Optional[str] = None
    
    state_reference_version: Optional[str] = None
    state_reference_id: Optional[str] = None
    
    ewb_policy_version: Optional[str] = None
    ewb_policy_id: Optional[str] = None
    
    itc_policy_version: Optional[str] = None
    itc_policy_id: Optional[str] = None

    # Granular record-level metadata with full provenance
    resolved_records: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    unresolved: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    resolved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    _is_frozen: bool = field(default=False, repr=False)

    @classmethod
    def from_context(cls, context: Any, invoice: Optional[Any] = None) -> ReferenceSnapshot:
        inv_id = getattr(invoice, "invoice_no", getattr(invoice, "invoice_id", "UNKNOWN")) if invoice else "UNKNOWN"
        dt = str(getattr(invoice, "invoice_date", "2023-01-01")) if invoice else "2023-01-01"
        pos = getattr(invoice, "place_of_supply", None)
        reason = f"Invoice {inv_id} dated {dt}" + (f" (Place of Supply: {pos})" if pos else "")
        return cls(
            invoice_id=str(inv_id),
            transaction_date=str(dt),
            applicability_reason=reason,
            source="OFFICIAL_GST",
        )

    def set_metadata(self, key: str, value: Any) -> None:
        if getattr(self, "_is_frozen", False):
            raise FrozenSnapshotError(
                f"Cannot set metadata on frozen ReferenceSnapshot for invoice '{self.invoice_id}'."
            )
        self.metadata[key] = value

    def __setattr__(self, name: str, value: Any) -> None:
        if getattr(self, "_is_frozen", False) and name != "_is_frozen":
            raise FrozenSnapshotError(
                f"Cannot modify frozen ReferenceSnapshot for invoice '{self.invoice_id}'."
            )
        super().__setattr__(name, value)

    def __delattr__(self, name: str) -> None:
        if getattr(self, "_is_frozen", False):
            raise FrozenSnapshotError(
                f"Cannot delete attributes from frozen ReferenceSnapshot for invoice '{self.invoice_id}'."
            )
        super().__delattr__(name)

    def freeze(self) -> ReferenceSnapshot:
        """Freeze this snapshot and all nested dictionaries to prevent any subsequent modifications."""
        self.resolved_records = _deep_freeze(self.resolved_records)
        self.metadata = _deep_freeze(self.metadata)
        self.unresolved = _deep_freeze(self.unresolved)
        self._is_frozen = True
        return self

    @property
    def is_frozen(self) -> bool:
        """Return True if the snapshot has been frozen."""
        return self._is_frozen

    def record_resolution(
        self,
        reference_type: str,
        ref_id: str,
        version: str,
        details: Optional[Dict[str, Any]] = None,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        source: Optional[str] = None,
        source_reference: Optional[str] = None,
        resolution_status: str = "RESOLVED",
        applicability_reason: Optional[str] = None,
    ) -> None:
        """Record a reference resolution with rich provenance metadata into the snapshot."""
        if self._is_frozen:
            raise FrozenSnapshotError(
                f"Cannot record resolution on frozen ReferenceSnapshot for invoice '{self.invoice_id}'."
            )

        t = reference_type.upper()
        if t == "HSN":
            self.hsn_reference_id = ref_id
            self.hsn_reference_version = version
        elif t == "TAX_RATE":
            self.tax_rate_reference_id = ref_id
            self.tax_rate_reference_version = version
        elif t == "STATE":
            self.state_reference_id = ref_id
            self.state_reference_version = version
        elif t == "EWB_POLICY":
            self.ewb_policy_id = ref_id
            self.ewb_policy_version = version
        elif t == "ITC_POLICY":
            self.itc_policy_id = ref_id
            self.itc_policy_version = version

        reason = applicability_reason or (
            f"Active on transaction date {self.transaction_date} "
            f"(effective {effective_from or 'start'} to {effective_to or 'open-ended'})"
        )

        self.resolved_records[reference_type] = {
            "reference_id": ref_id,
            "reference_type": reference_type,
            "version": version,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "source": source or "OFFICIAL_GST",
            "source_reference": source_reference,
            "resolution_status": resolution_status,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "applicability_reason": reason,
            "details": details or {},
        }

    def record_unresolved(
        self,
        reference_type: str,
        identifier_or_status: Optional[str] = None,
        resolution_status: str = "NOT_FOUND",
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an unresolved (NOT_FOUND or CONFLICT) reference query for audit completeness."""
        if self._is_frozen:
            raise FrozenSnapshotError(
                f"Cannot record unresolved reference on frozen ReferenceSnapshot for invoice '{self.invoice_id}'."
            )
        known_statuses = {"NOT_FOUND", "CONFLICT", "RESOLVED", "EXPIRED", "FUTURE"}
        if identifier_or_status in known_statuses:
            status = identifier_or_status
            ident = (details or {}).get("identifier")
            actual_reason = resolution_status if resolution_status not in known_statuses else reason
        else:
            ident = identifier_or_status
            status = resolution_status
            actual_reason = reason

        record_entry = {
            "reference_id": None,
            "reference_type": reference_type,
            "identifier": ident,
            "version": None,
            "effective_from": None,
            "effective_to": None,
            "source": None,
            "source_reference": None,
            "resolution_status": status,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "applicability_reason": actual_reason or f"Resolution status: {status} on {self.transaction_date}",
            "details": details or {},
        }
        self.resolved_records[reference_type] = record_entry
        self.unresolved[reference_type] = {
            "identifier": ident,
            "status": status,
            "reason": actual_reason or f"Resolution status: {status}",
            "details": details or {},
        }

    def set_hsn(self, record: Any, resolution_status: str = "RESOLVED") -> None:
        """Record resolved HSN reference with provenance."""
        eff_from = str(getattr(record, "effective_from", "")) if getattr(record, "effective_from", None) else None
        eff_to = str(getattr(record, "effective_to", "")) if getattr(record, "effective_to", None) else None
        self.record_resolution(
            reference_type="HSN",
            ref_id=record.reference_id,
            version=record.version,
            details={
                "code": getattr(record, "code", ""),
                "description": getattr(record, "description", ""),
            },
            effective_from=eff_from,
            effective_to=eff_to,
            source=getattr(record, "source", None),
            source_reference=getattr(record, "source_reference", None),
            resolution_status=resolution_status,
            applicability_reason=f"HSN '{getattr(record, 'code', '')}' valid on transaction date {self.transaction_date} (v{record.version})",
        )

    def set_tax_rate(self, record: Any, resolution_status: str = "RESOLVED") -> None:
        """Record resolved Tax Rate reference with provenance."""
        eff_from = str(getattr(record, "effective_from", "")) if getattr(record, "effective_from", None) else None
        eff_to = str(getattr(record, "effective_to", "")) if getattr(record, "effective_to", None) else None
        self.record_resolution(
            reference_type="TAX_RATE",
            ref_id=record.reference_id,
            version=record.version,
            details={
                "hsn_code": getattr(record, "hsn_code", ""),
                "cgst_rate": str(getattr(record, "cgst_rate", "")),
                "sgst_rate": str(getattr(record, "sgst_rate", "")),
                "igst_rate": str(getattr(record, "igst_rate", "")),
            },
            effective_from=eff_from,
            effective_to=eff_to,
            source=getattr(record, "source", None),
            source_reference=getattr(record, "source_reference", None),
            resolution_status=resolution_status,
            applicability_reason=f"Statutory schedule for HSN '{getattr(record, 'hsn_code', '')}' active on {self.transaction_date} per {getattr(record, 'notification_no', 'schedule')}",
        )

    def set_state(self, record: Any, resolution_status: str = "RESOLVED") -> None:
        """Record resolved State reference with provenance."""
        eff_from = str(getattr(record, "effective_from", "")) if getattr(record, "effective_from", None) else None
        eff_to = str(getattr(record, "effective_to", "")) if getattr(record, "effective_to", None) else None
        self.record_resolution(
            reference_type="STATE",
            ref_id=record.reference_id,
            version=record.version,
            details={
                "state_code": getattr(record, "state_code", ""),
                "state_name": getattr(record, "state_name", ""),
            },
            effective_from=eff_from,
            effective_to=eff_to,
            source=getattr(record, "source", None),
            source_reference=getattr(record, "source_reference", None),
            resolution_status=resolution_status,
            applicability_reason=f"GST state code '{getattr(record, 'state_code', '')}' mapped to '{getattr(record, 'state_name', '')}'",
        )

    def set_policy(self, policy_type: str, record: Any, resolution_status: str = "RESOLVED") -> None:
        """Record resolved policy reference (EWB, ITC, etc.) with provenance."""
        ref_type = "EWB_POLICY" if "ewb" in policy_type.lower() else ("ITC_POLICY" if "itc" in policy_type.lower() else policy_type.upper())
        eff_from = str(getattr(record, "effective_from", "")) if getattr(record, "effective_from", None) else None
        eff_to = str(getattr(record, "effective_to", "")) if getattr(record, "effective_to", None) else None
        self.record_resolution(
            reference_type=ref_type,
            ref_id=record.reference_id,
            version=record.version,
            details={
                "policy_id": getattr(record, "policy_id", record.reference_id),
                "name": getattr(record, "name", getattr(record, "category", "")),
            },
            effective_from=eff_from,
            effective_to=eff_to,
            source=getattr(record, "source", None),
            source_reference=getattr(record, "source_reference", None),
            resolution_status=resolution_status,
            applicability_reason=f"Policy '{getattr(record, 'policy_id', record.reference_id)}' effective on {self.transaction_date}",
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["is_frozen"] = self._is_frozen
        # Unpack _FrozenDict to normal dict if necessary
        if isinstance(d.get("resolved_records"), _FrozenDict):
            d["resolved_records"] = dict(d["resolved_records"])
        return d


