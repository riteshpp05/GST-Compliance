"""
UC15 GST Compliance Agent — Input Tax Credit (ITC) Policy Reference Model
Statutory Section 17(5) blocked credit rules, reconciliation requirements, and restrictions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from app.reference.models.base import BaseReferenceRecord


@dataclass
class ITCPolicyReference(BaseReferenceRecord):
    """
    Statutory ITC eligibility and restriction policy under Section 16 & 17(5) of the CGST Act.
    """
    policy_id: str = ""
    category: str = "GENERAL"
    blocked_keywords: List[str] = field(default_factory=list)
    is_blocked_17_5: bool = False
    blocked_reason: Optional[str] = None
    requires_2b_reconciliation: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        self.reference_type = "ITC_POLICY"

    def matches_item_description(self, item_desc: str) -> bool:
        """Check if invoice line item description matches any blocked keyword in this policy."""
        if not self.is_blocked_17_5:
            return False
        import re
        desc_lower = str(item_desc or "").strip().lower()
        for kw in self.blocked_keywords:
            kw_clean = kw.strip().lower()
            if " " in kw_clean:
                if kw_clean in desc_lower:
                    return True
            else:
                pattern = r"\b" + re.escape(kw_clean) + r"\b"
                if re.search(pattern, desc_lower):
                    return True
        return False
