"""Unit tests for the rule-based triage engine (POST /triage/analyze)."""


def _analyze(client, **overrides):
    payload = {
        "patient_name": "Test Patient",
        "age": 40,
        "symptoms": "general malaise",
        "oxygen_level": 98,
    }
    payload.update(overrides)
    response = client.post("/triage/analyze", json=payload)
    assert response.status_code == 200
    return response.json()


def test_critical_low_oxygen(client):
    result = _analyze(client, oxygen_level=85)
    assert result["priority"] == 1
    assert result["recommendation"] == "ICU (Immediate)"
    assert result["urgency"] == "CRITICAL"
    assert result["color"] == "bg-red-500"


def test_oxygen_boundary_90_is_not_critical(client):
    # Rule uses a strict "< 90" comparison, so exactly 90 is not critical.
    result = _analyze(client, oxygen_level=90)
    assert result["priority"] != 1


def test_critical_chest_pain_case_insensitive(client):
    result = _analyze(client, symptoms="Severe CHEST PAIN", oxygen_level=99)
    assert result["priority"] == 1
    assert result["urgency"] == "CRITICAL"


def test_chest_pain_takes_precedence_over_other_rules(client):
    # Elderly + cough would be rule 2, but chest pain forces critical.
    result = _analyze(client, age=80, symptoms="cough and chest pain", oxygen_level=99)
    assert result["priority"] == 1


def test_elderly_with_cough_is_urgent(client):
    result = _analyze(client, age=75, symptoms="persistent cough", oxygen_level=97)
    assert result["priority"] == 2
    assert result["recommendation"] == "Respiratory Unit"
    assert result["urgency"] == "High"
    assert result["color"] == "bg-yellow-500"


def test_age_boundary_70_is_not_urgent(client):
    # Rule uses a strict "> 70" comparison.
    result = _analyze(client, age=70, symptoms="cough", oxygen_level=97)
    assert result["priority"] != 2


def test_young_with_cough_is_not_urgent(client):
    result = _analyze(client, age=30, symptoms="cough", oxygen_level=97)
    assert result["priority"] != 2


def test_mild_fever_is_standard(client):
    result = _analyze(client, symptoms="mild fever", oxygen_level=98)
    assert result["priority"] == 3
    assert result["recommendation"] == "Urgent Care / Clinic"
    assert result["urgency"] == "Moderate"
    assert result["color"] == "bg-green-500"


def test_headache_is_standard(client):
    result = _analyze(client, symptoms="bad HEADACHE")
    assert result["priority"] == 3


def test_unmatched_symptoms_are_outpatient(client):
    result = _analyze(client, symptoms="sprained ankle", oxygen_level=99)
    assert result["priority"] == 4
    assert result["recommendation"] == "Outpatient Clinic"
    assert result["urgency"] == "Low"
    assert result["color"] == "bg-green-500"


def test_response_echoes_patient_name(client):
    result = _analyze(client, patient_name="Alice Example")
    assert result["patient"] == "Alice Example"


def test_missing_field_is_rejected(client):
    response = client.post("/triage/analyze", json={"patient_name": "No Vitals"})
    assert response.status_code == 422


def test_non_integer_oxygen_is_rejected(client):
    response = client.post(
        "/triage/analyze",
        json={
            "patient_name": "Bad Types",
            "age": 40,
            "symptoms": "fever",
            "oxygen_level": "not-a-number",
        },
    )
    assert response.status_code == 422
