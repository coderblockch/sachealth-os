import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path
from datetime import datetime, timezone
from typing import Annotated, Generic, Literal, Optional, TypeVar

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import func, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session, col, select

from auth import (
    authenticate,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
import database
from database import create_db_and_tables, engine
from models import Bed, Patient, TriageRecord, User, utcnow

logger = logging.getLogger("sachealth")

# The static dashboard lives at the repository root (../index.html).
FRONTEND_FILE = Path(__file__).resolve().parent.parent / "index.html"
# The React app (frontend/), built by `npm run build` into frontend/dist and
# served under /app so its routes never collide with API paths like /beds.
FRONTEND_DIST = Path(
    os.getenv("FRONTEND_DIST", Path(__file__).resolve().parent.parent / "frontend" / "dist")
)

# Public demo account (fake data only). Override with env vars in production.
DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "demo@sachealth.dev")
DEMO_USER_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "sachealth-demo")

def _env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes")


# Seed demo beds/user on startup (disable with SEED_DEMO_DATA=false).
SEED_DEMO_DATA = _env_flag("SEED_DEMO_DATA", "true")
# Also seed demo patients + triage history (what `python seed.py` does).
SEED_DEMO_PATIENTS = _env_flag("SEED_DEMO_PATIENTS", "false")
# Apply Alembic migrations on startup (`alembic upgrade head`). Useful when the
# host's start command only runs uvicorn.
DB_RUN_MIGRATIONS = _env_flag("DB_RUN_MIGRATIONS", "false")


def seed_beds() -> None:
    """Insert a starter set of beds only if the table is empty."""
    with Session(engine) as session:
        if session.exec(select(Bed)).first():
            return
        session.add_all(
            [
                Bed(num="101", status="Occupied", patient="John Doe"),
                Bed(num="102", status="Pending_Discharge", patient="Jane Smith"),
                Bed(num="103", status="Available", patient=None),
                Bed(num="104", status="Cleaning", patient=None),
                Bed(num="105", status="Pending_Discharge", patient="Robert Wilson"),
            ]
        )
        session.commit()
        logger.info("Database seeded with initial beds")


def seed_demo_user() -> None:
    """Create the demo staff account if it does not exist yet."""
    email = DEMO_USER_EMAIL.strip().lower()
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.email == email)).first()
        if existing:
            # Keep the stored hash in sync if DEMO_USER_PASSWORD was rotated.
            if not verify_password(DEMO_USER_PASSWORD, existing.hashed_password):
                existing.hashed_password = hash_password(DEMO_USER_PASSWORD)
                session.add(existing)
                session.commit()
            return
        session.add(
            User(
                email=email,
                full_name="Demo Clinician",
                hashed_password=hash_password(DEMO_USER_PASSWORD),
            )
        )
        session.commit()
        logger.info("Demo user created")


def seed_demo_data() -> None:
    """Idempotent demo seed: beds and the demo staff account."""
    seed_beds()
    seed_demo_user()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DB_RUN_MIGRATIONS:
        import migrate

        migrate.upgrade_to_head(engine)
        logger.info("Database migrated to the latest Alembic revision")
    elif database.DB_AUTO_CREATE:
        create_db_and_tables()
    if SEED_DEMO_DATA:
        seed_demo_data()
        if SEED_DEMO_PATIENTS:
            import seed

            seed.seed_demo_patients()
    yield


app = FastAPI(title="SacHealth OS Core", lifespan=lifespan)

# Restrict CORS to an explicit allow-list. Configure via the
# ALLOWED_ORIGINS env var (comma-separated); defaults to the local
# development servers used in the README.
_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5500,http://127.0.0.1:5500,"
        "http://localhost:8080,http://127.0.0.1:8080,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "https://coderblockch.github.io",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


