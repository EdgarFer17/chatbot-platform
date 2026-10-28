from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Chatbot Platform",
        "version": "1.0.0-rc.1",
        "environment": "development",
    }
