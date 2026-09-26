"""
app.knowledge.config
====================
Configuration settings for UC15 Knowledge & RAG Subsystem (Sprint 12.3).
"""

import os
from typing import List
from pydantic import BaseModel, Field


class KnowledgeConfig(BaseModel):
    """Configuration options for document ingestion, chunking, embeddings, and vector store."""
    max_file_size_bytes: int = Field(10 * 1024 * 1024, description="Maximum allowed file size for upload (10 MB).")
    allowed_extensions: List[str] = Field(
        default_factory=lambda: [".pdf", ".docx", ".txt", ".md", ".markdown"],
        description="Allowed document extensions.",
    )
    chunk_size: int = Field(500, description="Target character length for text chunks.")
    chunk_overlap: int = Field(50, description="Character overlap between consecutive chunks.")
    default_relevance_threshold: float = Field(0.3, description="Minimum relevance score for retrieved evidence.")
    default_top_k: int = Field(3, description="Default top-k chunks to retrieve.")
    embedding_provider_name: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "auto"),
        description="Embedding provider name ('auto', 'mock', 'openai').",
    )
    storage_dir: str = Field(
        default_factory=lambda: os.getenv("KNOWLEDGE_STORAGE_DIR", "data/knowledge"),
        description="Directory for storing uploaded documents and persisted indexes.",
    )


def get_knowledge_config() -> KnowledgeConfig:
    """Return default KnowledgeConfig instance."""
    return KnowledgeConfig()
