"""
app.knowledge
=============
UC15 Regulatory & GST Knowledge Intelligence Package (Sprint 12.3).
Provides modular, evidence-grounded RAG retrieval, document parsing, chunking,
embedding abstractions, in-memory vector store, and temporal effective-date evaluation.
"""

from app.knowledge.config import KnowledgeConfig, get_knowledge_config
from app.knowledge.exceptions import (
    DocumentParsingError,
    DocumentSecurityError,
    EmbeddingError,
    KnowledgeError,
    RetrievalError,
)
from app.knowledge.models import (
    DocumentType,
    EvidenceStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeMetadata,
    KnowledgeProviderStatus,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
    RetrievedEvidence,
)
from app.knowledge.service import KnowledgeService

__all__ = [
    "KnowledgeService",
    "KnowledgeConfig",
    "get_knowledge_config",
    "DocumentType",
    "EvidenceStatus",
    "RetrievalStatus",
    "KnowledgeProviderStatus",
    "KnowledgeMetadata",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "RetrievalQuery",
    "RetrievedEvidence",
    "RetrievalResult",
    "KnowledgeError",
    "DocumentParsingError",
    "DocumentSecurityError",
    "EmbeddingError",
    "RetrievalError",
]
