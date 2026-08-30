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


def test_library_endpoints(tmp_path):
    # 1. Stats
    res_stats = client.get("/api/v1/library/stats")
    assert res_stats.status_code == 200
    assert "total_items" in res_stats.json()

    # 2. Collections
    res_col = client.post("/api/v1/library/collections", json={"name": "Test Col", "description": "Desc"})
    assert res_col.status_code == 201
    col_data = res_col.json()
    col_id = col_data["id"]

    res_list_col = client.get("/api/v1/library/collections")
    assert res_list_col.status_code == 200
    assert any(c["id"] == col_id for c in res_list_col.json())

    # 3. Add Media File
    test_media = tmp_path / "sample_video.mp4"
    test_media.write_text("dummy video content")

    res_add = client.post(
        "/api/v1/library/add",
        json={"file_path": str(test_media), "title": "Sample Clip", "tags": ["test", "clip"]},
    )
    assert res_add.status_code == 201
    media_id = res_add.json()["media_id"]

    # 4. Search
    res_search = client.get("/api/v1/library/?q=Sample&tags=test")
    assert res_search.status_code == 200
    results = res_search.json()
    assert any(item["id"] == media_id for item in results)

    # 5. Add to Collection
    res_add_col = client.post(f"/api/v1/library/collections/{col_id}/items", json={"media_id": media_id})
    assert res_add_col.status_code == 200

    res_col_items = client.get(f"/api/v1/library/collections/{col_id}/items")
    assert res_col_items.status_code == 200
    assert len(res_col_items.json()) >= 1

    # 6. Export
    export_file = tmp_path / "export.json"
    res_export = client.post("/api/v1/library/export", json={"format": "json", "output_file": str(export_file)})
    assert res_export.status_code == 200
    assert export_file.exists()

    # 7. Delete Item and Collection
    res_del_media = client.delete(f"/api/v1/library/{media_id}")
    assert res_del_media.status_code == 200

    res_del_col = client.delete(f"/api/v1/library/collections/{col_id}")
    assert res_del_col.status_code == 200


def test_settings_extended_endpoints(tmp_path):
    # 1. Get settings
    res = client.get("/api/v1/settings/")
    assert res.status_code == 200
    assert "theme" in res.json()

    # 2. Patch settings
    patch_res = client.patch("/api/v1/settings/", json={"data": {"default_format": "MKV", "history_limit": 500}})
    assert patch_res.status_code == 200
    assert patch_res.json()["default_format"] == "MKV"

    # 3. Export settings
    export_file = tmp_path / "settings_export.json"
    exp_res = client.post("/api/v1/settings/export", json={"output_file": str(export_file)})
    assert exp_res.status_code == 200
    assert export_file.exists()

    # 4. Import settings
    imp_res = client.post("/api/v1/settings/import", json={"file_path": str(export_file)})
    assert imp_res.status_code == 200
    assert imp_res.json()["config"]["default_format"] == "MKV"

    # 5. Direct data import
    data_imp = client.post("/api/v1/settings/import", json={"data": {"theme": "light"}})
    assert data_imp.status_code == 200
    assert data_imp.json()["config"]["theme"] == "light"

    # 6. Check updates endpoint
    update_res = client.get("/api/v1/settings/updates/check")
    assert update_res.status_code == 200
    assert "current_version" in update_res.json()

    # 7. Reset settings
    reset_res = client.post("/api/v1/settings/reset")
    assert reset_res.status_code == 200






