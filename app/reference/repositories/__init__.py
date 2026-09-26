"""
Repositories package for reference domain.
"""
from app.reference.repositories.base import BaseReferenceRepository
from app.reference.repositories.in_memory import InMemoryReferenceRepository

__all__ = [
    "BaseReferenceRepository",
    "InMemoryReferenceRepository",
]
