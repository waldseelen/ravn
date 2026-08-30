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


def test_api_v1_health_and_tools():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "tools" in data
    assert "overall_status" in data["tools"]


def test_get_history_stats():
    response = client.get("/api/v1/history/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_downloads" in data
    assert "total_conversions" in data
    assert "total_operations" in data


def test_get_history_recent():
    response = client.get("/api/v1/history/recent")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_operations_history():
    response = client.get("/api/v1/history/operations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_batch_download_endpoint():
    payload = {
        "urls": ["https://example.com/video1.mp4", "https://example.com/video2.mp4"],
        "output_dir": ".",
        "format": "mp4",
        "quality": "best"
    }
    response = client.post("/api/v1/downloads/batch/start", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["enqueued"] == 2
    assert len(data["task_ids"]) == 2


def test_torrent_download_endpoint():
    payload = {
        "source": "magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567",
        "output_dir": ".",
        "mode": "FULL"
    }
    response = client.post("/api/v1/downloads/torrent/start", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["mode"] == "full"


def test_studio_convert_endpoint():
    payload = {
        "input_file": "test_video.mp4",
        "video_codec": "h264",
        "audio_codec": "aac",
        "video_quality": "HIGH"
    }
    response = client.post("/api/v1/convert/start", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"


def test_studio_subtitle_download_endpoint():
    payload = {
        "url": "https://example.com/video",
        "languages": ["tr", "en"],
        "auto_generated": True
    }
    response = client.post("/api/v1/subtitle/download", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data


def test_studio_filters_endpoint():
    payload = {
        "input_file": "sample.mp4",
        "brightness": 0.1,
        "contrast": 1.2,
        "rotate": 90
    }
    response = client.post("/api/v1/filters/apply", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data


def test_studio_mixer_endpoint():
    payload = {
        "mode": "audio",
        "operation": "mix",
        "input_files": ["track1.mp3", "track2.mp3"]
    }
    response = client.post("/api/v1/mixer/run", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data


def test_studio_utilities_endpoint():
    payload = {
        "category": "quick",
        "operation": "remux",
        "input_file": "source.mkv"
    }
    response = client.post("/api/v1/utilities/run", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert "task_id" in data




