"""Seed the database with demo data (fake people only). Safe to run repeatedly.

    cd backend
    alembic upgrade head   # make sure the schema exists
    python seed.py         # beds, demo staff user, demo patients + triage history

Uses DATABASE_URL like the app. The demo staff account comes from
DEMO_USER_EMAIL / DEMO_USER_PASSWORD.
"""

import logging

from sqlmodel import Session, select

import main
from models import Bed, Patient, TriageRecord, User

logger = logging.getLogger("sachealth.seed")

# (name, age, oxygen, symptoms, bed number or None)
DEMO_PATIENTS = [
    ("John Doe", 64, 87, "shortness of breath, chest pain", "101"),
    ("Jane Smith", 75, 93, "persistent cough", "102"),
    ("Robert Wilson", 52, 96, "fever and headache", "105"),
    ("Maria Lopez", 31, 98, "sprained ankle", None),
]


def seed_demo_patients() -> int:
    """Create demo patients with one triage record each and link the occupied
    demo beds to them. Does nothing if any patient already exists.
    Returns the number of patients created."""
    with Session(main.engine) as session:
        if session.exec(select(Patient)).first():
            return 0
        staff = session.exec(
            select(User).where(User.email == main.DEMO_USER_EMAIL.strip().lower())
        ).first()
        for name, age, oxygen, symptoms, bed_num in DEMO_PATIENTS:
            patient = Patient(full_name=name, age=age)
            session.add(patient)
            session.flush()
            priority, recommendation, urgency = main.evaluate_triage(age, oxygen, symptoms)
            session.add(
                TriageRecord(
                    patient_id=patient.id,
                    age=age,
                    oxygen_level=oxygen,
                    symptoms=symptoms,
                    priority=priority,
                    recommendation=recommendation,
                    urgency=urgency,
                    created_by_id=staff.id if staff else None,
                )
            )
            if bed_num:
                bed = session.exec(select(Bed).where(Bed.num == bed_num)).first()
                if bed and bed.patient_id is None and bed.status in ("Occupied", "Pending_Discharge"):
                    bed.patient_id = patient.id
                    bed.patient = name
                    session.add(bed)
        session.commit()  # all demo rows are written in one transaction
        return len(DEMO_PATIENTS)


def run() -> None:
    main.seed_demo_data()
    created = seed_demo_patients()
    logger.info("Seed complete (%s demo patients created)", created)
    print(f"Seed complete: beds + demo user ensured, {created} demo patients created.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
