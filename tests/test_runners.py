"""
Tests for FFmpegRunner and YtDlpRunner classes
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ravn_app.core.runners import (
    FFmpegRunner,
    YtDlpRunner,
    RunnerResult,
    RunnerStatus,
    get_ffmpeg_runner,
    get_ytdlp_runner,
    Aria2Runner,
    TorrentProgressSnapshot,
    get_aria2c_runner,
)
from ravn_app.core.runners.aria2 import _Aria2ProgressParser, emit_torrent_progress


class TestFFmpegRunner:
    """Tests for FFmpegRunner class"""

    def test_initialization(self):
        """Test FFmpegRunner initialization"""
        runner = FFmpegRunner()
        assert runner.executable_path == "ffmpeg"
        assert runner.ffprobe_path == "ffprobe"
        assert runner.status == RunnerStatus.IDLE
        assert runner.current_process is None

    def test_initialization_custom_paths(self):
        """Test FFmpegRunner with custom paths"""
        runner = FFmpegRunner("/custom/ffmpeg", "/custom/ffprobe")
        assert runner.executable_path == "/custom/ffmpeg"
        assert runner.ffprobe_path == "/custom/ffprobe"

    def test_build_command_basic(self):
        """Test basic command building"""
        runner = FFmpegRunner()
        cmd = runner._build_command(
            input_file="input.mp4",
            output_file="output.mp4"
        )
        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert "input.mp4" in cmd
        assert "output.mp4" in cmd
        assert "-y" in cmd  # overwrite flag

    def test_build_command_with_video_args(self):
        """Test command building with video arguments"""
        runner = FFmpegRunner()
        cmd = runner._build_command(
            input_file="input.mp4",
            output_file="output.mp4",
            video_args=["-c:v", "libx264", "-crf", "23"]
        )
        assert "-c:v" in cmd
        assert "libx264" in cmd
        assert "-crf" in cmd
        assert "23" in cmd

    def test_build_command_with_audio_args(self):
        """Test command building with audio arguments"""
        runner = FFmpegRunner()
        cmd = runner._build_command(
            input_file="input.mp4",
            output_file="output.mp4",
            audio_args=["-c:a", "aac", "-b:a", "128k"]
        )
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-b:a" in cmd
        assert "128k" in cmd

    def test_build_command_without_overwrite(self):
        """Test command building without overwrite flag"""
        runner = FFmpegRunner()
        cmd = runner._build_command(
            input_file="input.mp4",
            output_file="output.mp4",
            overwrite=False
        )
        assert "-y" not in cmd

    def test_parse_error_file_not_found(self):
        """Test error parsing for file not found"""
        runner = FFmpegRunner()
        stderr = "No such file or directory: input.mp4"
        result = runner._parse_error(stderr)
        assert "not found" in result.lower()

    def test_parse_error_invalid_input(self):
        """Test error parsing for invalid input"""
        runner = FFmpegRunner()
        stderr = "Invalid data found when processing input"
        result = runner._parse_error(stderr)
        assert "invalid" in result.lower() or "corrupted" in result.lower()

    def test_parse_error_unknown_encoder(self):
        """Test error parsing for unknown encoder"""
        runner = FFmpegRunner()
        stderr = "Unknown encoder 'libfoo'"
        result = runner._parse_error(stderr)
        assert "encoder" in result.lower() or "codec" in result.lower()

    def test_parse_error_permission_denied(self):
        """Test error parsing for permission denied"""
        runner = FFmpegRunner()
        stderr = "Permission denied when writing output"
        result = runner._parse_error(stderr)
        assert "permission" in result.lower()

    def test_parse_error_disk_full(self):
        """Test error parsing for disk full"""
        runner = FFmpegRunner()
        stderr = "No space left on device"
        result = runner._parse_error(stderr)
        assert "disk" in result.lower() or "space" in result.lower()

    @patch('subprocess.run')
    def test_get_version_success(self, mock_run):
        """Test getting FFmpeg version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="ffmpeg version 5.1.2 Copyright (c) 2000-2022"
        )
        runner = FFmpegRunner()
        version = runner.get_version()
        assert version is not None
        assert "ffmpeg" in version.lower()

    @patch('subprocess.run')
    def test_get_version_failure(self, mock_run):
        """Test getting FFmpeg version when not available"""
        mock_run.side_effect = FileNotFoundError()
        runner = FFmpegRunner()
        version = runner.get_version()
        assert version is None

    @patch('subprocess.run')
    def test_probe_success(self, mock_run):
        """Test FFprobe successful analysis"""
        mock_data = {
            "format": {
                "duration": "120.5",
                "bit_rate": "1500000"
            },
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"}
            ]
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )
        runner = FFmpegRunner()

        with patch('os.path.exists', return_value=True):
            result = runner.probe("test.mp4")

        assert result is not None
        assert "format" in result
        assert "streams" in result

    @patch('subprocess.run')
    def test_probe_file_not_found(self, mock_run):
        """Test FFprobe with non-existent file"""
        runner = FFmpegRunner()

        with patch('os.path.exists', return_value=False):
            result = runner.probe("nonexistent.mp4")

        assert result is None

    @patch('subprocess.run')
    def test_get_duration(self, mock_run):
        """Test getting media duration"""
        mock_data = {
            "format": {"duration": "120.5"}
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )
        runner = FFmpegRunner()

        with patch('os.path.exists', return_value=True):
            duration = runner.get_duration("test.mp4")

        assert duration == 120.5

    @patch('subprocess.run')
    def test_check_codec_support(self, mock_run):
        """Test codec support check"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="V..... libx264    H.264 / AVC"
        )
        runner = FFmpegRunner()
        assert runner.check_codec_support("libx264") is True
        assert runner.check_codec_support("nonexistent") is False

    def test_run_input_not_found(self):
        """Test run with non-existent input file"""
        runner = FFmpegRunner()
        result = runner.run("nonexistent.mp4", "output.mp4")
        assert result.success is False
        assert "not found" in result.error_message.lower()

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('os.path.getsize')
    def test_run_success(self, mock_getsize, mock_makedirs, mock_exists, mock_popen):
        """Test successful FFmpeg run"""
        mock_exists.return_value = True
        mock_getsize.return_value = 1000

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        runner = FFmpegRunner()
        result = runner.run("input.mp4", "output.mp4")

        assert result.success is True
        assert result.return_code == 0

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_run_failure(self, mock_makedirs, mock_exists, mock_popen):
        """Test failed FFmpeg run"""
        mock_exists.return_value = True

        mock_process = Mock()
        mock_process.communicate.return_value = ("", "Conversion failed")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        runner = FFmpegRunner()
        result = runner.run("input.mp4", "output.mp4")

        assert result.success is False
        assert result.return_code == 1

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_run_timeout(self, mock_makedirs, mock_exists, mock_popen):
        """Test FFmpeg run timeout"""
        import subprocess
        mock_exists.return_value = True

        mock_process = Mock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired("cmd", 10)
        mock_process.kill = Mock()
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process

        runner = FFmpegRunner()
        result = runner.run("input.mp4", "output.mp4", timeout=10)

        assert result.success is False
        assert "timed out" in result.error_message.lower()

    def test_cancel_no_process(self):
        """Test cancel when no process running"""
        runner = FFmpegRunner()
        result = runner.cancel()
        assert result is False

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    @patch('os.makedirs')
    def test_cancel_running_process(self, mock_makedirs, mock_exists, mock_popen):
        """Test cancel with running process"""
        mock_exists.return_value = True

        mock_process = Mock()
        mock_process.terminate = Mock()
        mock_process.wait = Mock()
        mock_popen.return_value = mock_process

        runner = FFmpegRunner()
        runner.current_process = mock_process
        runner.status = RunnerStatus.RUNNING

        result = runner.cancel()
        assert result is True
        mock_process.terminate.assert_called_once()


class TestYtDlpRunner:
    """Tests for YtDlpRunner class"""

    def test_initialization(self):
        """Test YtDlpRunner initialization"""
        runner = YtDlpRunner()
        assert runner.executable_path == "yt-dlp"
        assert runner.status == RunnerStatus.IDLE

    def test_initialization_custom_path(self):
        """Test YtDlpRunner with custom path"""
        runner = YtDlpRunner("/custom/yt-dlp")
        assert runner.executable_path == "/custom/yt-dlp"

    def test_build_command_basic(self):
        """Test basic command building"""
        runner = YtDlpRunner()
        cmd = runner._build_command(
            url="https://example.com/video",
            output_template="output/%(title)s.%(ext)s"
        )
        assert cmd[0] == "yt-dlp"
        assert "--no-warnings" in cmd
        assert "-o" in cmd
        assert "--newline" in cmd
        assert "https://example.com/video" in cmd

    def test_build_command_with_format(self):
        """Test command building with format spec"""
        runner = YtDlpRunner()
        cmd = runner._build_command(
            url="https://example.com/video",
            output_template="output/%(title)s.%(ext)s",
            format_spec="bestvideo+bestaudio/best"
        )
        assert "-f" in cmd
        assert "bestvideo+bestaudio/best" in cmd

    def test_build_command_with_extra_args(self):
        """Test command building with extra arguments"""
        runner = YtDlpRunner()
        cmd = runner._build_command(
            url="https://example.com/video",
            output_template="output/%(title)s.%(ext)s",
            extra_args=["--write-thumbnail", "--embed-metadata"]
        )
        assert "--write-thumbnail" in cmd
        assert "--embed-metadata" in cmd

    def test_parse_error_video_unavailable(self):
        """Test error parsing for unavailable video"""
        runner = YtDlpRunner()
        stderr = "ERROR: Video unavailable"
        result = runner._parse_error(stderr)
        assert "unavailable" in result.lower()

    def test_parse_error_private_video(self):
        """Test error parsing for private video"""
        runner = YtDlpRunner()
        stderr = "ERROR: Private video"
        result = runner._parse_error(stderr)
        assert "private" in result.lower()

    def test_parse_error_age_restricted(self):
        """Test error parsing for age-restricted content"""
        runner = YtDlpRunner()
        stderr = "Sign in to confirm your age"
        result = runner._parse_error(stderr)
        assert "age" in result.lower()

    def test_parse_error_geo_restricted(self):
        """Test error parsing for geo-restricted content"""
        runner = YtDlpRunner()
        stderr = "Geo-restricted content"
        result = runner._parse_error(stderr)
        assert "geo" in result.lower()

    def test_parse_error_invalid_url(self):
        """Test error parsing for invalid URL"""
        runner = YtDlpRunner()
        stderr = "ERROR: is not a valid URL"
        result = runner._parse_error(stderr)
        assert "invalid" in result.lower() or "url" in result.lower()

    def test_parse_error_http_403(self):
        """Test error parsing for HTTP 403"""
        runner = YtDlpRunner()
        stderr = "HTTP Error 403: Forbidden"
        result = runner._parse_error(stderr)
        assert "403" in result or "denied" in result.lower()

    def test_parse_error_http_429(self):
        """Test error parsing for HTTP 429"""
        runner = YtDlpRunner()
        stderr = "HTTP Error 429: Too Many Requests"
        result = runner._parse_error(stderr)
        assert "429" in result or "too many" in result.lower()

    @patch('subprocess.run')
    def test_get_version_success(self, mock_run):
        """Test getting yt-dlp version"""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="2024.01.01"
        )
        runner = YtDlpRunner()
        version = runner.get_version()
        assert version == "2024.01.01"

    @patch('subprocess.run')
    def test_get_version_failure(self, mock_run):
        """Test getting yt-dlp version when not available"""
        mock_run.side_effect = FileNotFoundError()
        runner = YtDlpRunner()
        version = runner.get_version()
        assert version is None

    @patch('subprocess.run')
    def test_extract_info_success(self, mock_run):
        """Test successful info extraction"""
        mock_data = {
            "title": "Test Video",
            "duration": 120,
            "formats": [{"format_id": "22"}]
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )
        runner = YtDlpRunner()
        result = runner.extract_info("https://example.com/video")

        assert result is not None
        assert result["title"] == "Test Video"
        assert result["duration"] == 120

    @patch('subprocess.run')
    def test_extract_info_failure(self, mock_run):
        """Test failed info extraction"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Video unavailable"
        )
        runner = YtDlpRunner()
        result = runner.extract_info("https://example.com/video")
        assert result is None

    @patch('subprocess.run')
    def test_list_formats(self, mock_run):
        """Test listing available formats"""
        mock_data = {
            "formats": [
                {"format_id": "22", "ext": "mp4"},
                {"format_id": "18", "ext": "mp4"}
            ]
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data)
        )
        runner = YtDlpRunner()
        formats = runner.list_formats("https://example.com/video")

        assert formats is not None
        assert len(formats) == 2

    @patch('subprocess.run')
    def test_extract_playlist_entries_success(self, mock_run):
        """Test playlist entry extraction for YouTube IDs"""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {"id": "abc123", "title": "Video 1", "duration": 100, "view_count": 12345},
                {"webpage_url": "https://youtu.be/def456", "title": "Video 2", "duration": 200},
            ],
        }
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(mock_data),
        )

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries("https://www.youtube.com/playlist?list=PL123")

        assert len(entries) == 2
        assert entries[0]["url"] == "https://www.youtube.com/watch?v=abc123"
        assert entries[0]["title"] == "Video 1"
        assert entries[0]["view_count"] == 12345
        assert entries[1]["url"] == "https://youtu.be/def456"

    @patch('subprocess.run')
    def test_extract_playlist_entries_failure(self, mock_run):
        """Test playlist extraction failure returns empty list"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr="Playlist unavailable",
        )

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries("https://example.com/playlist")
        assert entries == []

    @patch('subprocess.run')
    def test_extract_playlist_entries_with_quality_specific_details(self, mock_run):
        """Test playlist extraction picks format details based on selected quality"""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Video 1",
                    "duration": 120,
                    "formats": [
                        {
                            "format_id": "18",
                            "width": 854,
                            "height": 480,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 30 * 1024 * 1024,
                            "format_note": "480p"
                        },
                        {
                            "format_id": "22",
                            "width": 1280,
                            "height": 720,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 52 * 1024 * 1024,
                            "format_note": "720p"
                        },
                        {
                            "format_id": "137+140",
                            "width": 1920,
                            "height": 1080,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 90 * 1024 * 1024,
                            "format_note": "1080p"
                        },
                    ],
                }
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data))

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries(
            "https://www.youtube.com/playlist?list=PL123",
            with_details=True,
            quality_label="720p",
        )

        assert len(entries) == 1
        assert entries[0]["resolution"] == "1280x720"
        assert entries[0]["filesize_mb"] == 52.0
        assert entries[0]["format_note"] == "720p"

    @patch('subprocess.run')
    def test_extract_playlist_entries_with_dash_split_streams(self, mock_run):
        """Test quality details include paired audio when only video stream matches selected quality."""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Video 1",
                    "duration": 120,
                    "formats": [
                        {
                            "format_id": "137",
                            "width": 1920,
                            "height": 1080,
                            "vcodec": "avc1",
                            "acodec": "none",
                            "filesize": 80 * 1024 * 1024,
                            "format_note": "1080p"
                        },
                        {
                            "format_id": "248",
                            "width": 1280,
                            "height": 720,
                            "vcodec": "vp9",
                            "acodec": "none",
                            "filesize": 44 * 1024 * 1024,
                            "format_note": "720p"
                        },
                        {
                            "format_id": "140",
                            "vcodec": "none",
                            "acodec": "mp4a",
                            "filesize": 9 * 1024 * 1024,
                            "format_note": "audio"
                        },
                    ],
                }
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data))

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries(
            "https://www.youtube.com/playlist?list=PL123",
            with_details=True,
            quality_label="720p",
        )

        assert len(entries) == 1
        assert entries[0]["resolution"] == "1280x720"
        assert entries[0]["filesize_mb"] == 53.0

    @patch('subprocess.run')
    def test_extract_playlist_entries_size_fallback_keeps_selected_resolution(self, mock_run):
        """When selected quality size is unknown, fallback size should not overwrite selected resolution."""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Video 1",
                    "duration": 120,
                    "formats": [
                        {
                            "format_id": "22",
                            "width": 1280,
                            "height": 720,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "format_note": "720p"
                        },
                        {
                            "format_id": "137+140",
                            "width": 1920,
                            "height": 1080,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 90 * 1024 * 1024,
                            "format_note": "1080p"
                        },
                    ],
                }
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data))

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries(
            "https://www.youtube.com/playlist?list=PL123",
            with_details=True,
            quality_label="720p",
        )

        assert len(entries) == 1
        assert entries[0]["resolution"] == "1280x720"
        assert entries[0]["filesize_mb"] == 90.0

    @patch('subprocess.run')
    def test_extract_playlist_entries_prefers_split_1080_over_progressive_360(self, mock_run):
        """Test 1080p selection prefers video-only 1080 + audio over lower progressive formats."""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Video 1",
                    "duration": 120,
                    "formats": [
                        {
                            "format_id": "18",
                            "width": 640,
                            "height": 360,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 20 * 1024 * 1024,
                            "format_note": "360p"
                        },
                        {
                            "format_id": "137",
                            "width": 1920,
                            "height": 1080,
                            "vcodec": "avc1",
                            "acodec": "none",
                            "filesize": 80 * 1024 * 1024,
                            "format_note": "1080p"
                        },
                        {
                            "format_id": "140",
                            "vcodec": "none",
                            "acodec": "mp4a",
                            "filesize": 9 * 1024 * 1024,
                            "format_note": "audio"
                        },
                    ],
                }
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data))

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries(
            "https://www.youtube.com/playlist?list=PL123",
            with_details=True,
            quality_label="1080p",
        )

        assert len(entries) == 1
        assert entries[0]["resolution"] == "1920x1080"
        assert entries[0]["filesize_mb"] == 89.0

    @patch('subprocess.run')
    def test_extract_playlist_entries_audio_only_prefers_pure_audio_stream(self, mock_run):
        """Test audio-only quality avoids muxed video+audio formats when pure audio exists."""
        mock_data = {
            "webpage_url": "https://www.youtube.com/playlist?list=PL123",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Video 1",
                    "duration": 120,
                    "formats": [
                        {
                            "format_id": "22",
                            "width": 1280,
                            "height": 720,
                            "vcodec": "avc1",
                            "acodec": "mp4a",
                            "filesize": 52 * 1024 * 1024,
                            "format_note": "720p"
                        },
                        {
                            "format_id": "140",
                            "vcodec": "none",
                            "acodec": "mp4a",
                            "filesize": 8 * 1024 * 1024,
                            "format_note": "audio"
                        },
                    ],
                }
            ],
        }
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(mock_data))

        runner = YtDlpRunner()
        entries = runner.extract_playlist_entries(
            "https://www.youtube.com/playlist?list=PL123",
            with_details=True,
            quality_label="Sadece Ses",
        )

        assert len(entries) == 1
        assert entries[0]["resolution"] == "Audio"
        assert entries[0]["filesize_mb"] == 8.0

    def test_extract_downloaded_files(self):
        """Test extracting downloaded file paths from output"""
        runner = YtDlpRunner()
        stdout = """
        [download] Destination: /path/to/video.mp4
        [download] 100% of 50.00MiB
        [Merger] Merging formats into "/path/to/final.mkv"
        """
        files = runner._extract_downloaded_files(stdout)
        assert "/path/to/video.mp4" in files
        assert "/path/to/final.mkv" in files

    @patch('subprocess.run')
    def test_update_success(self, mock_run):
        """Test successful yt-dlp update"""
        mock_run.return_value = Mock(returncode=0)
        runner = YtDlpRunner()
        result = runner.update()
        assert result is True

    @patch('subprocess.run')
    def test_update_failure(self, mock_run):
        """Test failed yt-dlp update"""
        mock_run.return_value = Mock(returncode=1)
        runner = YtDlpRunner()
        result = runner.update()
        assert result is False

    @patch('subprocess.Popen')
    @patch('os.makedirs')
    def test_download_success(self, mock_makedirs, mock_popen):
        """Test successful download"""
        mock_process = Mock()
        mock_process.communicate.return_value = (
            "[download] Destination: output/video.mp4",
            ""
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        runner = YtDlpRunner()
        result = runner.download(
            url="https://example.com/video",
            output_dir="output"
        )

        assert result.success is True
        assert result.return_code == 0
        assert result.metadata["archive_skipped"] is False

    @patch('subprocess.Popen')
    @patch('os.makedirs')
    def test_download_success_marks_archive_skip_metadata(self, mock_makedirs, mock_popen):
        """Archive-skip output should be exposed to higher download layers."""
        mock_process = Mock()
        mock_process.communicate.return_value = (
            "[download] VIDEO123: has already been recorded in the archive",
            "",
        )
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        runner = YtDlpRunner()
        result = runner.download(
            url="https://example.com/video",
            output_dir="output"
        )

        assert result.success is True
        assert result.metadata["archive_skipped"] is True
        assert result.metadata["downloaded_files"] == []

    @patch('subprocess.Popen')
    @patch('os.makedirs')
    def test_download_failure_no_retry(self, mock_makedirs, mock_popen):
        """Test download failure that shouldn't retry"""
        mock_process = Mock()
        mock_process.communicate.return_value = ("", "Video unavailable")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        runner = YtDlpRunner()
        result = runner.download(
            url="https://example.com/video",
            output_dir="output",
            retries=3
        )

        assert result.success is False
        # Should not retry 3 times for unavailable videos
        assert mock_popen.call_count == 1


