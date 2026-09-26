"""
Base knowledge repository interface and alias.
"""
from __future__ import annotations

from app.knowledge.repository.in_memory import InMemoryKnowledgeRepository

KnowledgeRepository = InMemoryKnowledgeRepository
BaseKnowledgeRepository = InMemoryKnowledgeRepository

__all__ = ["KnowledgeRepository", "BaseKnowledgeRepository"]
