"""Datenbankverbindung (SQLAlchemy). Lokal SQLite, später austauschbar gegen PostgreSQL."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, inspect, text
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
    """Legt fehlende Tabellen an und ergänzt neue Spalten in bestehenden Tabellen.

    Für die bisherigen Änderungen reicht das: neue Spalten sind immer optional
    (NULL erlaubt). Für umfangreichere Umbauten käme später Alembic infrage.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    add_missing_columns(engine)


def add_missing_columns(engine: Engine) -> list[str]:
    """Fügt Spalten hinzu, die im Modell stehen, aber in der Datenbank fehlen."""
    inspector = inspect(engine)
    added = []
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}')
                )
                added.append(f"{table.name}.{column.name}")
    return added


def session_scope() -> Iterator[Session]:
    """FastAPI-Dependency: eine Session pro Anfrage."""
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