class TestRunnerResult:
    """Tests for RunnerResult dataclass"""

    def test_default_values(self):
        """Test RunnerResult default values"""
        result = RunnerResult(success=True, return_code=0)
        assert result.success is True
        assert result.return_code == 0
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.error_message == ""
        assert result.duration_seconds == 0.0
        assert result.metadata == {}

    def test_with_all_values(self):
        """Test RunnerResult with all values"""
        result = RunnerResult(
            success=False,
            return_code=1,
            stdout="output",
            stderr="error output",
            error_message="Something failed",
            duration_seconds=5.5,
            metadata={"key": "value"}
        )
        assert result.success is False
        assert result.return_code == 1
        assert result.stdout == "output"
        assert result.stderr == "error output"
        assert result.error_message == "Something failed"
        assert result.duration_seconds == 5.5
        assert result.metadata == {"key": "value"}


class TestFactoryFunctions:
    """Tests for factory functions"""

    def test_get_ffmpeg_runner_default(self):
        """Test get_ffmpeg_runner with defaults"""
        runner = get_ffmpeg_runner()
        assert isinstance(runner, FFmpegRunner)
        assert runner.executable_path == "ffmpeg"
        assert runner.ffprobe_path == "ffprobe"

    def test_get_ffmpeg_runner_custom(self):
        """Test get_ffmpeg_runner with custom paths"""
        runner = get_ffmpeg_runner("/custom/ffmpeg", "/custom/ffprobe")
        assert runner.executable_path == "/custom/ffmpeg"
        assert runner.ffprobe_path == "/custom/ffprobe"

    def test_get_ytdlp_runner_default(self):
        """Test get_ytdlp_runner with defaults"""
        runner = get_ytdlp_runner()
        assert isinstance(runner, YtDlpRunner)
        assert runner.executable_path == "yt-dlp"

    def test_get_ytdlp_runner_custom(self):
        """Test get_ytdlp_runner with custom path"""
        runner = get_ytdlp_runner("/custom/yt-dlp")
        assert runner.executable_path == "/custom/yt-dlp"


