import os

from sqlmodel import SQLModel, create_engine, Session

# Name of the SQLite database file (created automatically on first run)
DATABASE_FILE = "sachealth.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# SQL echo logs every statement (including data) and is disabled by default to
# avoid leaking sensitive information. Enable with SQL_ECHO=true for debugging.
SQL_ECHO = os.getenv("SQL_ECHO", "false").lower() in ("1", "true", "yes")

# The engine is the core connection to the database
engine = create_engine(DATABASE_URL, echo=SQL_ECHO)


def create_db_and_tables():
    # Creates the database file and all tables defined as SQLModel models
    SQLModel.metadata.create_all(engine)


def get_session():
    # Provides a database session for each request, then closes it
    with Session(engine) as session:
        yield session