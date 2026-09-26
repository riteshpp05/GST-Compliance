"""
app.intelligence.repositories
=============================
Repositories for persisting and querying intelligence findings.
"""

from app.intelligence.repositories.base import BaseIntelligenceRepository
from app.intelligence.repositories.in_memory import InMemoryIntelligenceRepository

__all__ = [
    "BaseIntelligenceRepository",
    "InMemoryIntelligenceRepository",
]
