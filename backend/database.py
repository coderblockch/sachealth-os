import os
import sqlite3

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine, Session

# Default: a local SQLite file (created automatically on first run).
# Set DATABASE_URL to use another database, e.g. PostgreSQL:
#   DATABASE_URL=postgresql://user:password@host:5432/sachealth
DATABASE_FILE = "sachealth.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DATABASE_FILE}"


def resolve_database_url(raw_url: str | None) -> str:
    """Return a SQLAlchemy URL, normalising Heroku/Render style postgres:// URLs."""
    url = (raw_url or "").strip() or DEFAULT_DATABASE_URL
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = resolve_database_url(os.getenv("DATABASE_URL"))

# SQL echo logs every statement (including data) and is disabled by default to
# avoid leaking sensitive information. Enable with SQL_ECHO=true for debugging.
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")

# SQLite needs check_same_thread=False because FastAPI may use the connection
# from different threads; other databases do not accept this argument.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Pool sizing only applies to server databases (PostgreSQL); SQLite ignores it.
_pool_args = (
    {}
    if DATABASE_URL.startswith("sqlite")
    else {
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "5")),
        "pool_recycle": 1800,
    }
)

# The engine is the core connection to the database
engine = create_engine(
    DATABASE_URL, echo=SQL_ECHO, connect_args=_connect_args, pool_pre_ping=True, **_pool_args
)

# When true (default, handy for local SQLite), tables are created on startup.
# In production the schema is managed by Alembic (`alembic upgrade head`), so
# render.yaml sets DB_AUTO_CREATE=false.
DB_AUTO_CREATE = os.getenv("DB_AUTO_CREATE", "true").lower() in ("1", "true", "yes")


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    """SQLite ignores FOREIGN KEY / ON DELETE rules unless this pragma is on."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_db_and_tables():
    # Creates the database file and all tables defined as SQLModel models
    SQLModel.metadata.create_all(engine)


def get_session():
    # Provides a database session for each request, then closes it
    with Session(engine) as session:
        yield session
