"""
app.knowledge.models
====================
Pydantic domain models and enums for UC15 Knowledge & Regulatory Intelligence Subsystem (Sprint 12.3).
Provides strictly typed, serializable structures for documents, chunks, metadata,
retrieval queries, retrieved evidence, and conflict evaluation results.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Taxonomy of statutory and enterprise knowledge document categories."""
    GST_RULE = "GST_RULE"
    GST_NOTIFICATION = "GST_NOTIFICATION"
    GST_CIRCULAR = "GST_CIRCULAR"
    GST_FAQ = "GST_FAQ"
    COMPANY_POLICY = "COMPANY_POLICY"
    INTERNAL_CONTROL = "INTERNAL_CONTROL"


class EvidenceStatus(str, Enum):
    """Quality and verification status of retrieved regulatory evidence."""
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    LOW_RELEVANCE = "LOW_RELEVANCE"
    CONFLICTING = "CONFLICTING"
    EXPIRED = "EXPIRED"
    NO_EVIDENCE = "NO_EVIDENCE"


class RetrievalStatus(str, Enum):
    """Execution status of a knowledge retrieval query."""
    SUCCESS = "SUCCESS"
    NO_MATCH = "NO_MATCH"
    FILTER_EXCLUDED = "FILTER_EXCLUDED"
    ERROR = "ERROR"


class KnowledgeProviderStatus(str, Enum):
    """Operating status of embedding and vector repository providers."""
    ACTIVE = "ACTIVE"
    MOCK_FALLBACK = "MOCK_FALLBACK"
    DISABLED = "DISABLED"
    ERROR = "ERROR"


class KnowledgeMetadata(BaseModel):
    """Structured metadata preserving regulatory provenance, temporal scope, and authority."""
    document_id: str = Field(..., description="Unique deterministic identifier of parent document.")
    document_name: str = Field(..., description="Original filename or document title.")
    document_type: DocumentType = Field(DocumentType.GST_RULE, description="Regulatory authority category.")
    source: str = Field("SYSTEM_INGEST", description="Source origin (file path, URL, or official gazette).")
    page_number: Optional[int] = Field(None, description="1-based page number if extracted from page-based formats.")
    section: Optional[str] = Field(None, description="Heading, rule, or clause section identifier (e.g. 'Rule 36(4)').")
    chunk_id: Optional[str] = Field(None, description="Deterministic chunk identifier.")
    effective_from: Optional[str] = Field(None, description="ISO date (YYYY-MM-DD) when regulation became active.")
    effective_to: Optional[str] = Field(None, description="ISO date (YYYY-MM-DD) when regulation expired/superseded.")
    version: Optional[str] = Field("1.0", description="Regulatory document or amendment version.")
    jurisdiction: Optional[str] = Field("CENTRAL", description="Target GST jurisdiction (e.g. 'CENTRAL', 'MAHARASHTRA').")
    topic: Optional[str] = Field(None, description="Tax topic classification (e.g. 'TAX_RATE', 'ITC', 'EWAY_BILL').")
    authority_level: int = Field(5, ge=1, le=10, description="Hierarchical authority rank (GST_RULE=10 .. INTERNAL_CONTROL=2).")


class KnowledgeDocument(BaseModel):
    """Complete parsed knowledge document container."""
    id: str = Field(
        default_factory=lambda: f"DOC-{uuid.uuid4().hex[:8].upper()}",
        description="Unique document ID.",
    )
    title: str = Field(..., description="Document title or header.")
    metadata: KnowledgeMetadata
    raw_content: str = Field(..., description="Full extracted text content.")
    file_path: Optional[str] = Field(None, description="Path on disk if file-backed.")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO UTC creation timestamp.",
    )


class KnowledgeChunk(BaseModel):
    """Single text chunk with embedded vector representation and regulatory metadata."""
    id: str = Field(..., description="Deterministic chunk ID.")
    document_id: str = Field(..., description="Parent KnowledgeDocument ID.")
    content: str = Field(..., description="Chunk text content.")
    metadata: KnowledgeMetadata
    embedding: Optional[List[float]] = Field(None, description="Vector embedding float array.")

    @staticmethod
    def generate_deterministic_id(doc_id: str, page_number: Optional[int], section: Optional[str], chunk_idx: int, content: str) -> str:
        """Construct a deterministic chunk ID based on doc_id, location, index, and content hash."""
        seed = f"{doc_id}|p:{page_number}|s:{section}|idx:{chunk_idx}|txt:{content[:64]}"
        digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12].upper()
        return f"CHK-{doc_id}-{digest}"


class RetrievalQuery(BaseModel):
    """Structured query inputs for knowledge retrieval."""
    query: str = Field(..., description="Natural language search query.")
    topic: Optional[str] = Field(None, description="Optional topic filter.")
    transaction_date: Optional[str] = Field(None, description="Optional target transaction date for temporal validity (YYYY-MM-DD).")
    jurisdiction: Optional[str] = Field(None, description="Optional jurisdiction filter.")
    document_type: Optional[DocumentType] = Field(None, description="Optional document type filter.")
    top_k: int = Field(3, ge=1, le=20, description="Number of top relevant chunks to retrieve.")
    relevance_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum relevance score threshold.")


class RetrievedEvidence(BaseModel):
    """Single retrieved chunk enriched with relevance score, provenance, and temporal status."""
    chunk: KnowledgeChunk
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Cosine similarity score.")
    status: EvidenceStatus = Field(..., description="Evidence verification status.")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Complete audit provenance dictionary.")
    temporal_applicable: bool = Field(True, description="True if evidence is valid for requested transaction date.")
    notes: Optional[str] = Field(None, description="Explanatory notes on applicability or conflicts.")


class RetrievalResult(BaseModel):
    """Full structured output payload from KnowledgeRetrievalService."""
    query: RetrievalQuery
    evidence_items: List[RetrievedEvidence] = Field(default_factory=list)
    status: RetrievalStatus = Field(RetrievalStatus.SUCCESS)
    overall_evidence_status: EvidenceStatus = Field(EvidenceStatus.NO_EVIDENCE)
    conflicts_detected: bool = Field(False)
    conflicting_details: List[str] = Field(default_factory=list)
    summary: str = Field("", description="Grounded summary of retrieved regulatory knowledge.")
