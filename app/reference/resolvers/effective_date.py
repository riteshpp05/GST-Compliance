"""
UC15 GST Compliance Agent — Effective-Date Resolver
Deterministic temporal resolution engine for version-controlled statutory references.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Generic, List, Optional, TypeVar

from app.reference.models.base import BaseReferenceRecord

T = TypeVar("T", bound=BaseReferenceRecord)


class ResolutionStatus(str, Enum):
    """Status outcomes from effective-date reference resolution."""
    RESOLVED = "RESOLVED"                                  # Exactly 1 active reference found
    NOT_FOUND = "NOT_FOUND"                                # 0 active references valid on target date
    CONFLICT = "CONFLICT"                                  # > 1 active references valid on target date
    INVALID_REFERENCE = "INVALID_REFERENCE"                # Reference record has malformed date range or integrity error


@dataclass
class ResolutionResult(Generic[T]):
    """
    Structured, explainable outcome of resolving an effective-date reference.
    """
    status: ResolutionStatus
    resolution_date: date
    reference: Optional[T] = None
    reference_id: Optional[str] = None
    reference_version: Optional[str] = None
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None
    source: Optional[str] = None
    reason: Optional[str] = None
    candidates: List[T] = field(default_factory=list)

    @property
    def is_resolved(self) -> bool:
        return self.status == ResolutionStatus.RESOLVED and self.reference is not None

    @property
    def record(self) -> Optional[T]:
        """Convenience alias for the resolved reference record."""
        return self.reference

    @property
    def is_conflict(self) -> bool:
        return self.status == ResolutionStatus.CONFLICT

    @property
    def is_not_found(self) -> bool:
        return self.status == ResolutionStatus.NOT_FOUND

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "resolution_date": str(self.resolution_date),
            "reference_id": self.reference_id,
            "reference_version": self.reference_version,
            "effective_from": str(self.effective_from) if self.effective_from else None,
            "effective_to": str(self.effective_to) if self.effective_to else None,
            "source": self.source,
            "reason": self.reason,
            "candidate_count": len(self.candidates),
        }


class EffectiveDateResolver:
    """
    Deterministic resolver that matches candidate reference records against a transaction date.
    
    Rules:
      - Valid window: effective_from <= D <= (effective_to or infinity) and status == 'ACTIVE'
      - Exactly 1 match -> RESOLVED
      - 0 matches       -> NOT_FOUND
      - > 1 matches     -> CONFLICT (never silently choose one)
      - Corrupt range   -> INVALID_REFERENCE
    """

    @staticmethod
    def resolve(
        candidates: List[T],
        target_date: date,
        entity_label: str = "Reference",
    ) -> ResolutionResult[T]:
        """Resolve applicable reference for a given target date."""
        if not candidates:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                resolution_date=target_date,
                reason=f"No {entity_label} records exist in repository.",
            )

        # 1. Check integrity of candidates
        for c in candidates:
            if c.effective_to is not None and c.effective_from is not None:
                if c.effective_to < c.effective_from:
                    return ResolutionResult(
                        status=ResolutionStatus.INVALID_REFERENCE,
                        resolution_date=target_date,
                        reference_id=c.reference_id,
                        reference_version=c.version,
                        reason=f"Invalid date window in candidate {c.reference_id}: effective_to ({c.effective_to}) < effective_from ({c.effective_from})",
                        candidates=candidates,
                    )

        # 2. Filter active matches on target_date
        active_matches = [c for c in candidates if c.is_active_on(target_date)]

        if len(active_matches) == 1:
            match = active_matches[0]
            return ResolutionResult(
                status=ResolutionStatus.RESOLVED,
                resolution_date=target_date,
                reference=match,
                reference_id=match.reference_id,
                reference_version=match.version,
                effective_from=match.effective_from,
                effective_to=match.effective_to,
                source=match.source,
                reason=f"Successfully resolved active {entity_label} {match.reference_id} (v{match.version}).",
                candidates=active_matches,
            )

        elif len(active_matches) == 0:
            # Check if there are future or expired references to provide explanatory context
            expired = [c for c in candidates if c.effective_to and c.effective_to < target_date]
            future = [c for c in candidates if c.effective_from > target_date]
            detail_msg = []
            if expired:
                detail_msg.append(f"{len(expired)} expired reference(s) (last expired {max(c.effective_to for c in expired)})")
            if future:
                detail_msg.append(f"{len(future)} future reference(s) (next starts {min(c.effective_from for c in future)})")
            context_str = f" ({'; '.join(detail_msg)})" if detail_msg else ""

            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                resolution_date=target_date,
                reason=f"No active {entity_label} found valid for transaction date {target_date}{context_str}.",
                candidates=candidates,
            )

        else:
            # Multiple active matches -> CONFLICT
            conflict_ids = [f"{c.reference_id} (v{c.version})" for c in active_matches]
            return ResolutionResult(
                status=ResolutionStatus.CONFLICT,
                resolution_date=target_date,
                reason=f"Reference conflict: Multiple active {entity_label} records match date {target_date}: {', '.join(conflict_ids)}.",
                candidates=active_matches,
            )
