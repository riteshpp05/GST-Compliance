"""
UC15 GST Compliance Agent — HSN/SAC Reference Model
Comprehensive tariff classification model supporting chapters, headings, and hierarchy.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.reference.models.base import BaseReferenceRecord


@dataclass
class HSNReference(BaseReferenceRecord):
    """
    Standard statutory HSN/SAC classification master record.
    Supports 2, 4, 6, and 8-digit tariff levels and chapter hierarchy.
    """
    code: str = ""
    description: str = ""
    code_type: str = "HSN"                                  # HSN (Goods) | SAC (Services)
    chapter: Optional[str] = None                           # First 2 digits
    heading: Optional[str] = None                           # First 4 digits
    subheading: Optional[str] = None                        # First 6 digits
    tariff_item: Optional[str] = None                       # Full 8 digits
    is_service: bool = False

    # Default rates associated with baseline HSN entry
    default_cgst_rate: Optional[Decimal] = None
    default_sgst_rate: Optional[Decimal] = None
    default_igst_rate: Optional[Decimal] = None

    def __post_init__(self):
        clean_code = str(self.code or "").strip()
        self.code = clean_code
        self.reference_type = "HSN" if self.code_type == "HSN" else "SAC"
        
        # Derive hierarchy components if not explicitly passed
        if clean_code and len(clean_code) >= 2 and not self.chapter:
            self.chapter = clean_code[:2]
        if clean_code and len(clean_code) >= 4 and not self.heading:
            self.heading = clean_code[:4]
        if clean_code and len(clean_code) >= 6 and not self.subheading:
            self.subheading = clean_code[:6]
        if clean_code and len(clean_code) == 8 and not self.tariff_item:
            self.tariff_item = clean_code

        if clean_code.startswith("99"):
            self.code_type = "SAC"
            self.is_service = True

    def matches_code_or_prefix(self, query_code: str) -> bool:
        """Check if query code matches exact code or falls within hierarchy."""
        q = query_code.strip()
        if self.code == q:
            return True
        if len(self.code) < len(q) and q.startswith(self.code):
            return True
        if len(q) < len(self.code) and self.code.startswith(q):
            return True
        return False
