"""Unit tests for the database helper layer."""

import database
from sqlmodel import Session, SQLModel
from sqlalchemy import inspect

from models import Bed


def test_create_db_and_tables_creates_bed_table(monkeypatch, in_memory_engine):
    # Use a bare engine (no tables yet) so we prove the helper creates them.
    from sqlalchemy.pool import StaticPool
    from sqlmodel import create_engine

    bare_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "engine", bare_engine)

    assert "bed" not in inspect(bare_engine).get_table_names()
    database.create_db_and_tables()
    assert "bed" in inspect(bare_engine).get_table_names()


def test_get_session_yields_usable_session(monkeypatch, in_memory_engine):
    monkeypatch.setattr(database, "engine", in_memory_engine)

    generator = database.get_session()
    session = next(generator)
    try:
        assert isinstance(session, Session)
        session.add(Bed(num="301", status="Available"))
        session.commit()
    finally:
        # Exhaust the generator so the session's context manager closes it.
        generator.close()


def test_database_url_is_sqlite():
    assert database.DATABASE_URL.startswith("sqlite:///")
    assert database.DATABASE_FILE in database.DATABASE_URL


def test_resolve_database_url_defaults_to_sqlite():
    assert database.resolve_database_url(None) == database.DEFAULT_DATABASE_URL
    assert database.resolve_database_url("  ") == database.DEFAULT_DATABASE_URL


def test_resolve_database_url_normalises_postgres_schemes():
    expected = "postgresql+psycopg://u:p@db:5432/app"
    assert database.resolve_database_url("postgres://u:p@db:5432/app") == expected
    assert database.resolve_database_url("postgresql://u:p@db:5432/app") == expected
