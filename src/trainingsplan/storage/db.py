"""Datenbankverbindung (SQLAlchemy). Lokal SQLite, später austauschbar gegen PostgreSQL."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from trainingsplan.config import get_settings
from trainingsplan.storage.models import Base


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    settings.ensure_dirs()
    return create_engine(settings.db_url)


def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def init_db() -> None:
    """Legt alle Tabellen an. Später ersetzt durch Migrationen (Alembic)."""
    Base.metadata.create_all(get_engine())


def session_scope() -> Iterator[Session]:
    """FastAPI-Dependency: eine Session pro Anfrage."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
