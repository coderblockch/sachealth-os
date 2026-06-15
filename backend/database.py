from sqlmodel import SQLModel, create_engine, Session

# Name of the SQLite database file (created automatically on first run)
DATABASE_FILE = "sachealth.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# The engine is the core connection to the database
engine = create_engine(DATABASE_URL, echo=True)


def create_db_and_tables():
    # Creates the database file and all tables defined as SQLModel models
    SQLModel.metadata.create_all(engine)


def get_session():
    # Provides a database session for each request, then closes it
    with Session(engine) as session:
        yield session