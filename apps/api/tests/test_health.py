from fastapi.testclient import TestClient

from qa_test_manager.main import app


def test_health_returns_service_status() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "qa-test-manager-api"}
