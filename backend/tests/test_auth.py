"""Tests for login (JWT) and the protected bed-update endpoint."""

import auth
import main

DEMO = {"email": main.DEMO_USER_EMAIL, "password": main.DEMO_USER_PASSWORD}


def _token(client):
    response = client.post("/auth/login", json=DEMO)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    return body["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_password_hashing_roundtrip():
    hashed = auth.hash_password("s3cret!")
    assert hashed != "s3cret!"
    assert auth.verify_password("s3cret!", hashed)
    assert not auth.verify_password("wrong", hashed)


def test_demo_user_is_seeded_with_hashed_password(client, patched_engine):
    from sqlmodel import Session, select

    from models import User

    with Session(patched_engine) as session:
        users = session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].email == DEMO["email"]
    assert users[0].hashed_password != DEMO["password"]


def test_login_success_and_me(client):
    token = _token(client)
    response = client.get("/auth/me", headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["email"] == DEMO["email"]


def test_login_is_case_insensitive_on_email(client):
    response = client.post(
        "/auth/login", json={"email": DEMO["email"].upper(), "password": DEMO["password"]}
    )
    assert response.status_code == 200


def test_login_wrong_password_returns_401(client):
    response = client.post("/auth/login", json={"email": DEMO["email"], "password": "nope"})
    assert response.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_invalid_token_is_rejected(client):
    assert client.get("/auth/me", headers=_auth("not-a-jwt")).status_code == 401


def test_update_bed_requires_auth(client):
    response = client.patch("/beds/1", json={"status": "Cleaning"})
    assert response.status_code == 401


def test_update_bed_with_token(client):
    token = _token(client)
    bed_id = next(b["id"] for b in client.get("/beds").json() if b["num"] == "103")
    response = client.patch(
        f"/beds/{bed_id}",
        json={"status": "Occupied", "patient": "Test Patient"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Occupied"
    assert response.json()["patient"] == "Test Patient"


def test_freeing_a_bed_clears_patient(client):
    token = _token(client)
    bed_id = next(b["id"] for b in client.get("/beds").json() if b["num"] == "101")
    response = client.patch(f"/beds/{bed_id}", json={"status": "Cleaning"}, headers=_auth(token))
    assert response.status_code == 200
    assert response.json()["patient"] is None


def test_update_bed_rejects_invalid_status(client):
    token = _token(client)
    response = client.patch("/beds/1", json={"status": "Exploded"}, headers=_auth(token))
    assert response.status_code == 422


def test_update_missing_bed_returns_404(client):
    token = _token(client)
    response = client.patch("/beds/9999", json={"status": "Cleaning"}, headers=_auth(token))
    assert response.status_code == 404
