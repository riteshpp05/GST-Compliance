"""
Base historical repository interface and alias.
"""
from __future__ import annotations

from app.historical.repositories.in_memory import InMemoryHistoricalRepository

BaseHistoricalRepository = InMemoryHistoricalRepository
HistoricalRepository = InMemoryHistoricalRepository

__all__ = ["BaseHistoricalRepository", "HistoricalRepository"]
