"""initial schema: bed and user tables (as created by v1 of the app)

Revision ID: 0001
Revises:
Create Date: 2026-11-19

Databases created by the old ``SQLModel.metadata.create_all`` startup code
already match this revision: mark them with ``alembic stamp 0001`` and then
run ``alembic upgrade head``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bed",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("num", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("patient", sa.String(), nullable=True),
    )
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_email", table_name="user")
    op.drop_table("user")
    op.drop_table("bed")
