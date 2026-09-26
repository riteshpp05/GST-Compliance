"""
app.db.connection
=================
Engine Connection Management & Session Scope for Sprint 14 Relational Persistence.
Supports configurable PERSISTENCE_BACKEND ('memory' vs 'db' / 'sqlalchemy' / 'postgres')
and DATABASE_URL configuration.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[Engine] = None
_sessionmaker: Optional[sessionmaker] = None


def get_persistence_backend() -> str:
    """
    Retrieve configured persistence backend name.
    Options: 'memory' (default), 'db', 'sqlalchemy', 'postgres', 'sqlite'.
    """
    return os.environ.get("PERSISTENCE_BACKEND", "memory").lower().strip()


def get_database_url() -> str:
    """
    Retrieve DATABASE_URL from environment or fallback to local SQLite for ORM testing.
    In PRODUCTION mode (APP_ENV=production), fallback to SQLite is strictly forbidden.
    Supports automatic detection of PostgreSQL credentials from Cloud Foundry VCAP_SERVICES.
    """
    import json

    env = os.environ.get("APP_ENV", "development").lower().strip()
    is_prod = env in ("production", "prod")
    url = os.environ.get("DATABASE_URL", "").strip()

    if not url and "VCAP_SERVICES" in os.environ:
        try:
            vcap = json.loads(os.environ["VCAP_SERVICES"])
            for svc_name, instances in vcap.items():
                for inst in instances:
                    creds = inst.get("credentials", {})
                    candidate_uri = creds.get("uri") or creds.get("url")
                    if candidate_uri and ("postgres" in candidate_uri or "postgresql" in candidate_uri):
                        url = candidate_uri
                        break
                    if "hostname" in creds and "username" in creds and "password" in creds:
                        h = creds["hostname"]
                        p = creds.get("port", 5432)
                        u = creds["username"]
                        pw = creds["password"]
                        db = creds.get("dbname") or creds.get("database", "postgres")
                        url = f"postgresql://{u}:{pw}@{h}:{p}/{db}"
                        break
                if url:
                    break
        except Exception as e:
            logger.warning(f"Failed to parse VCAP_SERVICES for database: {e}")

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    if is_prod:
        if not url or url.startswith("sqlite"):
            raise RuntimeError(
                "Production configuration error: Valid PostgreSQL DATABASE_URL is required in production mode. "
                "SQLite fallback is strictly forbidden when APP_ENV=production."
            )
        return url

    if not url:
        default_sqlite_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "scratch", "uc15_s14.db")
        )
        os.makedirs(os.path.dirname(default_sqlite_path), exist_ok=True)
        url = f"sqlite:///{default_sqlite_path}"
    return url


def is_db_configured() -> bool:
    """Check if persistence backend is set to a database implementation."""
    backend = get_persistence_backend()
    return backend in {"db", "sqlalchemy", "postgres", "sqlite", "relational"}


def get_db_engine() -> Engine:
    """Lazy-initialize and return global SQLAlchemy engine."""
    global _engine
    if _engine is None:
        env = os.environ.get("APP_ENV", "development").lower().strip()
        is_prod = env in ("production", "prod")
        db_url = get_database_url()

        if is_prod and db_url.startswith("sqlite"):
            raise RuntimeError(
                "Production configuration error: SQLite engine initialization forbidden in production mode."
            )

        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            engine_kwargs = {"connect_args": connect_args}
        else:
            engine_kwargs = {
                "pool_pre_ping": True,
                "pool_size": 10,
                "max_overflow": 20,
            }

        logger.info(f"Initializing SQLAlchemy engine for persistence backend '{get_persistence_backend()}'")
        _engine = create_engine(db_url, **engine_kwargs)
    return _engine


def get_sessionmaker() -> sessionmaker:
    """Lazy-initialize global sessionmaker factory."""
    global _sessionmaker
    if _sessionmaker is None:
        engine = get_db_engine()
        init_db()
        _sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _sessionmaker


def get_db_session() -> Session:
    """Create a new SQLAlchemy Session."""
    sm = get_sessionmaker()
    return sm()


@contextmanager
def db_session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = get_db_session()
    try:
        yield session
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error(f"Transaction rollback triggered due to exception: {exc}")
        raise exc
    finally:
        session.close()


def init_db() -> None:
    """Initialize database tables via SQLAlchemy metadata (used for dev/test setup)."""
    from app.db.models import Base
    engine = get_db_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Executed Base.metadata.create_all() for database schema initialization.")


def reset_db_connection() -> None:
    """Reset global engine and sessionmaker (used for testing simulated process restarts)."""
    global _engine, _sessionmaker
    if _engine:
        _engine.dispose()
    _engine = None
    _sessionmaker = None
