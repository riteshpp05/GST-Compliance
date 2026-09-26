"""
app.knowledge.embeddings.factory
================================
Factory for instantiating EmbeddingProvider implementations (Sprint 12.3).
"""

from __future__ import annotations

import os
from typing import Optional
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.embeddings.mock_provider import DeterministicMockEmbeddingProvider
from app.knowledge.embeddings.openai_provider import OpenAIEmbeddingProvider


def create_embedding_provider(provider_name: Optional[str] = None) -> EmbeddingProvider:
    """
    Instantiate appropriate EmbeddingProvider based on name or environment settings.
    If 'mock' -> DeterministicMockEmbeddingProvider.
    If 'openai' -> OpenAIEmbeddingProvider.
    If 'auto' or None -> OpenAIEmbeddingProvider if key present, else DeterministicMockEmbeddingProvider.
    """
    name = (provider_name or os.getenv("EMBEDDING_PROVIDER", "auto")).lower()

    if name == "mock":
        return DeterministicMockEmbeddingProvider()
    elif name == "openai":
        return OpenAIEmbeddingProvider()
    else: # auto
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        if api_key and api_key.strip():
            return OpenAIEmbeddingProvider(api_key=api_key)
        return DeterministicMockEmbeddingProvider()
