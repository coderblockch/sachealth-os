"""Unit tests for the SQLModel Bed model."""

from sqlmodel import Session, select

from models import Bed


def test_bed_defaults():
    bed = Bed(num="201", status="Available")
    assert bed.id is None
    assert bed.patient is None


def test_bed_persists_and_autogenerates_id(in_memory_engine):
    with Session(in_memory_engine) as session:
        bed = Bed(num="202", status="Occupied", patient="Sam Patient")
        session.add(bed)
        session.commit()
        session.refresh(bed)

        assert bed.id is not None
        assert bed.num == "202"
        assert bed.status == "Occupied"
        assert bed.patient == "Sam Patient"


def test_bed_roundtrip_query(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(Bed(num="203", status="Cleaning"))
        session.commit()

    with Session(in_memory_engine) as session:
        fetched = session.exec(select(Bed).where(Bed.num == "203")).one()
        assert fetched.status == "Cleaning"
        assert fetched.patient is None
