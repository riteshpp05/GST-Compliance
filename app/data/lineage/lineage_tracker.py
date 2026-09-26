"""
app.data.lineage.lineage_tracker
================================
Enterprise Data Lineage & Provenance Tracker for UC15 (Sprint 17).
Traces data lifecycle: Source -> Ingestion -> Raw -> Normalized -> Canonical -> Intelligence -> Evidence -> Finding -> Case.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TransformationStep:
    """Individual transformation applied during normalization or quality checks."""
    step_name: str
    input_value: Any
    output_value: Any
    description: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "input_value": str(self.input_value),
            "output_value": str(self.output_value),
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class DataLineageRecord:
    """Enterprise Data Lineage Record linking raw source to downstream evidence and cases."""
    lineage_id: str
    ingestion_id: str
    source_id: str
    source_record_id: str
    canonical_record_id: str
    tenant_id: str = "tenant_default"
    transformations: List[TransformationStep] = field(default_factory=list)
    downstream_analysis_ids: List[str] = field(default_factory=list)
    downstream_evidence_ids: List[str] = field(default_factory=list)
    downstream_finding_ids: List[str] = field(default_factory=list)
    downstream_case_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lineage_id": self.lineage_id,
            "ingestion_id": self.ingestion_id,
            "source_id": self.source_id,
            "source_record_id": self.source_record_id,
            "canonical_record_id": self.canonical_record_id,
            "tenant_id": self.tenant_id,
            "transformations": [t.to_dict() for t in self.transformations],
            "downstream_analysis_ids": self.downstream_analysis_ids,
            "downstream_evidence_ids": self.downstream_evidence_ids,
            "downstream_finding_ids": self.downstream_finding_ids,
            "downstream_case_id": self.downstream_case_id,
            "created_at": self.created_at,
        }


class LineageTracker:
    """In-memory and repository helper for generating and updating data lineage records."""

    @staticmethod
    def create_lineage(
        ingestion_id: str,
        source_id: str,
        source_record_id: str,
        canonical_record_id: str,
        tenant_id: str = "tenant_default",
        transformations: Optional[List[TransformationStep]] = None,
    ) -> DataLineageRecord:
        import uuid
        lineage_id = f"LIN-{uuid.uuid4().hex[:8].upper()}"
        return DataLineageRecord(
            lineage_id=lineage_id,
            ingestion_id=ingestion_id,
            source_id=source_id,
            source_record_id=source_record_id,
            canonical_record_id=canonical_record_id,
            tenant_id=tenant_id,
            transformations=transformations or [],
        )

    @staticmethod
    def link_downstream_case(
        lineage: DataLineageRecord,
        case_id: str,
        evidence_ids: Optional[List[str]] = None,
        finding_ids: Optional[List[str]] = None,
    ) -> DataLineageRecord:
        lineage.downstream_case_id = case_id
        if evidence_ids:
            lineage.downstream_evidence_ids.extend([e for e in evidence_ids if e not in lineage.downstream_evidence_ids])
        if finding_ids:
            lineage.downstream_finding_ids.extend([f for f in finding_ids if f not in lineage.downstream_finding_ids])
        return lineage
