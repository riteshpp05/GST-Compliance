"""
app.knowledge.embeddings
========================
Embeddings package re-exports.
"""

from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.embeddings.factory import create_embedding_provider
from app.knowledge.embeddings.mock_provider import DeterministicMockEmbeddingProvider
from app.knowledge.embeddings.openai_provider import OpenAIEmbeddingProvider

__all__ = [
    "EmbeddingProvider",
    "DeterministicMockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "create_embedding_provider",
]
