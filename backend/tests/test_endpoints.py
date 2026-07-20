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


def test_cors_headers_present(client):
    response = client.get("/", headers={"Origin": "http://example.com"})
    # With allow_credentials enabled the middleware echoes the request origin.
    assert response.headers["access-control-allow-origin"] == "http://example.com"
    assert response.headers["access-control-allow-credentials"] == "true"
