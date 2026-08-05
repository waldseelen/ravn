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


def test_patch_and_reset_settings():
    patch_res = client.patch("/api/v1/settings/", json={"data": {"auto_subtitle": True}})
    assert patch_res.status_code == 200
    assert patch_res.json().get("auto_subtitle") is True

    reset_res = client.post("/api/v1/settings/reset")
    assert reset_res.status_code == 200


def test_get_queue():
    response = client.get("/api/v1/queue/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_history():
    res_dl = client.get("/api/v1/history/downloads")
    assert res_dl.status_code == 200
    assert isinstance(res_dl.json(), list)

    res_conv = client.get("/api/v1/history/conversions")
    assert res_conv.status_code == 200
    assert isinstance(res_conv.json(), list)
