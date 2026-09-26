"""
app.intelligence.anomaly.models
===============================
Data models for Anomaly Intelligence (Sprint 7).
Defines dimensional anomaly findings, baseline metrics, and statistical contracts.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional

from app.intelligence.common.enums import (
    AnomalyDimension,
    AnomalyLevel,
    AnomalyStatus,
    IntelligenceConfidence,
)


@dataclass
class AnomalyFinding:
    """
    Dimensional anomaly finding evaluating a single transaction against historical baseline.
    Does NOT assert fraud or non-compliance; expresses statistical unusualness.
    """
    finding_id: str = field(default_factory=lambda: f"ANOM-{uuid.uuid4().hex[:8].upper()}")
    invoice_id: str = ""
    dimension: AnomalyDimension = AnomalyDimension.VALUE_ANOMALY
    status: AnomalyStatus = AnomalyStatus.NORMAL
    score: float = 0.0  # 0.0 to 100.0 anomaly score (independent of S3 risk score)
    level: AnomalyLevel = AnomalyLevel.LOW
    confidence: IntelligenceConfidence = IntelligenceConfidence.HIGH
    baseline_scope: str = "PORTFOLIO"  # COUNTERPARTY | HSN | PORTFOLIO | STATUTORY
    baseline_sample_size: int = 0
    observed_value: float = 0.0
    baseline_metrics: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    potential_financial_exposure: Decimal = Decimal("0.00")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "invoice_id": self.invoice_id,
            "dimension": self.dimension.value if hasattr(self.dimension, "value") else str(self.dimension),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "score": round(self.score, 2),
            "level": self.level.value if hasattr(self.level, "value") else str(self.level),
            "confidence": self.confidence.value if hasattr(self.confidence, "value") else str(self.confidence),
            "baseline_scope": self.baseline_scope,
            "baseline_sample_size": self.baseline_sample_size,
            "observed_value": round(self.observed_value, 2),
            "baseline_metrics": self.baseline_metrics,
            "evidence": self.evidence,
            "potential_financial_exposure": float(self.potential_financial_exposure),
        }
