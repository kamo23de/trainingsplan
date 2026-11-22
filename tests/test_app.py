from fastapi.testclient import TestClient

from trainingsplan.web.app import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_without_data():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "Noch keine Daten importiert" in response.text


def test_summary_empty():
    with TestClient(app) as client:
        data = client.get("/api/summary").json()
    assert data["activities"] == 0
    assert data["distance_km"] == 0
