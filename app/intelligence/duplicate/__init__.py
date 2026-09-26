"""
app.intelligence.duplicate
==========================
Duplicate Intelligence subsystem (Sprint 7).
Deterministic exact matching, structured near matching, clustering, and false-positive protection.
"""

from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
from app.intelligence.duplicate.fingerprint import (
    generate_exact_fingerprint,
    normalize_invoice_number,
    normalize_gstin,
    normalize_date,
    levenshtein_distance,
    compute_string_similarity,
)
from app.intelligence.duplicate.exact_detector import ExactDuplicateDetector
from app.intelligence.duplicate.near_detector import NearDuplicateDetector
from app.intelligence.duplicate.clusterer import DuplicateClusterer
from app.intelligence.duplicate.engine import DuplicateIntelligenceEngine

__all__ = [
    "DuplicateCandidate",
    "DuplicateCluster",
    "generate_exact_fingerprint",
    "normalize_invoice_number",
    "normalize_gstin",
    "normalize_date",
    "levenshtein_distance",
    "compute_string_similarity",
    "ExactDuplicateDetector",
    "NearDuplicateDetector",
    "DuplicateClusterer",
    "DuplicateIntelligenceEngine",
]
