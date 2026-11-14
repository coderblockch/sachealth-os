import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path
from typing import Literal, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from auth import authenticate, create_access_token, get_current_user, hash_password
from database import create_db_and_tables, engine
from models import Bed, User

logger = logging.getLogger("sachealth")

# The static dashboard lives at the repository root (../index.html).
FRONTEND_FILE = Path(__file__).resolve().parent.parent / "index.html"

# Public demo account (fake data only). Override with env vars in production.
DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "demo@sachealth.dev")
DEMO_USER_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "sachealth-demo")


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
        if session.exec(select(User).where(User.email == email)).first():
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_beds()
    seed_demo_user()
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
        "https://coderblockch.github.io",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


class TriageRequest(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    symptoms: str = Field(default="", max_length=2000)
    oxygen_level: int = Field(ge=0, le=100)


BedStatus = Literal["Available", "Occupied", "Pending_Discharge", "Cleaning"]


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class BedUpdate(BaseModel):
    status: Optional[BedStatus] = None
    patient: Optional[str] = Field(default=None, max_length=120)


@app.get("/", include_in_schema=False)
def frontend():
    """Serve the dashboard so one service hosts both the UI and the API."""
    return FileResponse(FRONTEND_FILE)


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
def get_beds():
    try:
        with Session(engine) as session:
            return session.exec(select(Bed)).all()
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
            patient = (changes["patient"] or "").strip()
            bed.patient = patient or None
        if bed.status in ("Available", "Cleaning"):
            bed.patient = None
        session.add(bed)
        session.commit()
        session.refresh(bed)
        logger.info("Bed %s updated by user %s", bed.num, user.id)
        return bed


@app.post("/triage/analyze")
async def analyze_patient(data: TriageRequest):
    """Rule-based clinical decision support: map vitals/symptoms to a priority."""
    symptoms = data.symptoms.lower()

    # Rule 1: Critical oxygen or chest pain
    if data.oxygen_level < 90 or "chest pain" in symptoms:
        priority, recommendation, urgency = 1, "ICU (Immediate)", "CRITICAL"
    # Rule 2: Elderly with respiratory issues
    elif data.age > 70 and "cough" in symptoms:
        priority, recommendation, urgency = 2, "Respiratory Unit", "High"
    # Rule 3: Mild symptoms
    elif "fever" in symptoms or "headache" in symptoms:
        priority, recommendation, urgency = 3, "Urgent Care / Clinic", "Moderate"
    # Rule 4: Otherwise stable
    else:
        priority, recommendation, urgency = 4, "Outpatient Clinic", "Low"

    color = {1: "bg-red-500", 2: "bg-yellow-500"}.get(priority, "bg-green-500")

    return {
        "patient": data.patient_name,
        "priority": priority,
        "recommendation": recommendation,
        "urgency": urgency,
        "color": color,
    }
