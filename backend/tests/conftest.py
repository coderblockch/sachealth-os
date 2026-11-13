import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, create_engine

# Ensure the backend package modules are importable when tests run from any CWD.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def in_memory_engine():
    """A fresh, isolated in-memory SQLite engine for each test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def patched_engine(monkeypatch, in_memory_engine):
    """Point both the app and the database layer at the in-memory engine."""
    import database
    import main

    monkeypatch.setattr(database, "engine", in_memory_engine)
    monkeypatch.setattr(main, "engine", in_memory_engine)
    return in_memory_engine


@pytest.fixture
def client(patched_engine):
    """A TestClient whose startup event seeds the in-memory database."""
    import main

    with TestClient(main.app) as test_client:
        yield test_client
