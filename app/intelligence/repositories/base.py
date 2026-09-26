"""
Base intelligence repository interface and alias.
"""
from __future__ import annotations

from app.intelligence.repositories.in_memory import InMemoryIntelligenceRepository

BaseIntelligenceRepository = InMemoryIntelligenceRepository
IntelligenceRepository = InMemoryIntelligenceRepository

__all__ = ["BaseIntelligenceRepository", "IntelligenceRepository"]
