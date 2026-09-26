"""
app.db package
==============
Sprint 14 PostgreSQL & Relational Database Subsystem.
Provides SQLAlchemy 2.0 ORM Base, engine connection management, Alembic migrations,
JSON/Decimal serialization helpers, and relational repository implementations.
"""

from app.db.connection import get_db_engine, get_db_session, init_db, is_db_configured
from app.db.models import Base, CaseDecisionORM, CaseEventORM, CaseEvidenceRefORM, CaseORM, SessionORM, TurnORM

__all__ = [
    "Base",
    "SessionORM",
    "TurnORM",
    "CaseORM",
    "CaseDecisionORM",
    "CaseEventORM",
    "CaseEvidenceRefORM",
    "get_db_engine",
    "get_db_session",
    "init_db",
    "is_db_configured",
]
