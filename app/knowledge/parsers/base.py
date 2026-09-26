"""
app.knowledge.parsers.base
==========================
Abstract base class and security validator for document parsers (Sprint 12.3).
Enforces file extension checks, file size limits, path traversal protection,
and safe temporary file handling.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional, Union
from app.knowledge.config import get_knowledge_config
from app.knowledge.exceptions import DocumentParsingError, DocumentSecurityError
from app.knowledge.models import DocumentType, KnowledgeDocument, KnowledgeMetadata


class DocumentParser(ABC):
    """
    Abstract Base Class for secure document parsing.
    Parsed documents are treated as DATA ONLY. No code or script execution permitted.
    """

    def __init__(self, config=None) -> None:
        self.config = config or get_knowledge_config()

    def validate_file(self, file_path_or_name: str, file_bytes: Optional[bytes] = None) -> None:
        """
        Enforce security boundaries before parsing:
        - Path traversal prevention
        - Allowed file extensions
        - File size limits
        - Null byte / malformed name checks
        """
        clean_name = os.path.basename(file_path_or_name)
        if ".." in file_path_or_name or "\0" in file_path_or_name:
            raise DocumentSecurityError(f"Path traversal or invalid characters detected in filename: '{file_path_or_name}'")

        _, ext = os.path.splitext(clean_name.lower())
        if ext not in self.config.allowed_extensions:
            raise DocumentSecurityError(
                f"File extension '{ext}' is prohibited. Allowed extensions: {self.config.allowed_extensions}"
            )

        if file_bytes is not None:
            if len(file_bytes) > self.config.max_file_size_bytes:
                raise DocumentSecurityError(
                    f"File size ({len(file_bytes)} bytes) exceeds maximum limit ({self.config.max_file_size_bytes} bytes)."
                )
        elif os.path.exists(file_path_or_name):
            size = os.path.getsize(file_path_or_name)
            if size > self.config.max_file_size_bytes:
                raise DocumentSecurityError(
                    f"File size ({size} bytes) exceeds maximum limit ({self.config.max_file_size_bytes} bytes)."
                )

    @abstractmethod
    def parse(
        self,
        file_source: Union[str, bytes],
        filename: str,
        metadata: Optional[KnowledgeMetadata] = None,
    ) -> KnowledgeDocument:
        """
        Extract text content and page/section metadata from file source.
        Must return a structured KnowledgeDocument object.
        """
        pass

    def _default_metadata(self, filename: str, metadata: Optional[KnowledgeMetadata] = None) -> KnowledgeMetadata:
        """Build fallback KnowledgeMetadata if not provided."""
        if metadata:
            return metadata

        doc_id = f"DOC-{os.path.splitext(filename)[0].upper().replace(' ', '_')}"
        return KnowledgeMetadata(
            document_id=doc_id,
            document_name=filename,
            document_type=DocumentType.GST_RULE,
            source=filename,
        )
