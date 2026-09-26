"""
UC15 GST Compliance Agent — Common Domain Models & Types
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class AuditTrail(BaseModel):
    """Audit metadata tracking transaction validation lifecycle."""
    reference_id: str
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor: str = "UC15_AGENT"
    system: str = "SAP_FI_TAX"
    notes: Optional[str] = None


class MonetaryAmount(BaseModel):
    """Precision monetary value wrapper."""
    amount: Decimal
    currency: str = "INR"

    def to_float(self) -> float:
        return float(self.amount)
