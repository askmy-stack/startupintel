from fastapi.testclient import TestClient

from startupintel.api.main import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_startup_stress_demo_route():
    response = client.get("/startup/00000000-0000-0000-0000-000000000001/stress")
    assert response.status_code == 200
    body = response.json()
    assert body["startup_id"] == "00000000-0000-0000-0000-000000000001"
    assert "signal_breakdown" in body

