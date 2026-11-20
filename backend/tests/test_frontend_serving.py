"""Serving the React build (frontend/dist) under /app, with SPA fallback."""

import pytest

import main


@pytest.fixture
def dist(tmp_path, monkeypatch):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><div id='root'>react</div>")
    (tmp_path / "assets" / "app.js").write_text("console.log('hi')")
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path)
    return tmp_path


def test_root_redirects_to_react_app_when_built(client, dist):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/app/"


def test_react_assets_are_served(client, dist):
    response = client.get("/app/assets/app.js")
    assert response.status_code == 200
    assert "console.log" in response.text


def test_client_side_routes_fall_back_to_index(client, dist):
    for path in ("/app", "/app/", "/app/patients/3", "/app/beds"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "react" in response.text


def test_missing_asset_is_404_not_index(client, dist):
    assert client.get("/app/assets/missing.js").status_code == 404


def test_path_traversal_is_blocked(client, dist):
    response = client.get("/app/..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 200
    assert "react" in response.text  # falls back to index.html, never leaks files


def test_api_routes_still_win_over_the_spa(client, dist):
    assert isinstance(client.get("/beds").json(), list)
    assert client.get("/docs").status_code == 200


def test_classic_dashboard_stays_reachable(client, dist):
    response = client.get("/classic")
    assert response.status_code == 200 and "SacHealth" in response.text


def test_app_returns_404_when_not_built(client, tmp_path, monkeypatch):
    monkeypatch.setattr(main, "FRONTEND_DIST", tmp_path / "nope")
    assert client.get("/app/").status_code == 404
    assert "SacHealth" in client.get("/").text  # falls back to the classic page
