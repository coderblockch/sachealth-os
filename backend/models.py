from sqlmodel import SQLModel, Field
from typing import Optional


class Bed(SQLModel, table=True):
    # table=True tells SQLModel this is a real database table

    # Primary key: unique identifier for each bed.
    # default=None + primary_key=True lets the DB auto-generate it (1, 2, 3...)
    id: Optional[int] = Field(default=None, primary_key=True)

    # Bed number (e.g. "101"). Stored as text.
    num: str

    # Bed status (Occupied, Available, Pending_Discharge, Cleaning)
    status: str

    # Patient name. Optional because an empty bed has no patient (None).