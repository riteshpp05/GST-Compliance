"""
app.knowledge.embeddings.openai_provider
========================================
OpenAI Embedding Provider implementation with graceful fallback (Sprint 12.3).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
import httpx
from app.infrastructure.logging import get_logger
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.embeddings.mock_provider import DeterministicMockEmbeddingProvider
from app.knowledge.models import KnowledgeProviderStatus

logger = get_logger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embeddings API wrapper.
    Falls back gracefully to DeterministicMockEmbeddingProvider if API key is missing or call fails.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small") -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model = model
        self.fallback_provider = DeterministicMockEmbeddingProvider()

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def embed_text(self, text: str) -> List[float]:
        if not self.is_available():
            logger.info("OpenAI API key missing. Using DeterministicMockEmbeddingProvider fallback.")
            return self.fallback_provider.embed_text(text)

        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {"input": text, "model": self.model}

            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["data"][0]["embedding"]

        except Exception as exc:
            logger.warning(f"OpenAI embedding call failed: {exc}. Falling back to mock provider.")
            return self.fallback_provider.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available():
            return self.fallback_provider.embed_batch(texts)
        return [self.embed_text(t) for t in texts]

    def get_status(self) -> Dict[str, Any]:
        if self.is_available():
            return {
                "status": KnowledgeProviderStatus.ACTIVE.value,
                "available": True,
                "provider": "OpenAIEmbeddingProvider",
                "model": self.model,
            }
        return self.fallback_provider.get_status()
