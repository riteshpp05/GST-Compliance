"""
app.knowledge.parsers.pdf_parser
================================
PDF Document Parser implementation for UC15 Knowledge Subsystem (Sprint 12.3).
Extracts text page by page using pypdf, preserving page number provenance.
"""

from __future__ import annotations

import io
from typing import Optional, Union
from app.knowledge.exceptions import DocumentParsingError
from app.knowledge.models import KnowledgeDocument, KnowledgeMetadata
from app.knowledge.parsers.base import DocumentParser

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


class PDFParser(DocumentParser):
    """Parses PDF documents into KnowledgeDocument objects."""

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

        if not PYPDF_AVAILABLE:
            raise DocumentParsingError("pypdf library is not installed. PDF parsing unavailable.")

        meta = self._default_metadata(filename, metadata)
        pages_text = []

        try:
            if isinstance(file_source, bytes):
                stream = io.BytesIO(file_source)
                reader = pypdf.PdfReader(stream)
            else:
                reader = pypdf.PdfReader(file_source)

            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception as dec_err:
                    raise DocumentParsingError(f"PDF document '{filename}' is encrypted and cannot be read: {dec_err}") from dec_err

            for idx, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- [Page {idx}] ---\n{text.strip()}")

        except DocumentParsingError:
            raise
        except Exception as exc:
            raise DocumentParsingError(f"Failed to parse PDF document '{filename}': {str(exc)}") from exc

        if not pages_text:
            raise DocumentParsingError(f"PDF document '{filename}' contains no extractable text.")

        full_content = "\n\n".join(pages_text)
        return KnowledgeDocument(
            id=meta.document_id,
            title=meta.document_name,
            metadata=meta,
            raw_content=full_content,
            file_path=file_source if isinstance(file_source, str) else None,
        )
