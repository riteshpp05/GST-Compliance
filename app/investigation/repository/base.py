"""
Base investigation repository interface and alias.
"""
from __future__ import annotations

from app.investigation.repository.in_memory import InMemoryInvestigationRepository

BaseInvestigationRepository = InMemoryInvestigationRepository
InvestigationRepository = InMemoryInvestigationRepository

__all__ = ["BaseInvestigationRepository", "InvestigationRepository"]
