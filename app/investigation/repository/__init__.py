"""
app.investigation.repository package.
"""
from app.investigation.repository.base import BaseInvestigationRepository
from app.investigation.repository.in_memory import InMemoryInvestigationRepository

__all__ = ["BaseInvestigationRepository", "InMemoryInvestigationRepository"]
