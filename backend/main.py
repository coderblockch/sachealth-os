import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Bed

logger = logging.getLogger("sachealth")


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_beds()
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
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class TriageRequest(BaseModel):
    patient_name: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    symptoms: str = Field(default="", max_length=2000)
    oxygen_level: int = Field(ge=0, le=100)


@app.get("/")
async def root():
    return {"message": "Sachealth OS is Alive!"}


@app.get("/beds")
def get_beds():
    try:
        with Session(engine) as session:
            return session.exec(select(Bed)).all()
    except SQLAlchemyError:
        logger.exception("Failed to fetch beds from the database")
        raise HTTPException(status_code=500, detail="Could not retrieve bed data")


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
