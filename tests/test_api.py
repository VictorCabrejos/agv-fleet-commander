from fastapi.testclient import TestClient

from main import app


def test_health_reports_unstarted_services_without_failing():
    response = TestClient(app).get("/api/system/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["services"]["fleet_service"] == "unavailable"
