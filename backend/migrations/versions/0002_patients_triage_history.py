"""patients, triage history, constraints and indexes

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19

- new ``patient`` and ``triage_record`` tables with foreign keys
- ``bed``: unique bed number, status CHECK + index, ``patient_id`` FK
  (unique: one bed per patient), ``updated_at`` timestamp
- length limits that match the API validation
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BED_STATUS_CHECK = "status IN ('Available', 'Occupied', 'Pending_Discharge', 'Cleaning')"


def upgrade() -> None:
    op.create_table(
        "patient",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("age >= 0 AND age <= 130", name="ck_patient_age_range"),
        sa.PrimaryKeyConstraint("id", name="pk_patient"),
    )
    op.create_index("ix_patient_full_name", "patient", ["full_name"], unique=False)

    op.create_table(
        "triage_record",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("oxygen_level", sa.Integer(), nullable=False),
        sa.Column("symptoms", sa.String(length=2000), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("recommendation", sa.String(length=80), nullable=False),
        sa.Column("urgency", sa.String(length=20), nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority BETWEEN 1 AND 4", name="ck_triage_priority_range"),
        sa.CheckConstraint(
            "oxygen_level >= 0 AND oxygen_level <= 100", name="ck_triage_oxygen_range"
        ),
        sa.CheckConstraint("age >= 0 AND age <= 130", name="ck_triage_age_range"),
        sa.ForeignKeyConstraint(
            ["patient_id"], ["patient.id"],
            name="fk_triage_record_patient_id_patient", ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["user.id"],
            name="fk_triage_record_created_by_id_user", ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_triage_record"),
    )
    op.create_index(
        "ix_triage_record_patient_created", "triage_record", ["patient_id", "created_at"]
    )
    op.create_index(
        "ix_triage_record_priority_created", "triage_record", ["priority", "created_at"]
    )

    # batch_alter_table recreates the table on SQLite and uses ALTER on PostgreSQL.
    with op.batch_alter_table("bed") as batch:
        batch.alter_column("num", type_=sa.String(length=20), existing_nullable=False)
        batch.alter_column("status", type_=sa.String(length=20), existing_nullable=False)
        batch.alter_column("patient", type_=sa.String(length=120), existing_nullable=True)
        batch.add_column(sa.Column("patient_id", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),  # backfills existing rows
            )
        )
        batch.create_unique_constraint("uq_bed_patient_id", ["patient_id"])
        batch.create_foreign_key(
            "fk_bed_patient_id_patient", "patient", ["patient_id"], ["id"], ondelete="SET NULL"
        )
        batch.create_check_constraint("ck_bed_status", BED_STATUS_CHECK)
        batch.create_index("ix_bed_num", ["num"], unique=True)
        batch.create_index("ix_bed_status", ["status"], unique=False)

    with op.batch_alter_table("user") as batch:
        batch.alter_column("email", type_=sa.String(length=254), existing_nullable=False)
        batch.alter_column("full_name", type_=sa.String(length=120), existing_nullable=False)
        batch.alter_column(
            "hashed_password", type_=sa.String(length=255), existing_nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("user") as batch:
        batch.alter_column("hashed_password", type_=sa.String(), existing_nullable=False)
        batch.alter_column("full_name", type_=sa.String(), existing_nullable=False)
        batch.alter_column("email", type_=sa.String(), existing_nullable=False)

    with op.batch_alter_table("bed") as batch:
        batch.drop_index("ix_bed_status")
        batch.drop_index("ix_bed_num")
        batch.drop_constraint("ck_bed_status", type_="check")
        batch.drop_constraint("fk_bed_patient_id_patient", type_="foreignkey")
        batch.drop_constraint("uq_bed_patient_id", type_="unique")
        batch.drop_column("updated_at")
        batch.drop_column("patient_id")
        batch.alter_column("patient", type_=sa.String(), existing_nullable=True)
        batch.alter_column("status", type_=sa.String(), existing_nullable=False)
        batch.alter_column("num", type_=sa.String(), existing_nullable=False)

    op.drop_index("ix_triage_record_priority_created", table_name="triage_record")
    op.drop_index("ix_triage_record_patient_created", table_name="triage_record")
    op.drop_table("triage_record")
    op.drop_index("ix_patient_full_name", table_name="patient")
    op.drop_table("patient")
