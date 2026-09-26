"""
app.intelligence.duplicate.models
=================================
Data models for Duplicate Intelligence (Sprint 7).
Defines candidate pairs and multi-invoice duplicate clusters.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.intelligence.common.enums import (
    DuplicateMatchType,
    IntelligenceConfidence,
)


@dataclass
class DuplicateCandidate:
    """
    Pairwise comparison result between two invoices.
    Identifies exact or near duplicate candidates with structured field evidence.
    """
    candidate_id: str = field(default_factory=lambda: f"DUP-{uuid.uuid4().hex[:8].upper()}")
    source_invoice_id: str = ""
    matched_invoice_id: str = ""
    match_type: DuplicateMatchType = DuplicateMatchType.NO_DUPLICATE
    similarity_score: float = 0.0
    confidence: IntelligenceConfidence = IntelligenceConfidence.LOW
    field_matches: Dict[str, bool] = field(default_factory=dict)
    field_scores: Dict[str, float] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    cluster_id: Optional[str] = None
    is_recurring_legitimate: bool = False
    potential_financial_exposure: Decimal = Decimal("0.00")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "source_invoice_id": self.source_invoice_id,
            "matched_invoice_id": self.matched_invoice_id,
            "match_type": self.match_type.value if hasattr(self.match_type, "value") else str(self.match_type),
            "similarity_score": round(self.similarity_score, 2),
            "confidence": self.confidence.value if hasattr(self.confidence, "value") else str(self.confidence),
            "field_matches": self.field_matches,
            "field_scores": self.field_scores,
            "evidence": self.evidence,
            "cluster_id": self.cluster_id,
            "is_recurring_legitimate": self.is_recurring_legitimate,
            "potential_financial_exposure": float(self.potential_financial_exposure),
        }


@dataclass
class DuplicateCluster:
    """
    Group of 2 or more mutually duplicated invoices.
    Consolidates pairwise matches into a single unified investigation entity.
    """
    cluster_id: str = field(default_factory=lambda: f"CLUST-DUP-{uuid.uuid4().hex[:6].upper()}")
    invoice_ids: List[str] = field(default_factory=list)
    primary_invoice_id: str = ""
    match_type: DuplicateMatchType = DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE
    average_similarity: float = 0.0
    common_attributes: Dict[str, Any] = field(default_factory=dict)
    candidates: List[DuplicateCandidate] = field(default_factory=list)

    @property
    def invoice_count(self) -> int:
        return len(self.invoice_ids)

    @property
    def anchor_invoice_id(self) -> str:
        return self.primary_invoice_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "invoice_ids": self.invoice_ids,
            "primary_invoice_id": self.primary_invoice_id,
            "match_type": self.match_type.value if hasattr(self.match_type, "value") else str(self.match_type),
            "average_similarity": round(self.average_similarity, 2),
            "common_attributes": self.common_attributes,
            "candidates_count": len(self.candidates),
        }
