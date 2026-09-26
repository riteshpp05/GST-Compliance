"""
app.intelligence.duplicate.engine
=================================
Duplicate Intelligence Engine orchestrating exact detection, near detection,
clustering, and transformation into canonical IntelligenceFinding records.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

from app.domain.models.invoice import Invoice
from app.intelligence.common.enums import (
    DuplicateMatchType,
    IntelligenceCategory,
    IntelligenceConfidence,
)
from app.intelligence.common.models import IntelligenceFinding
from app.intelligence.config.intelligence_config import (
    DuplicatePolicyConfig,
    default_intelligence_config,
)
from app.intelligence.duplicate.clusterer import DuplicateClusterer
from app.intelligence.duplicate.exact_detector import ExactDuplicateDetector
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.intelligence.duplicate.near_detector import NearDuplicateDetector


class DuplicateIntelligenceEngine:
    """
    Central engine for Duplicate Intelligence.
    Detects exact duplicates, near duplicates, forms duplicate clusters, and emits canonical findings.
    """
    ENGINE_NAME = "DUPLICATE_INTELLIGENCE_ENGINE"
    ENGINE_VERSION = "1.0"

    def __init__(self, config: Optional[DuplicatePolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.duplicate
        self.exact_detector = ExactDuplicateDetector(config=self.config)
        self.near_detector = NearDuplicateDetector(config=self.config)
        self.clusterer = DuplicateClusterer()

    def compare_invoices(self, inv1: Invoice, inv2: Invoice) -> DuplicateCandidate:
        """Compare a single pair of invoices using exact detection first, then near detection."""
        exact = self.exact_detector.compare_pair(inv1, inv2)
        if exact and exact.match_type == DuplicateMatchType.EXACT_DUPLICATE:
            return exact
        return self.near_detector.compare_pair(inv1, inv2)

    def analyze(
        self,
        invoices: List[Invoice],
    ) -> Tuple[List[DuplicateCluster], List[DuplicateCandidate], List[IntelligenceFinding]]:
        """
        Analyze a batch of invoices for duplicate relationships.
        Returns:
            - duplicate_clusters: List of consolidated multi-invoice clusters.
            - duplicate_candidates: All pairwise duplicate candidates.
            - findings: Canonical IntelligenceFinding objects for UI/API/Agent consumption.
        """
        if not invoices or len(invoices) < 2:
            return [], [], []

        # 1. Detect exact duplicates
        exact_candidates = self.exact_detector.detect_exact(invoices)

        # 2. Detect near duplicates
        near_candidates = self.near_detector.detect_near(invoices)

        # 3. Deduplicate candidate pairs (exact takes precedence over near for same pair)
        exact_pairs: Set[Tuple[str, str]] = set()
        all_candidates: List[DuplicateCandidate] = []

        for ec in exact_candidates:
            if ec.match_type == DuplicateMatchType.EXACT_DUPLICATE:
                pair = (min(ec.source_invoice_id, ec.matched_invoice_id), max(ec.source_invoice_id, ec.matched_invoice_id))
                exact_pairs.add(pair)
                all_candidates.append(ec)
            elif ec.match_type == DuplicateMatchType.NOT_EVALUATED:
                all_candidates.append(ec)

        for nc in near_candidates:
            pair = (min(nc.source_invoice_id, nc.matched_invoice_id), max(nc.source_invoice_id, nc.matched_invoice_id))
            if pair not in exact_pairs:
                all_candidates.append(nc)

        # 4. Form duplicate clusters
        clusters = self.clusterer.cluster_candidates(all_candidates)

        # 5. Transform into canonical IntelligenceFinding records
        findings: List[IntelligenceFinding] = []
        emitted_pairs: Set[Tuple[str, str]] = set()

        for cand in all_candidates:
            if cand.match_type in (DuplicateMatchType.NO_DUPLICATE, DuplicateMatchType.NOT_EVALUATED):
                continue

            pair = (min(cand.source_invoice_id, cand.matched_invoice_id), max(cand.source_invoice_id, cand.matched_invoice_id))
            if pair in emitted_pairs:
                continue
            emitted_pairs.add(pair)

            is_exact = cand.match_type == DuplicateMatchType.EXACT_DUPLICATE
            severity = "CRITICAL" if is_exact else ("HIGH" if cand.match_type == DuplicateMatchType.HIGH_CONFIDENCE_NEAR_DUPLICATE else "MEDIUM")
            status = "CONFIRMED_DUPLICATE" if is_exact else "CANDIDATE"

            title = (
                f"Potential Exact Duplicate: {cand.source_invoice_id} & {cand.matched_invoice_id}"
                if is_exact
                else f"Near Duplicate Candidate: {cand.source_invoice_id} & {cand.matched_invoice_id}"
            )

            desc = (
                f"Invoices {cand.source_invoice_id} and {cand.matched_invoice_id} have identical identity fingerprints."
                if is_exact
                else f"Invoices {cand.source_invoice_id} and {cand.matched_invoice_id} share a structured similarity score of {cand.similarity_score:.1f}%."
            )

            finding = IntelligenceFinding(
                finding_id=f"FIND-DUP-{uuid.uuid4().hex[:8].upper()}",
                invoice_id=cand.source_invoice_id,
                category=IntelligenceCategory.DUPLICATE,
                finding_type=cand.match_type.value,
                status=status,
                score=cand.similarity_score,
                confidence=cand.confidence,
                severity=severity,
                title=title,
                description=desc,
                evidence=cand.evidence,
                related_invoice_ids=[cand.matched_invoice_id],
                detector=self.exact_detector.DETECTOR_NAME if is_exact else self.near_detector.DETECTOR_NAME,
                detector_version=self.ENGINE_VERSION,
                source_lineage={
                    "invoice_id": cand.source_invoice_id,
                    "source_invoice_id": cand.source_invoice_id,
                    "matched_invoice_id": cand.matched_invoice_id,
                    "cluster_id": cand.cluster_id,
                },
            )
            findings.append(finding)

        return clusters, all_candidates, findings
