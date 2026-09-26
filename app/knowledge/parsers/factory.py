"""
app.knowledge.parsers.factory
==============================
Factory for instantiating appropriate DocumentParser by file extension (Sprint 12.3).
"""

from __future__ import annotations

import os
from typing import Optional
from app.knowledge.exceptions import DocumentSecurityError
from app.knowledge.parsers.base import DocumentParser
from app.knowledge.parsers.docx_parser import DOCXParser
from app.knowledge.parsers.markdown_parser import MarkdownParser
from app.knowledge.parsers.pdf_parser import PDFParser
from app.knowledge.parsers.txt_parser import TXTParser


class ParserFactory:
    """Factory creating appropriate DocumentParser for a given filename."""

    @staticmethod
    def get_parser(filename: str, config=None) -> DocumentParser:
        clean_name = os.path.basename(filename)
        _, ext = os.path.splitext(clean_name.lower())

        if ext == ".pdf":
            return PDFParser(config=config)
        elif ext == ".docx":
            return DOCXParser(config=config)
        elif ext in [".txt"]:
            return TXTParser(config=config)
        elif ext in [".md", ".markdown"]:
            return MarkdownParser(config=config)
        else:
            raise DocumentSecurityError(f"Unsupported file format: '{ext}'")
