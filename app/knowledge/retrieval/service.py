"""
app.knowledge.retrieval.service
===============================
Knowledge Retrieval Service for UC15 Knowledge Subsystem (Sprint 12.3).
Orchestrates vector similarity search, metadata filtering, temporal effective-date validation,
evidence quality status classification, and cross-document conflict detection.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from app.infrastructure.logging import get_logger
from app.knowledge.config import KnowledgeConfig, get_knowledge_config
from app.knowledge.embeddings.base import EmbeddingProvider
from app.knowledge.embeddings.factory import create_embedding_provider
from app.knowledge.models import (
    EvidenceStatus,
    KnowledgeChunk,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatus,
    RetrievedEvidence,
)
from app.knowledge.repository.base import KnowledgeRepository
from app.knowledge.repository.in_memory import InMemoryKnowledgeRepository

logger = get_logger(__name__)


class KnowledgeRetrievalService:
    """
    Evidence-grounded knowledge retrieval service.
    Combines semantic vector search, metadata filtering, temporal applicability verification,
    and cross-document contradiction checks.
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

    def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """
        Execute knowledge retrieval for query.
        Returns structured RetrievalResult containing retrieved evidence, provenance, and conflict details.
        """
        if not query.query or not query.query.strip():
            return RetrievalResult(
                query=query,
                status=RetrievalStatus.NO_MATCH,
                overall_evidence_status=EvidenceStatus.NO_EVIDENCE,
                summary="Retrieval query was empty.",
            )

        logger.info(f"Retrieving knowledge for query: '{query.query}' (Topic: {query.topic}, Date: {query.transaction_date})")

        # 1. Embed query
        query_vector = self.embedding_provider.embed_text(query.query)

        # 2. Build metadata filters
        filters: Dict[str, Any] = {}
        if query.topic:
            filters["topic"] = query.topic
        if query.jurisdiction:
            filters["jurisdiction"] = query.jurisdiction
        if query.document_type:
            filters["document_type"] = query.document_type

        # 3. Vector search
        matched_tuples = self.repository.search(
            query_vector=query_vector,
            top_k=query.top_k * 2,  # Fetch extra candidate items for temporal filtering
            filters=filters,
        )

        if not matched_tuples:
            logger.info("No matching knowledge chunks found in repository.")
            return RetrievalResult(
                query=query,
                status=RetrievalStatus.NO_MATCH,
                overall_evidence_status=EvidenceStatus.NO_EVIDENCE,
                summary="No relevant statutory or enterprise knowledge documents found matching query.",
            )

        evidence_items: List[RetrievedEvidence] = []

        # 4. Temporal evaluation & evidence classification
        for chunk, score in matched_tuples:
            if score < query.relevance_threshold:
                continue

            temporal_ok, temp_notes = self._evaluate_temporal_applicability(chunk, query.transaction_date)
            status = self._classify_evidence_status(score, temporal_ok)

            provenance = {
                "document_id": chunk.metadata.document_id,
                "document_name": chunk.metadata.document_name,
                "document_type": chunk.metadata.document_type.value,
                "source": chunk.metadata.source,
                "page_number": chunk.metadata.page_number,
                "section": chunk.metadata.section,
                "chunk_id": chunk.id,
                "effective_from": chunk.metadata.effective_from,
                "effective_to": chunk.metadata.effective_to,
                "version": chunk.metadata.version,
                "authority_level": chunk.metadata.authority_level,
            }

            evidence_items.append(
                RetrievedEvidence(
                    chunk=chunk,
                    relevance_score=round(score, 4),
                    status=status,
                    provenance=provenance,
                    temporal_applicable=temporal_ok,
                    notes=temp_notes,
                )
            )

        # Rank evidence: temporal-applicable items first, then by authority level and score
        evidence_items.sort(
            key=lambda x: (
                1 if x.temporal_applicable else 0,
                x.provenance.get("authority_level", 0),
                x.relevance_score,
            ),
            reverse=True,
        )

        top_evidence = evidence_items[: query.top_k]

        if not top_evidence:
            return RetrievalResult(
                query=query,
                status=RetrievalStatus.NO_MATCH,
                overall_evidence_status=EvidenceStatus.NO_EVIDENCE,
                summary="Retrieved evidence fell below relevance threshold.",
            )

        # 5. Deterministic Conflict Detection
        conflicts_found, conflict_details = self._detect_contradictions(top_evidence)

        if conflicts_found:
            for item in top_evidence:
                item.status = EvidenceStatus.CONFLICTING
            overall_status = EvidenceStatus.CONFLICTING
        else:
            overall_status = top_evidence[0].status

        summary = self._build_summary(query, top_evidence, conflicts_found, conflict_details)

        return RetrievalResult(
            query=query,
            evidence_items=top_evidence,
            status=RetrievalStatus.SUCCESS,
            overall_evidence_status=overall_status,
            conflicts_detected=conflicts_found,
            conflicting_details=conflict_details,
            summary=summary,
        )

    def _evaluate_temporal_applicability(self, chunk: KnowledgeChunk, tx_date_str: Optional[str]) -> tuple[bool, Optional[str]]:
        """Verify if chunk is active on transaction_date."""
        if not tx_date_str:
            return True, None

        eff_from = chunk.metadata.effective_from
        eff_to = chunk.metadata.effective_to

        if not eff_from and not eff_to:
            return True, "No effective date restrictions specified."

        try:
            tx_dt = datetime.strptime(tx_date_str, "%Y-%m-%d")

            if eff_from:
                from_dt = datetime.strptime(eff_from, "%Y-%m-%d")
                if tx_dt < from_dt:
                    return False, f"Document not yet effective on {tx_date_str} (Effective from {eff_from})."

            if eff_to:
                to_dt = datetime.strptime(eff_to, "%Y-%m-%d")
                if tx_dt > to_dt:
                    return False, f"Document expired before {tx_date_str} (Expired on {eff_to})."

            return True, f"Valid for transaction date {tx_date_str}."

        except ValueError:
            return True, "Transaction date format unparseable; bypassing temporal filter."

    def _classify_evidence_status(self, score: float, temporal_ok: bool) -> EvidenceStatus:
        """Map relevance score and temporal validity to EvidenceStatus."""
        if not temporal_ok:
            return EvidenceStatus.EXPIRED

        if score >= 0.7:
            return EvidenceStatus.SUPPORTED
        elif score >= 0.4:
            return EvidenceStatus.PARTIALLY_SUPPORTED
        elif score >= 0.2:
            return EvidenceStatus.LOW_RELEVANCE
        else:
            return EvidenceStatus.NO_EVIDENCE

    def _detect_contradictions(self, items: List[RetrievedEvidence]) -> tuple[bool, List[str]]:
        """
        Detect explicit contradictions across retrieved evidence items.
        Example: Document A specifies 18% tax rate, Document B specifies 12% tax rate for same context.
        """
        if len(items) < 2:
            return False, []

        conflict_details: List[str] = []

        # Check for tax rate contradictions
        rate_pattern = re.compile(r"(\b\d{1,2}\.?\d?%|\b\d{1,2}\s*percent\b)", re.IGNORECASE)
        found_rates: Dict[str, str] = {}

        for item in items:
            if item.relevance_score < 0.1:
                continue

            doc_name = item.provenance.get("document_name", "Doc")
            rates = rate_pattern.findall(item.chunk.content)
            for r in rates:
                r_norm = r.replace(" ", "").lower()
                if found_rates and r_norm not in found_rates.values():
                    conflict_details.append(
                        f"Tax rate conflict detected: '{doc_name}' specifies '{r}' whereas existing evidence specifies '{list(found_rates.values())[0]}'."
                    )
                found_rates[doc_name] = r_norm

        # Check for ITC eligibility contradictions
        itc_block = False
        itc_allow = False
        block_doc = ""
        allow_doc = ""

        for item in items:
            if item.relevance_score < 0.1:
                continue
            txt = item.chunk.content.lower()
            doc_name = item.provenance.get("document_name", "Doc")
            if "itc blocked" in txt or "ineligible itc" in txt or "cannot claim itc" in txt:
                itc_block = True
                block_doc = doc_name
            if "itc eligible" in txt or "can claim itc" in txt or "itc allowed" in txt:
                itc_allow = True
                allow_doc = doc_name

        if itc_block and itc_allow:
            conflict_details.append(
                f"ITC Eligibility conflict detected: '{block_doc}' states ITC is blocked/ineligible whereas '{allow_doc}' states ITC is eligible/allowed."
            )

        return len(conflict_details) > 0, conflict_details

    def _build_summary(self, query: RetrievalQuery, items: List[RetrievedEvidence], conflicts: bool, conflict_details: List[str]) -> str:
        lines = [f"Retrieved {len(items)} regulatory evidence chunks for query: '{query.query}'."]

        if conflicts:
            lines.append("WARNING: CONFLICTING REGULATORY EVIDENCE DETECTED!")
            for c in conflict_details:
                lines.append(f"- {c}")

        for idx, item in enumerate(items, 1):
            p = item.provenance
            loc_str = f"Page {p.get('page_number')}" if p.get("page_number") else f"Section: {p.get('section') or 'General'}"
            lines.append(
                f"{idx}. [{item.status.value}] Source: '{p.get('document_name')}' ({loc_str}) | Relevance: {item.relevance_score:.2f} | Effective: {p.get('effective_from') or 'ALL'} to {p.get('effective_to') or 'ONGOING'}"
            )
            lines.append(f"   Excerpt: {item.chunk.content[:200]}...")

        return "\n".join(lines)
