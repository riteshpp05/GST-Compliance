"""
app.knowledge.parsers.markdown_parser
=====================================
Markdown Document Parser implementation for UC15 Knowledge Subsystem (Sprint 12.3).
Extracts headings and preserves regulatory section structures.
"""

from __future__ import annotations

from typing import Optional, Union
from app.knowledge.exceptions import DocumentParsingError
from app.knowledge.models import KnowledgeDocument, KnowledgeMetadata
from app.knowledge.parsers.base import DocumentParser


class MarkdownParser(DocumentParser):
    """Parses Markdown (.md, .markdown) documents into KnowledgeDocument objects."""

    def parse(
        self,
        file_source: Union[str, bytes],
        filename: str,
        metadata: Optional[KnowledgeMetadata] = None,
    ) -> KnowledgeDocument:
        import os

        file_bytes = file_source if isinstance(file_source, bytes) else None
        target_name = file_source if (isinstance(file_source, str) and os.path.exists(file_source)) else filename
        self.validate_file(target_name, file_bytes)

        meta = self._default_metadata(filename, metadata)

        try:
            if isinstance(file_source, bytes):
                text = file_source.decode("utf-8", errors="replace")
            elif isinstance(file_source, str) and os.path.exists(file_source):
                with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            else:
                text = str(file_source)

        except Exception as exc:
            raise DocumentParsingError(f"Failed to read Markdown document '{filename}': {str(exc)}") from exc

        if not text or not text.strip():
            raise DocumentParsingError(f"Markdown document '{filename}' is empty.")

        return KnowledgeDocument(
            id=meta.document_id,
            title=meta.document_name,
            metadata=meta,
            raw_content=text.strip(),
            file_path=file_source if isinstance(file_source, str) else None,
        )
