"""
app.knowledge.embeddings.base
=============================
Abstract base class for Knowledge Embedding Providers (Sprint 12.3).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from app.knowledge.models import KnowledgeProviderStatus


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Convert a single text string into a float vector."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Convert a list of text strings into float vectors."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if provider is ready and available."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return status dictionary describing provider state."""
        pass

    @staticmethod
    def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return max(0.0, min(1.0, dot / (norm_a * norm_b)))
