"""
Tests for ravn_app/api endpoints.
"""

from fastapi.testclient import TestClient
from ravn_app.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_get_settings():
    response = client.get("/api/v1/settings/")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_get_queue():
    response = client.get("/api/v1/queue/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
