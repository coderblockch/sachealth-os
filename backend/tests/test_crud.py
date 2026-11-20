"""Tests for patients, triage history, bed assignment and the data constraints."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

import main
from models import Bed, Patient, TriageRecord

DEMO = {"email": main.DEMO_USER_EMAIL, "password": main.DEMO_USER_PASSWORD}


@pytest.fixture
def auth(client):
    token = client.post("/auth/login", json=DEMO).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _bed_id(client, num):
    return next(b["id"] for b in client.get("/beds").json() if b["num"] == num)


def _new_patient(client, auth, name="Ana Test", age=40):
    response = client.post("/patients", json={"full_name": name, "age": age}, headers=auth)
    assert response.status_code == 201
    return response.json()


# --- patients ----------------------------------------------------------------


def test_patient_endpoints_require_auth(client):
    assert client.get("/patients").status_code == 401
    assert client.post("/patients", json={"full_name": "X", "age": 1}).status_code == 401
    assert client.get("/triage").status_code == 401
    assert client.post("/triage", json={"patient_name": "X", "age": 1, "oxygen_level": 99}).status_code == 401


def test_create_and_get_patient(client, auth):
    created = _new_patient(client, auth, "  Ana Test  ", 40)
    assert created["full_name"] == "Ana Test"
    detail = client.get(f"/patients/{created['id']}", headers=auth).json()
    assert detail["triage_history"] == [] and detail["current_bed"] is None


def test_get_missing_patient_returns_404(client, auth):
    assert client.get("/patients/9999", headers=auth).status_code == 404


def test_list_patients_search_and_pagination(client, auth):
    for i in range(5):
        _new_patient(client, auth, f"Patient {i}", 30 + i)
    _new_patient(client, auth, "Zoe Unique", 50)

    page = client.get("/patients?limit=2&offset=0", headers=auth).json()
    assert page["total"] == 6 and page["limit"] == 2 and len(page["items"]) == 2

    last = client.get("/patients?limit=4&offset=4", headers=auth).json()
    assert len(last["items"]) == 2

    found = client.get("/patients?q=zoe", headers=auth).json()
    assert found["total"] == 1 and found["items"][0]["full_name"] == "Zoe Unique"


def test_pagination_limits_are_validated(client, auth):
    assert client.get("/patients?limit=0", headers=auth).status_code == 422
    assert client.get("/patients?limit=500", headers=auth).status_code == 422
    assert client.get("/triage?offset=-1", headers=auth).status_code == 422


# --- triage history ----------------------------------------------------------


def test_create_triage_registers_new_patient(client, auth):
    response = client.post(
        "/triage",
        json={"patient_name": "Leo Test", "age": 80, "oxygen_level": 95, "symptoms": "Cough"},
        headers=auth,
    )
    assert response.status_code == 201
    record = response.json()
    assert record["priority"] == 2 and record["recommendation"] == "Respiratory Unit"
    assert record["created_by_id"] is not None

    detail = client.get(f"/patients/{record['patient_id']}", headers=auth).json()
    assert detail["full_name"] == "Leo Test"
    assert [r["id"] for r in detail["triage_history"]] == [record["id"]]


def test_create_triage_for_existing_patient_builds_history(client, auth):
    patient = _new_patient(client, auth)
    for oxygen in (98, 85):
        assert client.post(
            "/triage", json={"patient_id": patient["id"], "age": 41, "oxygen_level": oxygen},
            headers=auth,
        ).status_code == 201
    history = client.get(f"/patients/{patient['id']}", headers=auth).json()["triage_history"]
    assert [r["priority"] for r in history] == [1, 4]  # newest first
    assert client.get(f"/patients/{patient['id']}", headers=auth).json()["age"] == 41


def test_create_triage_requires_exactly_one_patient_reference(client, auth):
    both = {"patient_id": 1, "patient_name": "X", "age": 1, "oxygen_level": 99}
    neither = {"age": 1, "oxygen_level": 99}
    assert client.post("/triage", json=both, headers=auth).status_code == 422
    assert client.post("/triage", json=neither, headers=auth).status_code == 422
    missing = {"patient_id": 9999, "age": 1, "oxygen_level": 99}
    assert client.post("/triage", json=missing, headers=auth).status_code == 404


def test_list_triage_filters_by_priority_and_patient(client, auth):
    a = client.post("/triage", json={"patient_name": "A", "age": 30, "oxygen_level": 80}, headers=auth).json()
    client.post("/triage", json={"patient_name": "B", "age": 30, "oxygen_level": 99}, headers=auth)
    client.post("/triage", json={"patient_name": "C", "age": 30, "oxygen_level": 99}, headers=auth)

    critical = client.get("/triage?priority=1", headers=auth).json()
    assert critical["total"] == 1 and critical["items"][0]["id"] == a["id"]
    low = client.get("/triage?priority=4&limit=1", headers=auth).json()
    assert low["total"] == 2 and len(low["items"]) == 1
    mine = client.get(f"/triage?patient_id={a['patient_id']}", headers=auth).json()
    assert mine["total"] == 1
    assert client.get("/triage?priority=9", headers=auth).status_code == 422


def test_failed_triage_does_not_leave_orphan_patient(client, auth, patched_engine, monkeypatch):
    """Patient + record are one transaction: if saving the record fails, the
    new patient is rolled back too."""

    def broken(*_args, **_kwargs):
        return 9, "Bogus", "Low"  # priority 9 violates ck_triage_priority_range

    monkeypatch.setattr(main, "evaluate_triage", broken)
    with pytest.raises(IntegrityError):
        client.post("/triage", json={"patient_name": "Ghost", "age": 30, "oxygen_level": 99}, headers=auth)
    with Session(patched_engine) as session:
        assert session.exec(select(Patient).where(Patient.full_name == "Ghost")).first() is None


# --- beds --------------------------------------------------------------------


def test_filter_beds_by_status(client):
    available = client.get("/beds?status=Available").json()
    assert [b["num"] for b in available] == ["103"]
    assert client.get("/beds?status=Broken").status_code == 422


def test_get_single_bed(client):
    bed_id = _bed_id(client, "103")
    assert client.get(f"/beds/{bed_id}").json()["num"] == "103"
    assert client.get("/beds/9999").status_code == 404


def test_create_bed_and_duplicate_number_conflict(client, auth):
    response = client.post("/beds", json={"num": "201"}, headers=auth)
    assert response.status_code == 201 and response.json()["status"] == "Available"
    assert client.post("/beds", json={"num": "201"}, headers=auth).status_code == 409
    assert client.post("/beds", json={"num": "202"}).status_code == 401


def test_assign_and_discharge_bed(client, auth):
    patient = _new_patient(client, auth)
    bed_id = _bed_id(client, "103")

    assigned = client.post(f"/beds/{bed_id}/assign", json={"patient_id": patient["id"]}, headers=auth)
    assert assigned.status_code == 200
    body = assigned.json()
    assert body["status"] == "Occupied" and body["patient_id"] == patient["id"]
    assert body["patient"] == "Ana Test"
    assert client.get(f"/patients/{patient['id']}", headers=auth).json()["current_bed"] == "103"

    discharged = client.post(f"/beds/{bed_id}/discharge", headers=auth).json()
    assert discharged["status"] == "Cleaning" and discharged["patient_id"] is None
    assert client.post(f"/beds/{bed_id}/discharge", headers=auth).status_code == 409


def test_assign_rejects_unavailable_bed_and_double_booking(client, auth):
    patient = _new_patient(client, auth)
    occupied = _bed_id(client, "101")
    assert client.post(f"/beds/{occupied}/assign", json={"patient_id": patient["id"]}, headers=auth).status_code == 409

    free = _bed_id(client, "103")
    assert client.post(f"/beds/{free}/assign", json={"patient_id": patient["id"]}, headers=auth).status_code == 200
    other = client.post("/beds", json={"num": "301"}, headers=auth).json()["id"]
    second = client.post(f"/beds/{other}/assign", json={"patient_id": patient["id"]}, headers=auth)
    assert second.status_code == 409 and "103" in second.json()["detail"]
    assert client.post(f"/beds/{free}/assign", json={"patient_id": 9999}, headers=auth).status_code == 409
    assert client.post(f"/beds/{other}/assign", json={"patient_id": 9999}, headers=auth).status_code == 404


def test_patching_patient_name_unlinks_registered_patient(client, auth):
    patient = _new_patient(client, auth)
    bed_id = _bed_id(client, "103")
    client.post(f"/beds/{bed_id}/assign", json={"patient_id": patient["id"]}, headers=auth)
    bed = client.patch(f"/beds/{bed_id}", json={"patient": "Walk-in"}, headers=auth).json()
    assert bed["patient"] == "Walk-in" and bed["patient_id"] is None


def test_delete_patient_cascades_history_and_frees_bed(client, auth, patched_engine):
    record = client.post("/triage", json={"patient_name": "Del", "age": 30, "oxygen_level": 99}, headers=auth).json()
    pid = record["patient_id"]
    bed_id = _bed_id(client, "103")
    client.post(f"/beds/{bed_id}/assign", json={"patient_id": pid}, headers=auth)

    assert client.delete(f"/patients/{pid}", headers=auth).status_code == 204
    assert client.get(f"/patients/{pid}", headers=auth).status_code == 404
    bed = client.get(f"/beds/{bed_id}").json()
    assert bed["status"] == "Cleaning" and bed["patient_id"] is None
    with Session(patched_engine) as session:
        assert session.exec(select(TriageRecord).where(TriageRecord.patient_id == pid)).all() == []
    assert client.delete(f"/patients/{pid}", headers=auth).status_code == 404


def test_stats_counts_beds_and_triage(client, auth):
    client.post("/triage", json={"patient_name": "S", "age": 30, "oxygen_level": 80}, headers=auth)
    stats = client.get("/stats").json()
    assert stats["beds_by_status"] == {
        "Available": 1, "Occupied": 1, "Pending_Discharge": 2, "Cleaning": 1,
    }
    assert stats["triage_by_priority"] == {"1": 1, "2": 0, "3": 0, "4": 0}


# --- database constraints (enforced by the DB, not just the API) --------------


def test_db_rejects_invalid_bed_status(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(Bed(num="900", status="Broken"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_db_rejects_duplicate_bed_number(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add_all([Bed(num="901", status="Available"), Bed(num="901", status="Available")])
        with pytest.raises(IntegrityError):
            session.commit()


def test_db_rejects_triage_for_unknown_patient(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(TriageRecord(patient_id=12345, age=30, oxygen_level=99, priority=4,
                                 recommendation="x", urgency="Low"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_db_rejects_out_of_range_patient_age(in_memory_engine):
    with Session(in_memory_engine) as session:
        session.add(Patient(full_name="Old", age=200))
        with pytest.raises(IntegrityError):
            session.commit()
