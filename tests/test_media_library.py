"""Tests for the Phase 7 media library persistence layer."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.core.persistence.media_library import MediaLibrary, MediaSearchFilters


class TestMediaLibrary:
    def _build_library(self, tmp_path, metadata_handler=None, **kwargs):
        metadata_handler = metadata_handler or Mock()
        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            return MediaLibrary(db_path=str(tmp_path / "library.db"), metadata_handler=metadata_handler, **kwargs)

    def test_add_get_and_search_media(self, tmp_path):
        media_file = tmp_path / "demo.mp4"
        media_file.write_bytes(b"video")
        metadata_handler = Mock()
        metadata_handler.extract_metadata.return_value = {
            "title": "Demo Video",
            "format": "mp4",
            "duration": 42.0,
            "size": media_file.stat().st_size,
            "width": 1280,
            "height": 720,
            "fps": 30.0,
            "sample_rate": 48000,
            "codec": "h264",
            "bitrate": 2000000,
        }
        library = self._build_library(tmp_path, metadata_handler=metadata_handler)
        try:
            media_id = library.add_media(str(media_file), tags=["work", "tutorial"])
            item = library.get_media(media_id)
            assert item is not None
            assert item.title == "Demo Video"
            assert item.tags == ["tutorial", "work"]

            results = library.search_media(
                query="Demo",
                filters=MediaSearchFilters(format="mp4", tags=["tutorial"], limit=10),
            )
            assert len(results) == 1
            assert results[0].id == media_id
            assert library.get_recent_searches(limit=1)[0]["result_count"] == 1
        finally:
            library.close()

    def test_collection_and_statistics_flow(self, tmp_path):
        media_file = tmp_path / "demo.mp3"
        media_file.write_bytes(b"audio")
        metadata_handler = Mock()
        metadata_handler.extract_metadata.return_value = {
            "title": "Demo Audio",
            "format": "mp3",
            "duration": 10.0,
            "size": media_file.stat().st_size,
            "sample_rate": 44100,
            "codec": "mp3",
            "bitrate": 320000,
        }
        library = self._build_library(tmp_path, metadata_handler=metadata_handler)
        try:
            media_id = library.add_media(str(media_file), tags=["music"])
            collection_id = library.create_collection("Favourites", "Pinned files")
            assert library.add_to_collection(media_id=media_id, collection_id=collection_id) is True
            items = library.get_collection_items(collection_id)
            assert len(items) == 1
            assert items[0].id == media_id

            stats = library.get_statistics()
            assert stats["total_items"] == 1
            assert stats["collections"] == 1
            assert stats["formats"]["mp3"] == 1
        finally:
            library.close()

    def test_export_and_duplicate_detection(self, tmp_path):
        metadata_handler = Mock()
        metadata_handler.extract_metadata.side_effect = [
            {"title": "One", "format": "mp4", "duration": 5.0, "size": 4, "codec": "h264"},
            {"title": "Two", "format": "mp4", "duration": 5.0, "size": 4, "codec": "h264"},
        ]
        first = tmp_path / "one.mp4"
        second = tmp_path / "two.mp4"
        first.write_bytes(b"data")
        second.write_bytes(b"data")

        library = self._build_library(tmp_path, metadata_handler=metadata_handler)
        try:
            library.add_media(str(first))
            library.add_media(str(second))
            duplicates = library.detect_duplicates()
            assert len(duplicates) == 1
            assert len(duplicates[0]) == 2

            json_export = tmp_path / "library.json"
            csv_export = tmp_path / "library.csv"
            assert library.export_library("json", str(json_export)) is True
            assert library.export_library("csv", str(csv_export)) is True
            assert json.loads(json_export.read_text(encoding="utf-8"))["statistics"]["total_items"] == 2
            assert csv_export.exists()
        finally:
            library.close()

    def test_search_history_is_pruned(self, tmp_path):
        media_file = tmp_path / "demo.mp4"
        media_file.write_bytes(b"video")
        metadata_handler = Mock()
        metadata_handler.extract_metadata.return_value = {
            "title": "Demo Video",
            "format": "mp4",
            "duration": 42.0,
            "size": media_file.stat().st_size,
            "codec": "h264",
        }
        library = self._build_library(
            tmp_path,
            metadata_handler=metadata_handler,
            search_history_limit=3,
        )
        try:
            library.add_media(str(media_file), tags=["demo"])
            for index in range(5):
                library.search_media(query=f"demo-{index}", filters=MediaSearchFilters(limit=10))

            recent = library.get_recent_searches(limit=10)
            assert len(recent) == 3
            assert [row["query_text"] for row in recent] == ["demo-4", "demo-3", "demo-2"]
        finally:
            library.close()
