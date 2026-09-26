"""
UC15 GST Compliance Agent — Base Reference Domain Model
Foundational contract for version-controlled, effective-date bounded statutory reference entities.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class BaseReferenceRecord:
    """
    Standard base contract for all statutory reference records.
    Provides strict versioning, temporal bounding (effective_from / effective_to),
    and source provenance.
    """
    reference_id: str = ""
    reference_type: str = ""
    version: str = "1.0"
    effective_from: date = field(default_factory=lambda: date(2017, 7, 1))
    effective_to: Optional[date] = None
    status: str = "ACTIVE"                                  # ACTIVE | INACTIVE | SUPERSEDED
    source: str = "OFFICIAL_GST"
    source_reference: Optional[str] = None                  # e.g. Notification 01/2017-CT(R)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_active_on(self, target_date: date) -> bool:
        """Check if this reference is legally active on a specific transaction date."""
        if self.status.upper() != "ACTIVE":
            return False
        if target_date < self.effective_from:
            return False
        if self.effective_to is not None and target_date > self.effective_to:
            return False
        return True

    def validate_integrity(self) -> List[str]:
        """Perform data quality validation on the reference record itself."""
        issues: List[str] = []
        if not self.reference_id or not str(self.reference_id).strip():
            issues.append(f"[{self.reference_type}] Missing or empty reference_id")
        if not self.version or not str(self.version).strip():
            issues.append(f"[{self.reference_id}] Missing version tag")
        if self.effective_from is None:
            issues.append(f"[{self.reference_id}] Missing effective_from date")
        if self.effective_to is not None and self.effective_from is not None:
            if self.effective_to < self.effective_from:
                issues.append(
                    f"[{self.reference_id}] Invalid date window: effective_from must be on or before effective_to "
                    f"(effective_to {self.effective_to} < effective_from {self.effective_from})"
                )
        if self.status.upper() not in ("ACTIVE", "INACTIVE", "SUPERSEDED"):
            issues.append(f"[{self.reference_id}] Invalid reference status: {self.status}")
        return issues

    def to_dict(self) -> Dict[str, Any]:
        """Serialize reference record to dictionary."""
        return asdict(self)
