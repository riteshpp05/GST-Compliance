"""
app.knowledge.chunking.pipeline
================================
Deterministic Regulatory Chunking Pipeline for UC15 Knowledge Subsystem (Sprint 12.3).
Splits KnowledgeDocument text along natural regulatory section and page boundaries while
enforcing configurable size/overlap limits and generating deterministic chunk IDs.
"""

from __future__ import annotations

import re
from typing import List, Optional
from app.knowledge.config import KnowledgeConfig, get_knowledge_config
from app.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeMetadata


class DeterministicChunker:
    """
    Splits KnowledgeDocument objects into KnowledgeChunk objects.
    Respects regulatory sections, headings, page markers, and clause boundaries.
    """

    def __init__(self, config: Optional[KnowledgeConfig] = None) -> None:
        self.config = config or get_knowledge_config()

    def chunk_document(self, document: KnowledgeDocument) -> List[KnowledgeChunk]:
        """
        Produce a list of deterministic KnowledgeChunk objects from a KnowledgeDocument.
        """
        raw_text = document.raw_content
        if not raw_text or not raw_text.strip():
            return []

        chunks: List[KnowledgeChunk] = []
        seen_hashes = set()

        # Split text into logical blocks (pages, headings, sections)
        sections = self._split_into_sections(raw_text)

        chunk_idx = 0
        for page_num, section_title, block_text in sections:
            if not block_text.strip():
                continue

            # Sub-segment block if block exceeds chunk_size
            sub_texts = self._sliding_window_split(block_text.strip(), self.config.chunk_size, self.config.chunk_overlap)

            for sub_text in sub_texts:
                clean_sub = sub_text.strip()
                if not clean_sub:
                    continue

                # Deduplication check
                content_hash = hash((document.id, page_num, section_title, clean_sub))
                if content_hash in seen_hashes:
                    continue
                seen_hashes.add(content_hash)

                chunk_idx += 1

                # Construct chunk metadata
                chunk_meta = KnowledgeMetadata(
                    document_id=document.id,
                    document_name=document.metadata.document_name,
                    document_type=document.metadata.document_type,
                    source=document.metadata.source,
                    page_number=page_num or document.metadata.page_number,
                    section=section_title or document.metadata.section,
                    chunk_id=None,
                    effective_from=document.metadata.effective_from,
                    effective_to=document.metadata.effective_to,
                    version=document.metadata.version,
                    jurisdiction=document.metadata.jurisdiction,
                    topic=document.metadata.topic,
                    authority_level=document.metadata.authority_level,
                )

                chunk_id = KnowledgeChunk.generate_deterministic_id(
                    doc_id=document.id,
                    page_number=page_num,
                    section=section_title,
                    chunk_idx=chunk_idx,
                    content=clean_sub,
                )
                chunk_meta.chunk_id = chunk_id

                chunks.append(
                    KnowledgeChunk(
                        id=chunk_id,
                        document_id=document.id,
                        content=clean_sub,
                        metadata=chunk_meta,
                    )
                )

        return chunks

    def _split_into_sections(self, text: str) -> List[tuple[Optional[int], Optional[str], str]]:
        """
        Parse text looking for page markers (--- [Page N] ---), headings, and section titles.
        Returns list of (page_num, section_title, text_content).
        """
        lines = text.splitlines()
        results = []

        current_page: Optional[int] = None
        current_section: Optional[str] = None
        current_lines: List[str] = []

        page_pattern = re.compile(r"^---\s*\[Page\s*(\d+)\]\s*---", re.IGNORECASE)
        heading_pattern = re.compile(r"^(#+|\bSection\b|\bRule\b|\bCircular\b|\bNotification\b|\bClause\b)\s+(.*)", re.IGNORECASE)

        for line in lines:
            p_match = page_pattern.match(line.strip())
            if p_match:
                if current_lines:
                    results.append((current_page, current_section, "\n".join(current_lines)))
                    current_lines = []
                current_page = int(p_match.group(1))
                continue

            h_match = heading_pattern.match(line.strip())
            if h_match and len(line.strip()) < 120:
                if current_lines:
                    results.append((current_page, current_section, "\n".join(current_lines)))
                    current_lines = []
                current_section = line.strip().lstrip("#").strip()
                current_lines.append(line)
                continue

            current_lines.append(line)

        if current_lines:
            results.append((current_page, current_section, "\n".join(current_lines)))

        return results

    def _sliding_window_split(self, text: str, max_size: int, overlap: int) -> List[str]:
        """Split text using sliding character window respecting paragraph/sentence boundaries."""
        if len(text) <= max_size:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")

        current_chunk = []
        current_len = 0

        for p in paragraphs:
            p_len = len(p)
            if current_len + p_len + 2 <= max_size:
                current_chunk.append(p)
                current_len += p_len + 2
            else:
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))

                # Handle paragraph longer than max_size
                if p_len > max_size:
                    start = 0
                    while start < p_len:
                        end = start + max_size
                        chunks.append(p[start:end])
                        start = end - overlap if end < p_len else p_len
                    current_chunk = []
                    current_len = 0
                else:
                    current_chunk = [p]
                    current_len = p_len

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks
