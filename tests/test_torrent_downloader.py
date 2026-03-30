"""
Tests for TorrentDownloader
"""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from ravn_app.core.torrent_downloader import (
    TorrentDownloader,
    TorrentDownloadMode,
    TorrentDownloadResult,
    TorrentSource,
)
from ravn_app.core.runners import RunnerResult


class TestTorrentSource:
    def test_enum_values(self):
        assert TorrentSource.MAGNET.value == "magnet"
        assert TorrentSource.TORRENT_FILE.value == "torrent_file"


class TestTorrentDownloadMode:
    def test_enum_values(self):
        assert TorrentDownloadMode.FULL.value == "full"
        assert TorrentDownloadMode.SEQUENTIAL.value == "sequential"
        assert TorrentDownloadMode.STREAM.value == "stream"


class TestTorrentDownloadResult:
    def test_default_values(self):
        result = TorrentDownloadResult(success=True, source="magnet:?xt=urn:test")
        assert result.success is True
        assert result.source == "magnet:?xt=urn:test"
        assert result.output_files == []
        assert result.error_message == ""
        assert result.stream_url is None

    def test_with_all_values(self):
        result = TorrentDownloadResult(
            success=False,
            source="file.torrent",
            output_files=["a.mp4"],
            error_message="hata",
            stream_url="http://127.0.0.1:8080/a.mp4",
        )
        assert result.success is False
        assert result.output_files == ["a.mp4"]
        assert result.stream_url == "http://127.0.0.1:8080/a.mp4"


class TestDetectSourceType:
    def test_detect_magnet_link(self):
        td = TorrentDownloader()
        result = td.detect_source_type("magnet:?xt=urn:btih:abc123")
        assert result == TorrentSource.MAGNET

    def test_detect_torrent_file(self):
        td = TorrentDownloader()
        result = td.detect_source_type("/path/to/file.torrent")
        assert result == TorrentSource.TORRENT_FILE

    def test_detect_torrent_file_uppercase(self):
        td = TorrentDownloader()
        result = td.detect_source_type("/path/to/FILE.TORRENT")
        assert result == TorrentSource.TORRENT_FILE

    def test_detect_unsupported_raises(self):
        td = TorrentDownloader()
        with pytest.raises(ValueError, match="Desteklenmeyen"):
            td.detect_source_type("https://example.com/video")


class TestIsAvailable:
    def test_is_available_true(self):
        td = TorrentDownloader()
        with patch.object(td._runner, 'is_available', return_value=True):
            assert td.is_available() is True

    def test_is_available_false(self):
        td = TorrentDownloader()
        with patch.object(td._runner, 'is_available', return_value=False):
            assert td.is_available() is False


class TestTorrentDownloaderInit:
    def test_default_init(self):
        td = TorrentDownloader()
        assert td._runner.executable_path == "aria2c"

    def test_custom_path(self):
        td = TorrentDownloader("/custom/aria2c")
        assert td._runner.executable_path == "/custom/aria2c"


class TestCancel:
    def test_cancel_delegates_to_runner(self):
        td = TorrentDownloader()
        with patch.object(td._runner, 'cancel', return_value=True) as mock_cancel:
            result = td.cancel()
        assert result is True
        mock_cancel.assert_called_once()
