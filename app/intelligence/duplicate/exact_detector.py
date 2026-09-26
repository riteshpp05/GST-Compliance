"""
app.intelligence.duplicate.exact_detector
=========================================
Deterministic exact duplicate detector based on canonical normalized fingerprints.
Detects identical transactions across all strong identity attributes with zero heuristics.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.domain.models.invoice import Invoice
from app.intelligence.common.enums import (
    DuplicateMatchType,
    IntelligenceConfidence,
)
from app.intelligence.config.intelligence_config import (
    DuplicatePolicyConfig,
    default_intelligence_config,
)
from app.intelligence.duplicate.fingerprint import (
    extract_parties,
    generate_exact_fingerprint,
    normalize_date,
    normalize_invoice_number,
    parse_decimal_safe,
)
from app.intelligence.duplicate.models import DuplicateCandidate


class ExactDuplicateDetector:
    """
    Evaluates exact duplicate candidates using normalized identity fingerprints.
    Produces high-confidence, fully explainable evidence.
    """
    DETECTOR_NAME = "EXACT_DUPLICATE_DETECTOR"
    DETECTOR_VERSION = "1.0"

    def __init__(self, config: Optional[DuplicatePolicyConfig] = None) -> None:
        self.config = config or default_intelligence_config.duplicate

    def compare_pair(self, inv1: Invoice, inv2: Invoice) -> Optional[DuplicateCandidate]:
        """
        Compare two invoices directly for exact duplication.
        Returns a DuplicateCandidate if an exact match is established or NOT_EVALUATED on missing data.
        """
        if inv1.invoice_id == inv2.invoice_id:
            return None

        fp1 = generate_exact_fingerprint(inv1, self.config.normalization)
        fp2 = generate_exact_fingerprint(inv2, self.config.normalization)

        if fp1 is None or fp2 is None:
            return DuplicateCandidate(
                source_invoice_id=inv1.invoice_id,
                matched_invoice_id=inv2.invoice_id,
                match_type=DuplicateMatchType.NOT_EVALUATED,
                similarity_score=0.0,
                confidence=IntelligenceConfidence.LOW,
                evidence={
                    "status": "NOT_EVALUATED",
                    "reason": "Missing critical identity fields (invoice_number, supplier_gstin, or invoice_date) on one or both invoices.",
                },
            )

        if fp1 == fp2:
            sup1, buy1 = extract_parties(inv1)
            sup2, buy2 = extract_parties(inv2)
            evidence = {
                "match_type": "EXACT",
                "is_exact": True,
                "supplier_gstin": f"Identical ({sup1})",
                "buyer_gstin": f"Identical ({buy1 or 'N/A'})",
                "invoice_number": f"Identical after normalization ({normalize_invoice_number(inv1.invoice_number, self.config.normalization.remove_separators)})",
                "invoice_date": f"Identical ({normalize_date(inv1.invoice_date)})",
                "taxable_value": f"Identical (INR {parse_decimal_safe(inv1.taxable_value):,.2f})",
                "total_tax": f"Identical (INR {parse_decimal_safe(inv1.total_tax):,.2f})",
                "confidence_reason": "All 6 statutory identity attributes match exactly after standard format normalization.",
            }
            return DuplicateCandidate(
                source_invoice_id=inv1.invoice_id,
                matched_invoice_id=inv2.invoice_id,
                match_type=DuplicateMatchType.EXACT_DUPLICATE,
                similarity_score=100.0,
                confidence=IntelligenceConfidence.HIGH,
                field_matches={
                    "supplier_gstin": True,
                    "buyer_gstin": True,
                    "invoice_number": True,
                    "invoice_date": True,
                    "taxable_value": True,
                    "total_tax": True,
                },
                field_scores={
                    "supplier_gstin": self.config.weights.supplier_gstin_match,
                    "buyer_gstin": self.config.weights.buyer_gstin_match,
                    "invoice_number": self.config.weights.invoice_number_similarity,
                    "invoice_date": self.config.weights.date_proximity,
                    "taxable_value": self.config.weights.taxable_value_similarity,
                    "total_tax": self.config.weights.tax_amount_similarity,
                },
                evidence=evidence,
            )

        return None

    def detect_exact(self, invoices: List[Invoice]) -> List[DuplicateCandidate]:
        """
        Batch evaluation for exact duplicates using hash-indexed bucket lookup.
        O(N) time complexity instead of O(N^2).
        """
        buckets: Dict[str, List[Invoice]] = defaultdict(list)
        un_evaluated: List[DuplicateCandidate] = []

        for inv in invoices:
            fp = generate_exact_fingerprint(inv, self.config.normalization)
            if fp is None:
                # Missing critical attributes
                un_evaluated.append(
                    DuplicateCandidate(
                        source_invoice_id=inv.invoice_id,
                        matched_invoice_id="",
                        match_type=DuplicateMatchType.NOT_EVALUATED,
                        similarity_score=0.0,
                        confidence=IntelligenceConfidence.LOW,
                        evidence={
                            "status": "NOT_EVALUATED",
                            "reason": "Missing critical identity fields on invoice.",
                            "invoice_id": inv.invoice_id,
                        },
                    )
                )
            else:
                buckets[fp].append(inv)

        candidates: List[DuplicateCandidate] = []
        for fp, group in buckets.items():
            if len(group) > 1:
                # Pairwise within matching fingerprint bucket
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        inv1, inv2 = group[i], group[j]
                        cand = self.compare_pair(inv1, inv2)
                        if cand and cand.match_type == DuplicateMatchType.EXACT_DUPLICATE:
                            candidates.append(cand)

        return candidates + un_evaluated
