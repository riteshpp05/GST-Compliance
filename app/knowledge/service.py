"""
app.knowledge.service
=====================
High-level Knowledge Management Service for UC15 (Sprint 12.3).
Provides unified API for document ingestion, parsing, chunking, embedding, indexing,
knowledge retrieval, and status reporting.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union
from app.infrastructure.logging import get_logger
from app.knowledge.chunking.pipeline import DeterministicChunker
from app.knowledge.config import KnowledgeConfig, get_knowledge_config
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.embeddings.factory import create_embedding_provider
from app.knowledge.exceptions import DocumentParsingError, DocumentSecurityError
from app.knowledge.models import (
    DocumentType,
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeMetadata,
    RetrievalQuery,
    RetrievalResult,
)
from app.knowledge.parsers.factory import ParserFactory
from app.knowledge.repository.base import KnowledgeRepository
from app.knowledge.repository.in_memory import InMemoryKnowledgeRepository
from app.knowledge.retrieval.service import KnowledgeRetrievalService

logger = get_logger(__name__)


class KnowledgeService:
    """
    Main Facade for UC15 Knowledge & Regulatory Intelligence Subsystem.
    """

    def __init__(
        self,
        repository: Optional[KnowledgeRepository] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        config: Optional[KnowledgeConfig] = None,
    ) -> None:
        self.config = config or get_knowledge_config()
        self.repository = repository or InMemoryKnowledgeRepository()
        self.embedding_provider = embedding_provider or create_embedding_provider()
        self.chunker = DeterministicChunker(config=self.config)
        self.retrieval_service = KnowledgeRetrievalService(
            repository=self.repository,
            embedding_provider=self.embedding_provider,
            config=self.config,
        )
        self._initialize_seed_knowledge()

    def ingest_document(
        self,
        file_source: Union[str, bytes],
        filename: str,
        metadata: Optional[KnowledgeMetadata] = None,
    ) -> KnowledgeDocument:
        """
        Parse, chunk, embed, and index a document from file path or raw bytes.
        """
        logger.info(f"Ingesting document '{filename}'...")
        parser = ParserFactory.get_parser(filename, config=self.config)
        doc = parser.parse(file_source, filename, metadata=metadata)

        # Produce chunks
        chunks = self.chunker.chunk_document(doc)

        # Generate embeddings
        for chunk in chunks:
            chunk.embedding = self.embedding_provider.embed_text(chunk.content)

        # Index in repository
        self.repository.add_document(doc)
        self.repository.add_chunks(chunks)

        logger.info(f"Successfully ingested '{filename}' (ID: {doc.id}): {len(chunks)} chunks indexed.")
        return doc

    def ingest_text_content(
        self,
        title: str,
        content: str,
        metadata: Optional[KnowledgeMetadata] = None,
    ) -> KnowledgeDocument:
        """
        Ingest raw text content directly as a KnowledgeDocument.
        """
        doc_id = f"DOC-{title.upper().replace(' ', '_')[:24]}"
        meta = metadata or KnowledgeMetadata(
            document_id=doc_id,
            document_name=title,
            document_type=DocumentType.GST_RULE,
            source="DIRECT_INGEST",
        )
        meta.document_id = doc_id

        doc = KnowledgeDocument(
            id=doc_id,
            title=title,
            metadata=meta,
            raw_content=content,
        )

        chunks = self.chunker.chunk_document(doc)
        for chunk in chunks:
            chunk.embedding = self.embedding_provider.embed_text(chunk.content)

        self.repository.add_document(doc)
        self.repository.add_chunks(chunks)

        logger.info(f"Direct text ingestion for '{title}' complete: {len(chunks)} chunks indexed.")
        return doc

    def retrieve(self, query: Union[RetrievalQuery, str, dict]) -> RetrievalResult:
        """
        Execute knowledge retrieval for query object, raw query string, or dict.
        """
        if isinstance(query, str):
            req = RetrievalQuery(query=query)
        elif isinstance(query, dict):
            req = RetrievalQuery.model_validate(query)
        else:
            req = query

        return self.retrieval_service.retrieve(req)

    def list_documents(self) -> List[KnowledgeDocument]:
        return self.repository.list_documents()

    def delete_document(self, doc_id: str) -> bool:
        return self.repository.delete_document(doc_id)

    def get_status(self) -> Dict[str, Any]:
        docs = self.list_documents()
        return {
            "document_count": len(docs),
            "chunk_count": len(getattr(self.repository, "_chunks", {})),
            "embedding_provider": self.embedding_provider.get_status(),
        }

    def _initialize_seed_knowledge(self) -> None:
        """
        Seed standard GST rules and policy knowledge into repository on startup.
        """
        seed_docs = [
            {
                "title": "GST Rule 36(4) - ITC Availability Conditions",
                "content": (
                    "Section 16(2) of the CGST Act & Rule 36(4) specify conditions for claiming Input Tax Credit (ITC).\n"
                    "1. Tax invoice or debit note must be issued by the registered supplier.\n"
                    "2. Invoice details must be uploaded by supplier in GSTR-1 and reflected in GSTR-2B.\n"
                    "3. Tax charged in respect of supply must have been actually paid to the Government.\n"
                    "4. Recipient must have received the goods or services.\n"
                    "Effective from 2022-01-01. 100% matched GSTR-2B reflection is mandatory before claiming ITC."
                ),
                "metadata": KnowledgeMetadata(
                    document_id="DOC-GST-RULE-36-4",
                    document_name="GST Rule 36(4) ITC Rule",
                    document_type=DocumentType.GST_RULE,
                    source="CBIC statutory notification",
                    section="Rule 36(4)",
                    effective_from="2022-01-01",
                    topic="ITC",
                    authority_level=10,
                ),
            },
            {
                "title": "GST Tax Rates Master Schedule & HSN Guidelines",
                "content": (
                    "GST Tax Rates & Place of Supply Rules under CGST Act Section 8 & IGST Act Section 10:\n"
                    "1. Standard GST Tax Rates in India are 0%, 5%, 12%, 18%, and 28%.\n"
                    "2. Intra-state supplies (Supplier and POS in same state) require equal CGST and SGST/UTGST.\n"
                    "3. Inter-state supplies (Supplier and POS in different states) require IGST.\n"
                    "4. If CGST/SGST is incorrectly charged on inter-state supply, or IGST charged on intra-state supply, Gate 4 Place of Supply validation fails."
                ),
                "metadata": KnowledgeMetadata(
                    document_id="DOC-GST-TAX-RATES",
                    document_name="GST Tax Rates & POS Guidelines",
                    document_type=DocumentType.GST_RULE,
                    source="CBIC Tax Rate Circular",
                    section="Section 8 & 10",
                    effective_from="2017-07-01",
                    topic="TAX_RATE",
                    authority_level=10,
                ),
            },
            {
                "title": "E-Way Bill Requirement Threshold Rule 138",
                "content": (
                    "Rule 138 of CGST Rules - E-Way Bill Provisions:\n"
                    "1. E-Way Bill is mandatory for movement of goods where consignment value exceeds Rs. 50,000.\n"
                    "2. Value excludes exempt supplies and includes GST taxes.\n"
                    "3. Invoices with taxable consignment value > Rs. 50,000 missing valid EWB number fail Gate 5 E-Way Bill compliance."
                ),
                "metadata": KnowledgeMetadata(
                    document_id="DOC-GST-EWAY-BILL",
                    document_name="Rule 138 E-Way Bill Guidelines",
                    document_type=DocumentType.GST_RULE,
                    source="CBIC E-Way Bill Notification",
                    section="Rule 138",
                    effective_from="2018-04-01",
                    topic="EWAY_BILL",
                    authority_level=9,
                ),
            },
        ]

        for s in seed_docs:
            try:
                self.ingest_text_content(title=s["title"], content=s["content"], metadata=s["metadata"])
            except Exception as e:
                logger.warning(f"Failed to ingest seed document '{s['title']}': {e}")
