"""
app.knowledge.embeddings.mock_provider
======================================
Deterministic Mock Embedding Provider for UC15 Knowledge Subsystem (Sprint 12.3).
Generates deterministic 128-dimensional L2-normalized float vectors for offline dev/tests.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Dict, List
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.models import KnowledgeProviderStatus


class DeterministicMockEmbeddingProvider(EmbeddingProvider):
    """
    Generates deterministic float embeddings using character n-grams and word tokens.
    Guarantees reproducible cosine similarity without external API dependencies.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dimension = dimension

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dimension

        vector = [0.0] * self.dimension
        clean_text = text.lower().strip()
        tokens = re.findall(r"\w+", clean_text)

        # 1. Word token hashing
        for token in tokens:
            token_hash = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(min(16, len(token_hash))):
                idx = (token_hash[i] + i * 7) % self.dimension
                vector[idx] += float(token_hash[i]) / 255.0

        # 2. Character 3-gram hashing
        for i in range(len(clean_text) - 2):
            gram = clean_text[i : i + 3]
            gram_hash = hashlib.md5(gram.encode("utf-8")).digest()
            idx = (gram_hash[0] + i * 3) % self.dimension
            vector[idx] += 0.5

        # L2 Normalization
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0.0:
            vector = [v / norm for v in vector]

        return vector

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]

    def is_available(self) -> bool:
        return True

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": KnowledgeProviderStatus.MOCK_FALLBACK.value,
            "available": True,
            "provider": "DeterministicMockEmbeddingProvider",
            "dimension": self.dimension,
        }
