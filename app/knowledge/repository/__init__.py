"""
app.knowledge.repository
========================
Repository package re-exports.
"""

from app.knowledge.repository.base import KnowledgeRepository
from app.knowledge.repository.in_memory import InMemoryKnowledgeRepository

__all__ = [
    "KnowledgeRepository",
    "InMemoryKnowledgeRepository",
]
