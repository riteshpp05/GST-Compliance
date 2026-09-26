"""
UC15 GST Compliance Agent — Vendor & Customer Models
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class Counterparty(BaseModel):
    """Represents a vendor (AP) or customer (AR) entity in GST compliance."""
    name: str
    gstin: Optional[str] = None
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    pan: Optional[str] = None
    master_ref: Optional[str] = Field(default=None, description="SAP master reference (KNA1 for customer, LFA1 for vendor)")

    @property
    def derived_state_code(self) -> Optional[str]:
        if self.gstin and len(self.gstin) >= 2 and self.gstin[:2].isdigit():
            return self.gstin[:2]
        return self.state_code


# Convenience aliases for domain semantic clarity
Vendor = Counterparty
Customer = Counterparty
