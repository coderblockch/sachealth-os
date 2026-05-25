from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI(title="SacHealth OS Core")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

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
async def get_beds():
    return [
        {"id": "1", "num": "101", "status": "Occupied", "patient": "John Doe"},
        {"id": "2", "num": "102", "status": "Pending_Discharge", "patient": "Jane Smith"},
        {"id": "3", "num": "103", "status": "Available", "patient": None},
        {"id": "4", "num": "104", "status": "Cleaning", "patient": None},
    ]

@app.post("/triage/analyze")
async def analyze_patient(data: TriageRequest):
    print(f"📡 ANALYZING PATIENT: {data.patient_name}")
    
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


