"""
UC15 GST Compliance Agent — E-Way Bill Policy Reference Model
Externalized statutory thresholds, exemptions, and movement rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

from app.reference.models.base import BaseReferenceRecord


@dataclass
class EWBPolicyReference(BaseReferenceRecord):
    """
    Statutory E-Way Bill policy configuration valid for specific date windows and jurisdictions.
    """
    policy_id: str = ""
    name: str = "National E-Way Bill Movement Policy"
    threshold: Decimal = Decimal("50000.00")                 # Statutory threshold INR
    state_code: Optional[str] = None                        # None for national policy, or 2-digit state code
    interstate_threshold: Optional[Decimal] = None
    intrastate_threshold: Optional[Decimal] = None
    exempted_hsn: List[str] = field(default_factory=list)
    description: Optional[str] = None

    def __post_init__(self):
        self.reference_type = "EWB_POLICY"
        if not isinstance(self.threshold, Decimal):
            self.threshold = Decimal(str(self.threshold))
        if self.interstate_threshold and not isinstance(self.interstate_threshold, Decimal):
            self.interstate_threshold = Decimal(str(self.interstate_threshold))
        if self.intrastate_threshold and not isinstance(self.intrastate_threshold, Decimal):
            self.intrastate_threshold = Decimal(str(self.intrastate_threshold))

    def get_threshold_for(self, is_interstate: bool = False) -> Decimal:
        """Get the applicable threshold based on movement jurisdiction."""
        if is_interstate and self.interstate_threshold is not None:
            return self.interstate_threshold
        if not is_interstate and self.intrastate_threshold is not None:
            return self.intrastate_threshold
        return self.threshold

    def is_hsn_exempt(self, hsn_code: Optional[str]) -> bool:
        """Check if an HSN code is exempted from E-Way Bill requirement under this policy."""
        if not hsn_code or not self.exempted_hsn:
            return False
        clean_hsn = str(hsn_code).strip()
        for exempt in self.exempted_hsn:
            exempt_str = str(exempt).strip()
            if clean_hsn == exempt_str or clean_hsn.startswith(exempt_str):
                return True
        return False

