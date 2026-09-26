"""
UC15 GST Compliance Agent — State & Union Territory Reference Model
Statutory state codes, nomenclature, and jurisdiction classifications for GST.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.reference.models.base import BaseReferenceRecord


@dataclass
class StateReference(BaseReferenceRecord):
    """
    Indian State/UT master entry for GST jurisdiction and POS validation.
    """
    state_code: str = ""                                    # 2-digit GST state code e.g. '27'
    state_name: str = ""                                    # Official name e.g. 'Maharashtra'
    state_or_ut: str = "STATE"                              # STATE | UT
    jurisdiction_type: str = "STATE"                        # STATE | UNION_TERRITORY
    has_legislature: bool = True                            # True for States and UTs with legislative assemblies (Delhi, J&K, Puducherry)
    tin_prefix: Optional[str] = None

    def __post_init__(self):
        self.reference_type = "STATE"
        self.state_code = str(self.state_code or "").strip().zfill(2)
        self.state_name = str(self.state_name or "").strip()
        # Canonical UTs with legislative assembly (Delhi 07, J&K 01, Puducherry 34)
        if self.state_code in ("07", "01", "34"):
            self.state_or_ut = "UT"
            self.jurisdiction_type = "UNION_TERRITORY"
            self.has_legislature = True
        elif self.state_or_ut.upper() in ("UT", "UNION_TERRITORY"):
            self.state_or_ut = "UT"
            self.jurisdiction_type = "UNION_TERRITORY"
            # If not explicitly marked with legislature, default to False for UTs without legislature
            if self.state_code not in ("07", "01", "34"):
                self.has_legislature = False
        else:
            self.state_or_ut = "STATE"
            self.jurisdiction_type = "STATE"
            self.has_legislature = True

    @property
    def is_union_territory(self) -> bool:
        return self.state_or_ut == "UT" or self.jurisdiction_type == "UNION_TERRITORY"

    @property
    def is_ut_without_legislature(self) -> bool:
        """UT without its own legislature attracts CGST + UTGST under UTGST Act, 2017."""
        return self.is_union_territory and not self.has_legislature

