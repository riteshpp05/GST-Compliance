"""
app.knowledge.exceptions
========================
Custom domain exceptions for UC15 Regulatory Knowledge & RAG Subsystem (Sprint 12.3).
"""

class KnowledgeError(Exception):
    """Base class for all knowledge subsystem errors."""
    pass


class DocumentParsingError(KnowledgeError):
    """Raised when a document parser fails to process or extract text."""
    pass


class DocumentSecurityError(KnowledgeError):
    """Raised when document ingestion violates security boundaries (file size, extension, path traversal)."""
    pass


class EmbeddingError(KnowledgeError):
    """Raised when embedding provider fails."""
    pass


class RetrievalError(KnowledgeError):
    """Raised when retrieval pipeline encounters a fatal runtime failure."""
    pass
