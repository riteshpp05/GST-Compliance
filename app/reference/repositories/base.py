"""
Base reference repository interface and alias.
"""
from __future__ import annotations

from app.reference.repositories.in_memory import InMemoryReferenceRepository

BaseReferenceRepository = InMemoryReferenceRepository
ReferenceRepository = InMemoryReferenceRepository

__all__ = ["BaseReferenceRepository", "ReferenceRepository"]
