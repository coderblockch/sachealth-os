"""Unit tests for the root and bed-management endpoints."""


def test_root_returns_liveness_message(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Sachealth OS is Alive!"}


def test_get_beds_returns_seeded_beds(client):
    response = client.get("/beds")
    assert response.status_code == 200
    beds = response.json()
    # Startup seeds five beds into the (isolated) in-memory database.
    assert len(beds) == 5
    bed_numbers = {bed["num"] for bed in beds}
    assert bed_numbers == {"101", "102", "103", "104", "105"}


def test_seeded_beds_have_expected_shape(client):
    beds = client.get("/beds").json()
    for bed in beds:
        assert set(bed.keys()) == {"id", "num", "status", "patient"}
        assert isinstance(bed["id"], int)

    by_num = {bed["num"]: bed for bed in beds}
    assert by_num["101"]["status"] == "Occupied"
    assert by_num["101"]["patient"] == "John Doe"
    assert by_num["103"]["status"] == "Available"
    assert by_num["103"]["patient"] is None


def test_startup_does_not_reseed_when_beds_exist(patched_engine):
    from fastapi.testclient import TestClient

    import main

    # Two startup cycles against the same engine must not duplicate seed data.
    with TestClient(main.app) as client:
        first = client.get("/beds").json()
    with TestClient(main.app) as client:
        second = client.get("/beds").json()

    assert len(first) == 5
    assert len(second) == 5


def test_cors_allows_local_frontend(client):
    response = client.get("/", headers={"Origin": "http://localhost:5500"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5500"
    assert "access-control-allow-credentials" not in response.headers


def test_cors_rejects_unknown_origin(client):
    response = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_triage_rejects_out_of_range_input(client):
    payload = {"patient_name": "A", "age": 200, "symptoms": "", "oxygen_level": 95}
    assert client.post("/triage/analyze", json=payload).status_code == 422
    payload = {"patient_name": "", "age": 30, "symptoms": "", "oxygen_level": 95}
    assert client.post("/triage/analyze", json=payload).status_code == 422
