"""Alembic migrations: upgrade/downgrade work and match the SQLModel models.

Runs against a temporary SQLite file by default. Set TEST_POSTGRES_URL
(e.g. postgresql://postgres:postgres@localhost:5432/sachealth_test) to run the
same checks against PostgreSQL, as the `postgres` CI job does.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlmodel import Session, SQLModel

import database
import models  # noqa: F401

BACKEND = Path(__file__).resolve().parent.parent


def _urls():
    yield pytest.param("sqlite", id="sqlite")
    if os.getenv("TEST_POSTGRES_URL"):
        yield pytest.param("postgres", id="postgres")


@pytest.fixture(params=list(_urls()))
def db_url(request, tmp_path):
    if request.param == "sqlite":
        yield f"sqlite:///{tmp_path / 'migrations.db'}"
        return
    url = database.resolve_database_url(os.environ["TEST_POSTGRES_URL"])
    engine = create_engine(url)
    with engine.begin() as conn:  # start from an empty schema
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    engine.dispose()
    yield url


def _config(url):
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


def _run(url, fn, *args):
    engine = create_engine(url)
    with engine.begin() as connection:
        cfg = _config(url)
        cfg.attributes["connection"] = connection
        fn(cfg, *args)
    engine.dispose()


def test_upgrade_head_matches_models(db_url):
    _run(db_url, command.upgrade, "head")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), SQLModel.metadata)
        tables = set(inspect(conn).get_table_names())
    engine.dispose()
    assert diff == [], f"models.py and migrations are out of sync: {diff}"
    assert {"bed", "user", "patient", "triage_record", "alembic_version"} <= tables


def test_downgrade_to_base_and_back(db_url):
    _run(db_url, command.upgrade, "head")
    _run(db_url, command.downgrade, "base")
    engine = create_engine(db_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
    _run(db_url, command.upgrade, "head")


def test_upgrade_preserves_v1_data(db_url):
    """A database created by the old app (revision 0001) keeps its rows."""
    _run(db_url, command.upgrade, "0001")
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO bed (num, status, patient) VALUES ('101', 'Occupied', 'John Doe')"))
    engine.dispose()
    _run(db_url, command.upgrade, "head")
    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT num, status, patient, updated_at FROM bed")).one()
    engine.dispose()
    assert row[:3] == ("101", "Occupied", "John Doe") and row[3] is not None


def test_seed_script_is_idempotent(db_url, monkeypatch):
    import main
    import seed

    _run(db_url, command.upgrade, "head")
    engine = create_engine(db_url)
    monkeypatch.setattr(main, "engine", engine)
    seed.run()
    seed.run()
    with Session(engine) as session:
        counts = {
            t: session.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar_one()
            for t in ("bed", "user", "patient", "triage_record")
        }
        linked = session.execute(text("SELECT COUNT(*) FROM bed WHERE patient_id IS NOT NULL")).scalar_one()
    engine.dispose()
    assert counts == {"bed": 5, "user": 1, "patient": 4, "triage_record": 4}
    assert linked == 3


def test_seed_does_not_overwrite_edited_occupants(db_url, monkeypatch):
    import main
    import seed

    _run(db_url, command.upgrade, "head")
    engine = create_engine(db_url)
    monkeypatch.setattr(main, "engine", engine)
    main.seed_demo_data()
    with engine.begin() as conn:
        conn.execute(text("UPDATE bed SET patient = 'Someone Else' WHERE num = '101'"))
    seed.run()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT patient, patient_id FROM bed WHERE num = '101'")).one()
    engine.dispose()
    assert row == ("Someone Else", None)


def test_app_startup_can_run_migrations_and_seed(db_url, monkeypatch):
    """DB_RUN_MIGRATIONS=true: the app upgrades an empty DB and seeds it."""
    from fastapi.testclient import TestClient

    import main

    engine = create_engine(db_url)
    monkeypatch.setattr(main, "engine", engine)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(main, "DB_RUN_MIGRATIONS", True)
    monkeypatch.setattr(main, "SEED_DEMO_PATIENTS", True)
    for _ in range(2):  # a restart must be a no-op
        with TestClient(main.app) as client:
            assert client.get("/health").status_code == 200
            stats = client.get("/stats").json()
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        patients = conn.execute(text("SELECT COUNT(*) FROM patient")).scalar_one()
    engine.dispose()
    assert version == "0002" and patients == 4
    assert sum(stats["beds_by_status"].values()) == 5