class TriageRequest(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    symptoms: str = Field(default="", max_length=2000)
    oxygen_level: int = Field(ge=0, le=100)


BedStatus = Literal["Available", "Occupied", "Pending_Discharge", "Cleaning"]
BED_STATUS_VALUES = ("Available", "Occupied", "Pending_Discharge", "Cleaning")


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class BedUpdate(BaseModel):
    status: Optional[BedStatus] = None
    patient: Optional[str] = Field(default=None, max_length=120)


# Strings are stripped *before* length validation, so "   " is rejected (422).
BedNumber = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class BedCreate(BaseModel):
    num: BedNumber
    status: BedStatus = "Available"


class BedAssign(BaseModel):
    patient_id: int = Field(gt=0)


class PatientCreate(BaseModel):
    full_name: PersonName
    age: int = Field(ge=0, le=130)


class TriageCreate(BaseModel):
    """Run the CDSS and store the result. Pass ``patient_id`` for an existing
    patient, or ``patient_name`` to register a new one in the same transaction."""

    patient_id: Optional[int] = Field(default=None, gt=0)
    patient_name: Optional[PersonName] = None
    age: int = Field(ge=0, le=130)
    symptoms: str = Field(default="", max_length=2000)
    oxygen_level: int = Field(ge=0, le=100)


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    age: int
    created_at: datetime


class TriageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    age: int
    oxygen_level: int
    symptoms: str
    priority: int
    recommendation: str
    urgency: str
    created_by_id: Optional[int]
    created_at: datetime


class PatientDetail(PatientRead):
    current_bed: Optional[str] = None
    triage_history: list[TriageRead] = []


def evaluate_triage(age: int, oxygen_level: int, symptoms: str) -> tuple[int, str, str]:
    """Rule-based clinical decision support: map vitals/symptoms to a priority."""
    symptoms = symptoms.lower()

    # Rule 1: Critical oxygen or chest pain
    if oxygen_level < 90 or "chest pain" in symptoms:
        return 1, "ICU (Immediate)", "CRITICAL"
    # Rule 2: Elderly with respiratory issues
    if age > 70 and "cough" in symptoms:
        return 2, "Respiratory Unit", "High"
    # Rule 3: Mild symptoms
    if "fever" in symptoms or "headache" in symptoms:
        return 3, "Urgent Care / Clinic", "Moderate"
    # Rule 4: Otherwise stable
    return 4, "Outpatient Clinic", "Low"


Limit = Query(50, ge=1, le=200, description="Page size")
Offset = Query(0, ge=0, description="Rows to skip")


def _react_build_available() -> bool:
    return (FRONTEND_DIST / "index.html").is_file()


@app.get("/", include_in_schema=False)
def frontend():
    """Send visitors to the React app when it has been built; otherwise serve
    the original single-file dashboard, so one service hosts UI and API."""
    if _react_build_available():
        return RedirectResponse("/app/", status_code=307)
    return FileResponse(FRONTEND_FILE)


@app.get("/classic", include_in_schema=False)
def classic_dashboard():
    """The original vanilla-JS dashboard (index.html), kept for reference."""
    return FileResponse(FRONTEND_FILE)


@app.get("/app", include_in_schema=False)
@app.get("/app/{path:path}", include_in_schema=False)
def react_app(path: str = ""):
    """Serve the React build: real files (JS/CSS/images) as-is, and index.html
    for every other path so React Router can handle client-side routes."""
    if not _react_build_available():
        raise HTTPException(
            status_code=404,
            detail="React frontend not built. Run: cd frontend && npm ci && npm run build",
        )
    root = FRONTEND_DIST.resolve()
    candidate = (root / path).resolve()
    if path and candidate.is_file() and candidate.is_relative_to(root):
        return FileResponse(candidate)
    if path.startswith("assets/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(root / "index.html")


@app.get("/health")
def health():
    """Liveness probe used by Render's health check."""
    return {"status": "ok", "message": "Sachealth OS is Alive!"}


@app.post("/auth/login")
def login(data: LoginRequest):
    user = authenticate(data.email, data.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@app.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@app.get("/beds")
def get_beds(status: Optional[BedStatus] = None):
    """List beds ordered by number, optionally filtered by status."""
    try:
        with Session(engine) as session:
            query = select(Bed).order_by(Bed.num)
            if status is not None:
                query = query.where(Bed.status == status)
            return session.exec(query).all()
    except SQLAlchemyError:
        logger.exception("Failed to fetch beds from the database")
        raise HTTPException(status_code=500, detail="Could not retrieve bed data")


@app.patch("/beds/{bed_id}")
def update_bed(bed_id: int, data: BedUpdate, user: User = Depends(get_current_user)):
    """Update a bed's status and/or patient. Requires a logged-in staff user."""
    changes = data.model_dump(exclude_unset=True)
    with Session(engine) as session:
        bed = session.get(Bed, bed_id)
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found")
        if "status" in changes and changes["status"] is not None:
            bed.status = changes["status"]
        if "patient" in changes:
            patient = (changes["patient"] or "").strip() or None
            if patient != bed.patient:
                # A different free-text name no longer refers to the registered patient.
                bed.patient_id = None
            bed.patient = patient
        if bed.status in ("Available", "Cleaning"):
            bed.patient = None
            bed.patient_id = None
        session.add(bed)
        session.commit()
        session.refresh(bed)
        logger.info("Bed %s updated by user %s", bed.num, user.id)
        return bed


@app.post("/triage/analyze")
async def analyze_patient(data: TriageRequest):
    """Stateless CDSS evaluation (public). Use POST /triage to store the result."""
    priority, recommendation, urgency = evaluate_triage(
        data.age, data.oxygen_level, data.symptoms
    )
    color = {1: "bg-red-500", 2: "bg-yellow-500"}.get(priority, "bg-green-500")

    return {
        "patient": data.patient_name,
        "priority": priority,
        "recommendation": recommendation,
        "urgency": urgency,
        "color": color,
    }


# --- Beds: create, read one, assign/discharge (transactional) ---------------


@app.get("/beds/{bed_id}")
def get_bed(bed_id: int):
    with Session(engine) as session:
        bed = session.get(Bed, bed_id)
        if bed is None:
            raise HTTPException(status_code=404, detail="Bed not found")
        return bed


@app.post("/beds", status_code=201)
def create_bed(data: BedCreate, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        bed = Bed(num=data.num.strip(), status=data.status)
        session.add(bed)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="A bed with that number already exists")
        session.refresh(bed)
        logger.info("Bed %s created by user %s", bed.num, user.id)
        return bed


def _lock_patient(session: Session, patient_id: int) -> Patient:
    """Load a patient with a row lock (SELECT ... FOR UPDATE on PostgreSQL).

    Lock order is always patient → bed, in both assign_bed and delete_patient,
    so a patient cannot be deleted while being assigned (and vice versa)."""
    patient = session.exec(
        select(Patient).where(Patient.id == patient_id).with_for_update()
    ).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


def _get_bed_or_404(session: Session, bed_id: int) -> Bed:
    bed = session.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found")
    return bed


@app.post("/beds/{bed_id}/assign")
def assign_bed(bed_id: int, data: BedAssign, user: User = Depends(get_current_user)):
    """Put a registered patient in an Available bed, atomically.

    The bed is claimed with a conditional ``UPDATE ... WHERE status = 'Available'``,
    so of two concurrent requests for the same bed exactly one succeeds (on
    SQLite and PostgreSQL alike); the unique ``bed.patient_id`` constraint stops
    one patient from taking two beds. On failure nothing is written (409)."""
    with Session(engine) as session:
        bed = _get_bed_or_404(session, bed_id)
        patient = _lock_patient(session, data.patient_id)
        current = session.exec(select(Bed).where(Bed.patient_id == patient.id)).first()
        if current is not None:
            raise HTTPException(
                status_code=409, detail=f"Patient already assigned to bed {current.num}"
            )
        try:
            claimed = session.execute(
                update(Bed)
                .where(Bed.id == bed_id, Bed.status == "Available")
                .values(
                    status="Occupied",
                    patient_id=patient.id,
                    patient=patient.full_name,
                    updated_at=utcnow(),
                )
            ).rowcount
            if claimed != 1:
                session.rollback()
                session.refresh(bed)
                raise HTTPException(
                    status_code=409, detail=f"Bed is {bed.status}, not Available"
                )
            session.commit()
        except IntegrityError:
            # Unique constraint on bed.patient_id caught a concurrent assignment.
            session.rollback()
            raise HTTPException(status_code=409, detail="Patient already assigned to a bed")
        session.refresh(bed)
        logger.info("Bed %s assigned to patient %s by user %s", bed.num, patient.id, user.id)
        return bed


@app.post("/beds/{bed_id}/discharge")
def discharge_bed(bed_id: int, user: User = Depends(get_current_user)):
    """Release an occupied bed: clears the patient and marks it for Cleaning."""
    with Session(engine) as session:
        bed = _get_bed_or_404(session, bed_id)
        released = session.execute(
            update(Bed)
            .where(Bed.id == bed_id, col(Bed.status).in_(("Occupied", "Pending_Discharge")))
            .values(status="Cleaning", patient=None, patient_id=None, updated_at=utcnow())
        ).rowcount
        if released != 1:
            session.rollback()
            session.refresh(bed)
            raise HTTPException(status_code=409, detail=f"Bed is {bed.status}, nobody to discharge")
        session.commit()
        session.refresh(bed)
        logger.info("Bed %s discharged by user %s", bed.num, user.id)
        return bed


# --- Patients (staff only: contains patient data) ---------------------------


@app.post("/patients", status_code=201, response_model=PatientRead)
def create_patient(data: PatientCreate, user: User = Depends(get_current_user)):
    with Session(engine) as session:
        patient = Patient(full_name=data.full_name.strip(), age=data.age)
        session.add(patient)
        session.commit()
        session.refresh(patient)
        return patient


@app.get("/patients", response_model=Page[PatientRead])
def list_patients(
    q: Optional[str] = Query(None, max_length=120, description="Search by name"),
    limit: int = Limit,
    offset: int = Offset,
    user: User = Depends(get_current_user),
):
    with Session(engine) as session:
        filters = []
        if q:
            filters.append(func.lower(Patient.full_name).contains(q.strip().lower()))
        total = session.exec(select(func.count()).select_from(Patient).where(*filters)).one()
        items = session.exec(
            select(Patient)
            .where(*filters)
            .order_by(col(Patient.created_at).desc(), col(Patient.id).desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return Page[PatientRead](items=items, total=total, limit=limit, offset=offset)


@app.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient(patient_id: int, user: User = Depends(get_current_user)):
    """A patient with their current bed and full triage history (newest first)."""
    with Session(engine) as session:
        patient = session.get(Patient, patient_id)
        if patient is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        bed = session.exec(select(Bed).where(Bed.patient_id == patient_id)).first()
        history = session.exec(
            select(TriageRecord)
            .where(TriageRecord.patient_id == patient_id)
            .order_by(col(TriageRecord.created_at).desc(), col(TriageRecord.id).desc())
        ).all()
        return PatientDetail(
            **PatientRead.model_validate(patient, from_attributes=True).model_dump(),
            current_bed=bed.num if bed else None,
            triage_history=[TriageRead.model_validate(r, from_attributes=True) for r in history],
        )


@app.delete("/patients/{patient_id}", status_code=204)
def delete_patient(patient_id: int, user: User = Depends(get_current_user)):
    """Delete a patient. Their triage records are removed (ON DELETE CASCADE)
    and any bed they occupied is released for Cleaning, in one transaction."""
    with Session(engine) as session:
        patient = _lock_patient(session, patient_id)  # same lock order as assign_bed
        for bed in session.exec(
            select(Bed).where(Bed.patient_id == patient_id).with_for_update()
        ).all():
            bed.status, bed.patient, bed.patient_id = "Cleaning", None, None
            session.add(bed)
        for record in session.exec(
            select(TriageRecord).where(TriageRecord.patient_id == patient_id)
        ).all():
            session.delete(record)
        session.delete(patient)
        session.commit()


# --- Triage history ----------------------------------------------------------


@app.post("/triage", status_code=201, response_model=TriageRead)
def create_triage(data: TriageCreate, user: User = Depends(get_current_user)):
    """Evaluate and store a triage. Registering a new patient and saving the
    record happen in a single transaction: either both are saved or neither."""
    if (data.patient_id is None) == (data.patient_name is None):
        raise HTTPException(
            status_code=422, detail="Provide exactly one of patient_id or patient_name"
        )
    priority, recommendation, urgency = evaluate_triage(
        data.age, data.oxygen_level, data.symptoms
    )
    with Session(engine) as session:
        if data.patient_id is not None:
            patient = session.get(Patient, data.patient_id)
            if patient is None:
                raise HTTPException(status_code=404, detail="Patient not found")
            patient.age = data.age
        else:
            patient = Patient(full_name=data.patient_name.strip(), age=data.age)
        session.add(patient)
        session.flush()  # assigns patient.id without committing yet
        record = TriageRecord(
            patient_id=patient.id,
            age=data.age,
            oxygen_level=data.oxygen_level,
            symptoms=data.symptoms,
            priority=priority,
            recommendation=recommendation,
            urgency=urgency,
            created_by_id=user.id,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return record


@app.get("/triage", response_model=Page[TriageRead])
def list_triage(
    priority: Optional[int] = Query(None, ge=1, le=4),
    patient_id: Optional[int] = Query(None, gt=0),
    since: Optional[datetime] = Query(None, description="Only records at or after this time"),
    limit: int = Limit,
    offset: int = Offset,
    user: User = Depends(get_current_user),
):
    """Triage history, newest first, with filters and pagination."""
    filters = []
    if priority is not None:
        filters.append(TriageRecord.priority == priority)
    if patient_id is not None:
        filters.append(TriageRecord.patient_id == patient_id)
    if since is not None:
        # Compare in UTC on every backend: aware values are converted, naive
        # values are interpreted as UTC (SQLite stores timestamps without offset).
        since = (
            since.replace(tzinfo=timezone.utc)
            if since.tzinfo is None
            else since.astimezone(timezone.utc)
        )
        filters.append(TriageRecord.created_at >= since)
    with Session(engine) as session:
        total = session.exec(select(func.count()).select_from(TriageRecord).where(*filters)).one()
        items = session.exec(
            select(TriageRecord)
            .where(*filters)
            .order_by(col(TriageRecord.created_at).desc(), col(TriageRecord.id).desc())
            .offset(offset)
            .limit(limit)
        ).all()
        return Page[TriageRead](items=items, total=total, limit=limit, offset=offset)


@app.get("/stats")
def stats():
    """Aggregate counts for the dashboard: beds by status and triage by priority."""
    with Session(engine) as session:
        beds = dict(session.exec(select(Bed.status, func.count()).group_by(Bed.status)).all())
        triage = dict(
            session.exec(
                select(TriageRecord.priority, func.count()).group_by(TriageRecord.priority)
            ).all()
        )
    return {
        "beds_by_status": {status: beds.get(status, 0) for status in BED_STATUS_VALUES},
        "triage_by_priority": {str(p): triage.get(p, 0) for p in range(1, 5)},
    }
