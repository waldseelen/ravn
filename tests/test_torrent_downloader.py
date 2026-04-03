"""
Tests for TorrentDownloader
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ravn_app.core.runners import RunnerResult, TorrentProgressSnapshot
from ravn_app.core.torrent_downloader import (
    TorrentDownloader,
    TorrentDownloadMode,
    TorrentDownloadResult,
    TorrentSource,
)


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
        assert result.display_name == ""
        assert result.primary_file is None
        assert result.cancelled is False

    def test_with_all_values(self):
        result = TorrentDownloadResult(
            success=False,
            source="file.torrent",
            output_files=["a.mp4"],
            error_message="hata",
            stream_url="http://127.0.0.1:8080/a.mp4",
            display_name="a.mp4",
            primary_file="a.mp4",
            cancelled=True,
        )
        assert result.success is False
        assert result.output_files == ["a.mp4"]
        assert result.stream_url == "http://127.0.0.1:8080/a.mp4"
        assert result.display_name == "a.mp4"
        assert result.primary_file == "a.mp4"
        assert result.cancelled is True


class TestDetectSourceType:
    def test_detect_magnet_link(self):
        td = TorrentDownloader()
        result = td.detect_source_type("magnet:?xt=urn:btih:abc123")
        assert result == TorrentSource.MAGNET

    def test_detect_magnet_link_uppercase(self):
        td = TorrentDownloader()
        result = td.detect_source_type("MAGNET:?xt=urn:btih:abc123")
        assert result == TorrentSource.MAGNET

    def test_detect_magnet_link_with_dn_before_xt(self):
        td = TorrentDownloader()
        result = td.detect_source_type("magnet:?dn=Example&xt=urn:btih:abc123")
        assert result == TorrentSource.MAGNET

    def test_detect_torrent_file(self):
        td = TorrentDownloader()
        result = td.detect_source_type("/path/to/file.torrent")
        assert result == TorrentSource.TORRENT_FILE

    def test_detect_torrent_url(self):
        td = TorrentDownloader()
        result = td.detect_source_type("https://example.com/file.torrent?download=1")
        assert result == TorrentSource.TORRENT_FILE

    def test_detect_torrent_file_uppercase(self):
        td = TorrentDownloader()
        result = td.detect_source_type("/path/to/FILE.TORRENT")
        assert result == TorrentSource.TORRENT_FILE

    def test_detect_unsupported_raises(self):
        td = TorrentDownloader()
        with pytest.raises(ValueError, match="Desteklenmeyen"):
            td.detect_source_type("https://example.com/video")


class TestDisplayNameInference:
    def test_infer_display_name_prefers_magnet_dn(self):
        td = TorrentDownloader()
        result = td.infer_display_name("magnet:?xt=urn:btih:abc123&dn=My+Movie+1080p")
        assert result == "My Movie 1080p"

    def test_infer_display_name_uses_torrent_stem(self):
        td = TorrentDownloader()
        result = td.infer_display_name("C:/downloads/Series.S01E01.torrent")
        assert result == "Series.S01E01"


class TestIsAvailable:
    def test_is_available_true(self):
        td = TorrentDownloader()
        with patch.object(td._runner, "is_available", return_value=True):
            assert td.is_available() is True

    def test_is_available_false(self):
        td = TorrentDownloader()
        with patch.object(td._runner, "is_available", return_value=False):
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
        with patch.object(td._runner, "cancel", return_value=True) as mock_cancel:
            result = td.cancel()
        assert result is True
        mock_cancel.assert_called_once()


class TestOutputCollection:
    def test_collect_output_files_recurses_and_returns_all_payloads(self, tmp_path: Path):
        td = TorrentDownloader()
        nested = tmp_path / "Show" / "Season 1"
        nested.mkdir(parents=True)
        video = nested / "episode01.mkv"
        note = nested / "README.txt"
        video.write_bytes(b"video-data")
        note.write_text("info", encoding="utf-8")

        result = td._collect_output_files(str(tmp_path))

        assert set(result) == {str(video.resolve()), str(note.resolve())}

    def test_collect_output_files_skips_torrent_temp_files(self, tmp_path: Path):
        td = TorrentDownloader()
        archive = tmp_path / "bundle.zip"
        temp_meta = tmp_path / "bundle.zip.aria2"
        torrent_meta = tmp_path / "bundle.torrent"
        archive.write_bytes(b"zip-data")
        temp_meta.write_bytes(b"temp")
        torrent_meta.write_bytes(b"meta")

        result = td._collect_output_files(str(tmp_path))

        assert result == [str(archive.resolve())]

    def test_list_playable_files_filters_media(self, tmp_path: Path):
        td = TorrentDownloader()
        video = tmp_path / "movie.mp4"
        note = tmp_path / "readme.txt"
        video.write_bytes(b"video")
        note.write_text("note", encoding="utf-8")

        result = td.list_playable_files([str(video), str(note)])

        assert result == [str(video)]

    def test_pick_primary_output_file_uses_largest_media(self, tmp_path: Path):
        td = TorrentDownloader()
        small = tmp_path / "small.mp4"
        large = tmp_path / "large.mkv"
        note = tmp_path / "readme.txt"
        small.write_bytes(b"1" * 10)
        large.write_bytes(b"1" * 100)
        note.write_text("note", encoding="utf-8")

        result = td._pick_primary_output_file([str(small), str(large), str(note)])

        assert result == str(large)


class TestDownloadFlow:
    def test_download_propagates_progress_and_returns_primary_file(self, tmp_path: Path):
        td = TorrentDownloader()
        target_file = tmp_path / "Movie.mkv"
        target_file.write_bytes(b"1" * 32)
        received = []

        def fake_download(*args, **kwargs):
            progress_callback = kwargs["progress_callback"]
            progress_callback(
                TorrentProgressSnapshot(
                    percent=45,
                    name="Movie.mkv",
                    downloaded_text="450.0 MB",
                    total_text="1.0 GB",
                    remaining_text="574.0 MB",
                    speed_text="4MiB/s",
                    eta_text="2m",
                    status_message="4MiB/s • ETA 2m",
                )
            )
            return RunnerResult(success=True, return_code=0)

        with patch.object(td._runner, "download", side_effect=fake_download):
            result = td.download(
                source="magnet:?xt=urn:btih:abc123&dn=Movie",
                output_dir=str(tmp_path),
                progress_callback=lambda snapshot: received.append(snapshot),
            )

        assert result.success is True
        assert result.display_name == "Movie.mkv"
        assert result.primary_file == str(target_file.resolve())
        assert result.output_files == [str(target_file.resolve())]
        assert len(received) == 1
        assert received[0].percent == 45
        assert received[0].name == "Movie.mkv"

    def test_download_returns_cancelled_result(self, tmp_path: Path):
        td = TorrentDownloader()
        with patch.object(
            td._runner,
            "download",
            return_value=RunnerResult(success=False, return_code=-15, error_message="Cancelled", metadata={"cancelled": True}),
        ):
            result = td.download(
                source="magnet:?xt=urn:btih:abc123",
                output_dir=str(tmp_path),
            )

        assert result.success is False
        assert result.cancelled is True
        assert result.error_message == ""
