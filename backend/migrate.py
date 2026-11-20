"""Run Alembic migrations from Python (used on app startup when
DB_RUN_MIGRATIONS=true, e.g. on Render where the start command is just uvicorn).

Equivalent CLI: ``cd backend && alembic upgrade head``.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parent


def upgrade_to_head(engine: Engine) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
