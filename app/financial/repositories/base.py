"""
Base financial repository interface and alias.
"""
from __future__ import annotations

from app.financial.repositories.in_memory import InMemoryFinancialRepository

BaseFinancialRepository = InMemoryFinancialRepository
FinancialRepository = InMemoryFinancialRepository

__all__ = ["BaseFinancialRepository", "FinancialRepository"]
