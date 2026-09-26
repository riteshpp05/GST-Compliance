"""
app.financial.repositories
==========================
Repository abstractions and in-memory implementation for financial impact storage.
"""

from app.financial.repositories.base import BaseFinancialRepository
from app.financial.repositories.in_memory import InMemoryFinancialRepository

__all__ = [
    "BaseFinancialRepository",
    "InMemoryFinancialRepository",
]
