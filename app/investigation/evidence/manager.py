"""
app.investigation.evidence.manager
==================================
First-Class Evidence Model, Classification, Chain Provenance, and Snapshot Manager for UC15 (Sprint 18).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from app.case.models import CaseEvidenceRecord
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class EvidenceStrengthEnum(str, Enum):
    """Classification of evidence strength and grounding quality."""
    DETERMINISTIC = "DETERMINISTIC"
    STRONG = "STRONG"
    SUPPORTING = "SUPPORTING"
    CONTEXTUAL = "CONTEXTUAL"
    UNVERIFIED = "UNVERIFIED"


class EvidenceManager:
    """
    Manages structured evidence creation, classification, SHA-256 snapshot hashing, and provenance linkage.
    """

    @staticmethod
    def classify_strength(source_type: str) -> EvidenceStrengthEnum:
        """Map source type to explicit evidence strength classification."""
        st = source_type.upper()
        if st in {"VALIDATION_RESULT", "GATE_DETERMINATION", "GST_RETURNS", "TAX_CALCULATION"}:
            return EvidenceStrengthEnum.DETERMINISTIC
        if st in {"HISTORICAL_RESULT", "DUPLICATE_RESULT", "ANOMALY_RESULT", "FINANCIAL_ANALYSIS"}:
            return EvidenceStrengthEnum.STRONG
        if st in {"KNOWLEDGE_DOCUMENT", "RCA_RESULT", "BLAST_RADIUS_RESULT", "REGULATORY"}:
            return EvidenceStrengthEnum.SUPPORTING
        if st in {"SOURCE_RECORD", "INVOICE", "SYSTEM_EVENT", "TRANSACTION"}:
            return EvidenceStrengthEnum.CONTEXTUAL
        return EvidenceStrengthEnum.UNVERIFIED

    @classmethod
    def create_evidence(
        cls,
        case_id: str,
        source_type: str,
        source_id: str,
        description: str,
        data: Dict[str, Any],
        reliability: float = 1.0,
        strength: Optional[EvidenceStrengthEnum] = None,
        collected_by: str = "SYSTEM",
    ) -> CaseEvidenceRecord:
        """
        Create a first-class CaseEvidenceRecord with SHA-256 snapshot fingerprinting.
        """
        ev_strength = strength or cls.classify_strength(source_type)

        # Compute SHA-256 payload snapshot hash
        payload_str = json.dumps(data, sort_keys=True, default=str)
        snapshot_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        metadata = {
            "source_id": source_id,
            "evidence_strength": ev_strength.value,
            "snapshot_hash": snapshot_hash,
            "provenance_chain": [
                f"SourceRecord:{source_id}",
                f"AnalysisType:{source_type}",
                f"CaseID:{case_id}",
            ],
        }

        record = CaseEvidenceRecord(
            case_id=case_id,
            evidence_type=source_type,
            source=f"{source_type}:{source_id}",
            description=description,
            data=data,
            reliability=reliability,
            collected_by=collected_by,
            metadata=metadata,
        )
        logger.info(f"Created evidence record '{record.evidence_id}' for case '{case_id}' (Strength: {ev_strength.value}, Snapshot: {snapshot_hash[:8]}).")
        return record
