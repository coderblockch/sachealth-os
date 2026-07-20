from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Bed


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    seed_beds()
    yield


app = FastAPI(title="SacHealth OS Core", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    patient_name: str
    age: int
    symptoms: str
    oxygen_level: int


@app.get("/")
async def root():
    return {"message": "SacHealth OS is alive!"}


@app.get("/beds")
def get_beds():
    with Session(engine) as session:
        return session.exec(select(Bed)).all()


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
