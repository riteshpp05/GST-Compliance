"""
app.intelligence.common.models
==============================
Canonical model contracts for intelligence findings.
Serves as the unified output structure for both Duplicate and Anomaly engines.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.intelligence.common.enums import (
    IntelligenceCategory,
    IntelligenceConfidence,
)


@dataclass
class IntelligenceFinding:
    """
    Canonical, explainable intelligence finding.
    Does NOT alter statutory compliance decisions or financial authority.
    Provides structured evidence for downstream review and future AI Agent workflows.
    """
    finding_id: str = field(default_factory=lambda: f"FIND-{uuid.uuid4().hex[:8].upper()}")
    invoice_id: str = ""
    category: IntelligenceCategory = IntelligenceCategory.DUPLICATE
    finding_type: str = ""
    status: str = ""
    score: float = 0.0
    confidence: IntelligenceConfidence = IntelligenceConfidence.HIGH
    severity: str = "MEDIUM"
    title: str = ""
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    related_invoice_ids: List[str] = field(default_factory=list)
    detector: str = ""
    detector_version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    source_lineage: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize into clean dictionary representation."""
        return {
            "finding_id": self.finding_id,
            "invoice_id": self.invoice_id,
            "category": self.category.value if hasattr(self.category, "value") else str(self.category),
            "finding_type": self.finding_type,
            "status": self.status,
            "score": round(self.score, 2),
            "confidence": self.confidence.value if hasattr(self.confidence, "value") else str(self.confidence),
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "related_invoice_ids": self.related_invoice_ids,
            "detector": self.detector,
            "detector_version": self.detector_version,
            "created_at": self.created_at,
            "source_lineage": self.source_lineage,
        }
