"""
app.knowledge.repository.in_memory
==================================
In-Memory Knowledge Repository implementation for UC15 (Sprint 12.3).
Provides lightweight, thread-safe in-memory vector search and document index.
"""

from __future__ import annotations

import threading
from typing import Any, Dict, List, Optional, Tuple
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.models import KnowledgeChunk, KnowledgeDocument
class InMemoryKnowledgeRepository:
    """
    In-memory vector store and document index.
    Decoupled from specific vector DBs, permitting future pgvector migration.
    """

    def __init__(self) -> None:
        self._docs: Dict[str, KnowledgeDocument] = {}
        self._chunks: Dict[str, KnowledgeChunk] = {}
        self._lock = threading.RLock()

    def add_document(self, doc: KnowledgeDocument) -> None:
        with self._lock:
            self._docs[doc.id] = doc

    def add_chunks(self, chunks: List[KnowledgeChunk]) -> None:
        with self._lock:
            for chunk in chunks:
                self._chunks[chunk.id] = chunk
                if chunk.document_id not in self._docs and hasattr(chunk, "document"):
                    pass

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[KnowledgeChunk, float]]:
        filters = filters or {}
        results: List[Tuple[KnowledgeChunk, float]] = []

        with self._lock:
            for chunk in self._chunks.values():
                if not chunk.embedding:
                    continue

                # Filter matching
                if not self._matches_filters(chunk, filters):
                    continue

                sim = EmbeddingProvider.cosine_similarity(query_vector, chunk.embedding)
                results.append((chunk, sim))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _matches_filters(self, chunk: KnowledgeChunk, filters: Dict[str, Any]) -> bool:
        meta = chunk.metadata

        if "document_type" in filters and filters["document_type"]:
            expected = filters["document_type"]
            val = getattr(meta.document_type, "value", str(meta.document_type))
            exp_val = getattr(expected, "value", str(expected))
            if val != exp_val:
                return False

        if "topic" in filters and filters["topic"]:
            if not meta.topic or filters["topic"].upper() not in meta.topic.upper():
                return False

        if "jurisdiction" in filters and filters["jurisdiction"]:
            if meta.jurisdiction and filters["jurisdiction"].upper() != meta.jurisdiction.upper():
                return False

        if "document_id" in filters and filters["document_id"]:
            if meta.document_id != filters["document_id"]:
                return False

        return True

    def get_document(self, doc_id: str) -> Optional[KnowledgeDocument]:
        with self._lock:
            return self._docs.get(doc_id)

    def get_chunk(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        with self._lock:
            return self._chunks.get(chunk_id)

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self._docs:
                return False

            del self._docs[doc_id]
            chunk_ids_to_del = [cid for cid, c in self._chunks.items() if c.document_id == doc_id]
            for cid in chunk_ids_to_del:
                del self._chunks[cid]

            return True

    def list_documents(self) -> List[KnowledgeDocument]:
        with self._lock:
            return list(self._docs.values())

