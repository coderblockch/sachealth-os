import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from database import engine, create_db_and_tables
from models import Bed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sachealth")

app = FastAPI(title="SacHealth OS Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

@app.on_event("startup")
def on_startup():
    # Runs once when the server starts
    try:
        create_db_and_tables()
    except SQLAlchemyError:
        logger.exception("Failed to create database and tables on startup")
        raise

    # Seed initial beds only if the table is empty
    try:
        with Session(engine) as session:
            existing = session.exec(select(Bed)).first()
            if not existing:
                initial_beds = [
                    Bed(num="101", status="Occupied", patient="John Doe"),
                    Bed(num="102", status="Pending_Discharge", patient="Jane Smith"),
                    Bed(num="103", status="Available", patient=None),
                    Bed(num="104", status="Cleaning", patient=None),
                    Bed(num="105", status="Pending_Discharge", patient="Robert Wilson"),
                ]
                session.add_all(initial_beds)
                session.commit()
                logger.info("Database seeded with initial beds")
    except SQLAlchemyError:
        logger.exception("Failed to seed initial beds on startup")
        raise

# --- MODELS FOR AI TRIAGE ---
class TriageRequest(BaseModel):
    patient_name: str
    age: int
    symptoms: str
    oxygen_level: int

@app.get("/")
async def root():
    return {"message": "Sachealth OS is Alive!"}

@app.get("/beds")
def get_beds():
    # Open a session and query all beds from the database
    try:
        with Session(engine) as session:
            beds = session.exec(select(Bed)).all()
            return beds
    except SQLAlchemyError:
        logger.exception("Failed to fetch beds from the database")
        raise HTTPException(status_code=500, detail="Could not retrieve bed data")

@app.post("/triage/analyze")
async def analyze_patient(data: TriageRequest):
    logger.info("Analyzing patient: %s", data.patient_name)
    
    # --- SIMPLE AI LOGIC ENGINE ---
    priority = 3 # Default: Stable
    recommendation = "General Ward"
    urgency = "Moderate"
    
    # Rule 1: Critical Oxygen or Chest Pain
    if data.oxygen_level < 90 or "chest pain" in data.symptoms.lower():
        priority = 1
        recommendation = "ICU (Immediate)"
        urgency = "CRITICAL"
    
    # Rule 2: Elderly with respiratory issues
    elif data.age > 70 and "cough" in data.symptoms.lower():
        priority = 2
        recommendation = "Respiratory Unit"
        urgency = "High"
    
    # Rule 3: Mild symptoms
    elif "fever" in data.symptoms.lower() or "headache" in data.symptoms.lower():
        priority = 3
        recommendation = "Urgent Care / Clinic"
        urgency = "Moderate"
    
    else:
        priority = 4
        recommendation = "Outpatient Clinic"
        urgency = "Low"

    return {
        "patient": data.patient_name,
        "priority": priority,
        "recommendation": recommendation,
        "urgency": urgency,
        "color": "bg-red-500" if priority == 1 else "bg-yellow-500" if priority == 2 else "bg-green-500"
    }