class TestRunnerStatus:
    """Tests for RunnerStatus enum"""

    def test_status_values(self):
        """Test all RunnerStatus values"""
        assert RunnerStatus.IDLE.value == "idle"
        assert RunnerStatus.RUNNING.value == "running"
        assert RunnerStatus.COMPLETED.value == "completed"
        assert RunnerStatus.FAILED.value == "failed"
        assert RunnerStatus.CANCELLED.value == "cancelled"
        assert RunnerStatus.TIMEOUT.value == "timeout"


class TestAria2Runner:
    """Tests for Aria2Runner class."""

    # ------------------------------------------------------------------
    # _build_command tests
    # ------------------------------------------------------------------

    def test_build_command_basic(self):
        """Basic command contains expected flags and source."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="https://example.com/file.iso",
            output_dir="/tmp/downloads",
        )
        assert cmd[0] == "aria2c"
        assert "--console-log-level=notice" in cmd
        assert "--show-console-readout=false" in cmd
        assert "--summary-interval=1" in cmd
        assert "https://example.com/file.iso" in cmd

    def test_build_command_sequential_true(self):
        """sequential=True adds head-first torrent flags."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="magnet:?xt=urn:example",
            output_dir="/tmp/dl",
            sequential=True,
        )
        assert "--file-allocation=none" in cmd
        assert "--enable-sequential-download=true" in cmd
        assert "--bt-prioritize-piece=head=5M" in cmd

    def test_build_command_sequential_false(self):
        """sequential=False (default) does NOT add sequential flags."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="https://example.com/file.iso",
            output_dir="/tmp/dl",
            sequential=False,
        )
        assert "--file-allocation=none" not in cmd
        assert "--enable-sequential-download=true" not in cmd

    def test_build_command_seed_time_zero(self):
        """seed_time=0 adds --seed-time=0 flag."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="magnet:?xt=urn:example",
            output_dir="/tmp/dl",
            seed_time=0,
        )
        assert "--seed-time=0" in cmd

    def test_build_command_seed_time_nonzero(self):
        """seed_time > 0 does NOT add --seed-time=0."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="magnet:?xt=urn:example",
            output_dir="/tmp/dl",
            seed_time=60,
        )
        assert "--seed-time=0" not in cmd

    def test_build_command_with_extra_args(self):
        """extra_args are appended to the command."""
        runner = Aria2Runner()
        cmd = runner._build_command(
            source="https://example.com/file.iso",
            output_dir="/tmp/dl",
            extra_args=["--max-connection-per-server=5"],
        )
        assert "--max-connection-per-server=5" in cmd

    # ------------------------------------------------------------------
    # _parse_error tests
    # ------------------------------------------------------------------

    def test_parse_error_unknown(self):
        """errorCode=1 maps to a 'bilinmeyen' message."""
        runner = Aria2Runner()
        result = runner._parse_error("errorCode=1 unknown error occurred")
        assert "bilinmeyen" in result.lower()

    def test_parse_error_resource_not_found(self):
        """errorCode=3 maps to a resource-not-found message."""
        runner = Aria2Runner()
        result = runner._parse_error("errorCode=3 resource not found")
        assert "kaynak" in result.lower() or "bulunamadı" in result.lower()

    def test_parse_error_network(self):
        """errorCode=6 maps to a network-error message."""
        runner = Aria2Runner()
        result = runner._parse_error("errorCode=6 network problem")
        assert "ağ" in result.lower() or "network" in result.lower()

    def test_parse_error_disk_full(self):
        """errorCode=9 maps to a disk/space message."""
        runner = Aria2Runner()
        result = runner._parse_error("errorCode=9 not enough disk space")
        assert "disk" in result.lower() or "space" in result.lower()

    def test_parse_error_file_exists(self):
        """errorCode=13 maps to a file-exists message."""
        runner = Aria2Runner()
        result = runner._parse_error("errorCode=13 file already exists")
        assert (
            "dosya" in result.lower()
            or "mevcut" in result.lower()
            or "exists" in result.lower()
        )

    def test_parse_error_fallback(self):
        """Unrecognised stderr still returns a non-empty string."""
        runner = Aria2Runner()
        result = runner._parse_error("Some random error text")
        assert len(result) > 0

    # ------------------------------------------------------------------
    # is_available tests
    # ------------------------------------------------------------------

    @patch.object(Aria2Runner, "_find_executable", return_value="/usr/bin/aria2c")
    def test_is_available_true(self, mock_find):
        """is_available() returns True when executable is found."""
        runner = Aria2Runner()
        assert runner.is_available() is True

    @patch.object(Aria2Runner, "_find_executable", return_value=None)
    def test_is_available_false(self, mock_find):
        """is_available() returns False when executable is not found."""
        runner = Aria2Runner()
        assert runner.is_available() is False

    # ------------------------------------------------------------------
    # Factory function tests
    # ------------------------------------------------------------------

    def test_get_aria2c_runner_default(self):
        """get_aria2c_runner() returns an Aria2Runner with default path."""
        runner = get_aria2c_runner()
        assert isinstance(runner, Aria2Runner)
        assert runner.executable_path == "aria2c"

    def test_get_aria2c_runner_custom_path(self):
        """get_aria2c_runner() accepts a custom executable path."""
        runner = get_aria2c_runner("/custom/aria2c")
        assert runner.executable_path == "/custom/aria2c"

    # ------------------------------------------------------------------
    # Progress regex tests
    # ------------------------------------------------------------------

    def test_parse_progress_regex(self):
        """Percent and DL-speed regex patterns parse aria2c output correctly."""
        import re

        percent_pattern = re.compile(r"\((\d+)%\)")
        dl_pattern = re.compile(r"DL:(\S+)")

        line = "(45%) DL:1.2MiB"
        assert percent_pattern.search(line).group(1) == "45"
        assert dl_pattern.search(line).group(1) == "1.2MiB"

    def test_progress_parser_extracts_eta_sizes_and_name(self):
        parser = _Aria2ProgressParser()

        parser.parse_line("FILE: /downloads/My.Movie.2026.mkv")
        snapshot = parser.parse_line("[#1 SIZE:512MiB/2GiB(25%) CN:8 SEED:14 SPD:4MiBs ETA:6m30s]")

        assert snapshot is not None
        assert snapshot.name == "My.Movie.2026.mkv"
        assert snapshot.percent == 25
        assert snapshot.downloaded_text == "512.0 MB"
        assert snapshot.total_text == "2.0 GB"
        assert snapshot.remaining_text == "1.5 GB"
        assert snapshot.speed_text == "4MiB/s"
        assert snapshot.eta_text == "6m30s"
        assert snapshot.peers == 8
        assert snapshot.peers_text == "8"
        assert snapshot.seeders == 14
        assert snapshot.seeders_text == "14"

    def test_emit_torrent_progress_supports_snapshot_callback(self):
        received = []

        def callback(snapshot: TorrentProgressSnapshot):
            received.append(snapshot)

        snapshot = TorrentProgressSnapshot(percent=42, status_message="4MiB/s")
        emit_torrent_progress(callback, snapshot)

        assert received == [snapshot]

    @patch.object(Aria2Runner, "_find_executable", return_value="/custom/aria2c")
    def test_is_available_uses_custom_executable_path(self, mock_find):
        runner = Aria2Runner("/custom/aria2c")
        assert runner.is_available() is True
        mock_find.assert_called_once_with("/custom/aria2c")
