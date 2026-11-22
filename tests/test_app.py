from fastapi.testclient import TestClient

from trainingsplan.web.app import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_without_data():
    with TestClient(app) as client:
        response = client.get("/rueckblick")
    assert response.status_code == 200
    assert "Noch keine Daten importiert" in response.text


def test_summary_empty():
    with TestClient(app) as client:
        data = client.get("/api/summary").json()
    assert data["activities"] == 0
    assert data["distance_km"] == 0


def test_static_assets_have_cache_busting_version():
    with TestClient(app) as client:
        html = client.get("/rueckblick").text
        assert "/static/dashboard.js?v=" in html
        assert client.get("/static/info.js").status_code == 200


def test_pages_and_navigation():
    with TestClient(app) as client:
        start = client.get("/").text
        assert 'href="/rueckblick"' in start and 'href="/planung"' in start
        assert client.get("/planung").status_code == 200
