"""
CLI tests using click.testing.CliRunner.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner
import pytest

import ravn_app.cli as cli_module
from ravn_app.cli import cli


class TestCliCommands:
    def setup_method(self):
        self.runner = CliRunner()

    @patch("ravn_app.cli.YouTubeDownloader")
    @patch("ravn_app.cli.DatabaseManager")
    def test_download_json(self, mock_db_cls, mock_downloader_cls, tmp_path):
        mock_downloader = Mock()
        mock_downloader.download.return_value = Mock(
            success=True,
            url="https://example.com/video",
            output_files=[str(tmp_path / "video.mp4")],
            title="Demo Video",
            duration=20,
        )
        mock_downloader_cls.return_value = mock_downloader
        mock_db_cls.return_value = Mock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "https://example.com/video",
                "--json",
                "--output",
                str(tmp_path),
            ],
        )

        assert result.exit_code == 0
        assert '"success": true' in result.output.lower()

    @patch("ravn_app.cli.VideoConverter")
    @patch("ravn_app.cli.DatabaseManager")
    def test_convert_json(self, mock_db_cls, mock_converter_cls):
        converter = Mock()
        converter.convert.return_value = True
        mock_converter_cls.return_value = converter
        mock_db_cls.return_value = Mock()

        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            output_file = Path("output.webm")

            result = self.runner.invoke(
                cli,
                [
                    "convert",
                    str(input_file),
                    "--format",
                    "webm",
                    "--codec",
                    "vp9",
                    "--output",
                    str(output_file),
                    "--json",
                ],
            )

            assert result.exit_code == 0
            assert '"success": true' in result.output.lower()

    @patch("ravn_app.cli.FFmpegRunner")
    def test_info_json(self, mock_runner_cls):
        mock_runner = Mock()
        mock_runner.probe.return_value = {
            "format": {"duration": "60", "bit_rate": "1200000", "size": "1000"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        mock_runner_cls.return_value = mock_runner

        with self.runner.isolated_filesystem():
            input_file = Path("info.mp4")
            input_file.write_bytes(b"test")
            result = self.runner.invoke(cli, ["info", str(input_file), "--json"])
            assert result.exit_code == 0
            assert '"resolution": "1920x1080"' in result.output

    @patch("ravn_app.cli.SubtitleEmbedder")
    def test_subtitle_json(self, mock_embedder_cls):
        embedder = Mock()
        embedder.embed_soft.return_value = True
        mock_embedder_cls.return_value = embedder

        with self.runner.isolated_filesystem():
            video = Path("video.mp4")
            sub = Path("sub.srt")
            out = Path("video_sub.mp4")
            video.write_bytes(b"test")
            sub.write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n", encoding="utf-8")

            result = self.runner.invoke(
                cli,
                ["subtitle", str(video), "--embed", str(sub), "--output", str(out), "--json"],
            )
            assert result.exit_code == 0
            assert '"success": true' in result.output.lower()

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_json(self, mock_db_cls):
        db = Mock()
        db.get_downloads.return_value = [
            Mock(
                id=1,
                url="u",
                title="t",
                format="mp4",
                quality="best",
                file_path="/tmp/f",
                download_date="2024-01-01",
                status="completed",
            )
        ]
        db.get_conversions.return_value = []
        mock_db_cls.return_value = db

        result = self.runner.invoke(cli, ["history", "--json"])
        assert result.exit_code == 0
        assert '"count"' in result.output

    def test_serve_placeholder(self):
        result = self.runner.invoke(cli, ["serve", "--json"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    def test_cli_help(self):
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output
        assert "convert" in result.output

    @patch("ravn_app.cli.YouTubeDownloader")
    def test_download_failure_path(self, mock_downloader_cls, tmp_path):
        downloader = Mock()
        downloader.download.return_value = Mock(
            success=False,
            error_message="download failed",
            url="https://example.com/video",
            output_files=[],
            title="",
            duration=0,
        )
        mock_downloader_cls.return_value = downloader

        result = self.runner.invoke(
            cli,
            [
                "download",
                "https://example.com/video",
                "--json",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        assert '"success": false' in result.output.lower()

    @patch("ravn_app.cli.VideoConverter")
    def test_convert_failure_path(self, mock_converter_cls):
        converter = Mock()
        converter.convert.return_value = False
        mock_converter_cls.return_value = converter

        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            output_file = Path("output.webm")

            result = self.runner.invoke(
                cli,
                [
                    "convert",
                    str(input_file),
                    "--format",
                    "webm",
                    "--codec",
                    "vp9",
                    "--output",
                    str(output_file),
                    "--json",
                ],
            )
            assert result.exit_code == 1
            assert '"success": false' in result.output.lower()

    @patch("ravn_app.cli.FFmpegRunner")
    def test_info_probe_failure(self, mock_runner_cls):
        runner = Mock()
        runner.probe.return_value = None
        mock_runner_cls.return_value = runner

        with self.runner.isolated_filesystem():
            input_file = Path("broken.mp4")
            input_file.write_bytes(b"test")
            result = self.runner.invoke(cli, ["info", str(input_file), "--json"])
            assert result.exit_code == 1
            assert '"success": false' in result.output.lower()

    @patch("ravn_app.cli.SubtitleEmbedder")
    def test_subtitle_failure_path(self, mock_embedder_cls):
        embedder = Mock()
        embedder.embed_soft.return_value = False
        mock_embedder_cls.return_value = embedder

        with self.runner.isolated_filesystem():
            video = Path("video.mp4")
            sub = Path("sub.srt")
            out = Path("video_sub.mp4")
            video.write_bytes(b"test")
            sub.write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n", encoding="utf-8")

            result = self.runner.invoke(
                cli,
                ["subtitle", str(video), "--embed", str(sub), "--output", str(out), "--json"],
            )
            assert result.exit_code == 1
            assert '"success": false' in result.output.lower()

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_non_json_output(self, mock_db_cls):
        db = Mock()
        db.get_downloads.return_value = []
        db.get_conversions.return_value = []
        mock_db_cls.return_value = db

        result = self.runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "No history found" in result.output

    def test_output_helper_non_json_string_and_dict(self, capsys):
        cli_module._output("ok", as_json=False)
        cli_module._output({"a": 1}, as_json=False)
        captured = capsys.readouterr().out
        assert "ok" in captured
        assert '"a": 1' in captured

    def test_error_helper_non_json_exits(self, capsys):
        with pytest.raises(SystemExit):
            cli_module._error("boom", as_json=False)
        captured = capsys.readouterr().err
        assert "Error: boom" in captured

    @patch("ravn_app.cli.YouTubeDownloader")
    @patch("ravn_app.cli.DatabaseManager")
    def test_download_non_json_success(self, mock_db_cls, mock_downloader_cls, tmp_path):
        downloader = Mock()
        downloader.download.return_value = Mock(
            success=True,
            url="https://example.com/video",
            output_files=[str(tmp_path / "video.mp4")],
            title="Demo Video",
            duration=20,
        )
        mock_downloader_cls.return_value = downloader
        mock_db_cls.return_value = Mock()

        result = self.runner.invoke(
            cli,
            [
                "download",
                "https://example.com/video",
                "--quality",
                "720p",
                "--format",
                "mp4",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "Downloading:" in result.output
        assert "Done. Files saved to:" in result.output

    @patch("ravn_app.cli.YouTubeDownloader")
    def test_download_exception_non_json(self, mock_downloader_cls, tmp_path):
        downloader = Mock()
        downloader.download.side_effect = RuntimeError("network")
        mock_downloader_cls.return_value = downloader

        result = self.runner.invoke(
            cli,
            ["download", "https://example.com/video", "--output", str(tmp_path)],
        )
        assert result.exit_code == 1
        assert "Error: network" in result.output

    @patch("ravn_app.cli.YouTubeDownloader")
    @patch("ravn_app.cli.DatabaseManager")
    def test_download_db_error_nonfatal(self, mock_db_cls, mock_downloader_cls, tmp_path):
        downloader = Mock()
        downloader.download.return_value = Mock(
            success=True,
            url="https://example.com/video",
            output_files=[str(tmp_path / "video.mp4")],
            title="Demo Video",
            duration=20,
        )
        mock_downloader_cls.return_value = downloader
        mock_db_cls.side_effect = RuntimeError("db down")

        result = self.runner.invoke(
            cli,
            ["download", "https://example.com/video", "--output", str(tmp_path), "--json"],
        )
        assert result.exit_code == 0
        assert '"success": true' in result.output.lower()

    @patch("ravn_app.cli.VideoConverter")
    @patch("ravn_app.cli.DatabaseManager")
    def test_convert_non_json_success(self, mock_db_cls, mock_converter_cls):
        converter = Mock()
        converter.convert.return_value = True
        mock_converter_cls.return_value = converter
        mock_db_cls.return_value = Mock()

        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            output_file = Path("output.mkv")
            result = self.runner.invoke(
                cli,
                ["convert", str(input_file), "--format", "mkv", "--output", str(output_file)],
            )
            assert result.exit_code == 0
            assert "Converting:" in result.output
            assert "Conversion complete:" in result.output

    def test_convert_rejects_same_output_path(self):
        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            result = self.runner.invoke(
                cli,
                ["convert", str(input_file), "--output", str(input_file), "--json"],
            )
            assert result.exit_code == 1
            assert "identical to the input file" in result.output

    @patch("ravn_app.cli.VideoConverter")
    def test_convert_exception_non_json(self, mock_converter_cls):
        converter = Mock()
        converter.convert.side_effect = RuntimeError("ffmpeg crashed")
        mock_converter_cls.return_value = converter

        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            output_file = Path("output.mkv")
            result = self.runner.invoke(
                cli,
                ["convert", str(input_file), "--format", "mkv", "--output", str(output_file)],
            )
            assert result.exit_code == 1
            assert "Error: ffmpeg crashed" in result.output

    @patch("ravn_app.cli.VideoConverter")
    @patch("ravn_app.cli.DatabaseManager")
    def test_convert_db_error_nonfatal(self, mock_db_cls, mock_converter_cls):
        converter = Mock()
        converter.convert.return_value = True
        mock_converter_cls.return_value = converter
        mock_db_cls.side_effect = RuntimeError("db down")

        with self.runner.isolated_filesystem():
            input_file = Path("input.mp4")
            input_file.write_bytes(b"test")
            output_file = Path("output.mkv")
            result = self.runner.invoke(
                cli,
                ["convert", str(input_file), "--format", "mkv", "--output", str(output_file), "--json"],
            )
            assert result.exit_code == 0
            assert '"success": true' in result.output.lower()

    @patch("ravn_app.cli.FFmpegRunner")
    def test_info_non_json_success_no_fractional_fps(self, mock_runner_cls):
        runner = Mock()
        runner.probe.return_value = {
            "format": {"duration": "10", "bit_rate": "1000", "size": "100"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 640, "height": 360, "r_frame_rate": "25"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
        }
        mock_runner_cls.return_value = runner

        with self.runner.isolated_filesystem():
            input_file = Path("v.mp4")
            input_file.write_bytes(b"test")
            result = self.runner.invoke(cli, ["info", str(input_file)])
            assert result.exit_code == 0
            assert "Resolution:" in result.output
            assert "Container :" in result.output

    @patch("ravn_app.cli.FFmpegRunner")
    def test_info_exception_non_json(self, mock_runner_cls):
        runner = Mock()
        runner.probe.side_effect = RuntimeError("probe failed")
        mock_runner_cls.return_value = runner

        with self.runner.isolated_filesystem():
            input_file = Path("v.mp4")
            input_file.write_bytes(b"test")
            result = self.runner.invoke(cli, ["info", str(input_file)])
            assert result.exit_code == 1
            assert "Error: probe failed" in result.output

    @patch("ravn_app.cli.SubtitleEmbedder")
    def test_subtitle_non_json_success(self, mock_embedder_cls):
        embedder = Mock()
        embedder.embed_soft.return_value = True
        mock_embedder_cls.return_value = embedder

        with self.runner.isolated_filesystem():
            video = Path("video.mp4")
            sub = Path("sub.srt")
            out = Path("video_sub.mp4")
            video.write_bytes(b"test")
            sub.write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n", encoding="utf-8")

            result = self.runner.invoke(
                cli,
                ["subtitle", str(video), "--embed", str(sub), "--output", str(out)],
            )
            assert result.exit_code == 0
            assert "Embedding subtitle:" in result.output
            assert "Subtitle embedded:" in result.output

    @patch("ravn_app.cli.SubtitleEmbedder")
    def test_subtitle_exception_non_json(self, mock_embedder_cls):
        embedder = Mock()
        embedder.embed_soft.side_effect = RuntimeError("subtitle error")
        mock_embedder_cls.return_value = embedder

        with self.runner.isolated_filesystem():
            video = Path("video.mp4")
            sub = Path("sub.srt")
            out = Path("video_sub.mp4")
            video.write_bytes(b"test")
            sub.write_text("1\n00:00:00,000 --> 00:00:01,000\ntest\n", encoding="utf-8")

            result = self.runner.invoke(
                cli,
                ["subtitle", str(video), "--embed", str(sub), "--output", str(out)],
            )
            assert result.exit_code == 1
            assert "Error: subtitle error" in result.output

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_db_open_failure(self, mock_db_cls):
        mock_db_cls.side_effect = RuntimeError("db open failed")
        result = self.runner.invoke(cli, ["history", "--json"])
        assert result.exit_code == 1
        assert "Cannot open database" in result.output

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_download_read_failure(self, mock_db_cls):
        db = Mock()
        db.get_downloads.side_effect = RuntimeError("read fail")
        db.get_conversions.return_value = []
        mock_db_cls.return_value = db

        result = self.runner.invoke(cli, ["history", "--json"])
        assert result.exit_code == 1
        assert "Failed to read download history" in result.output

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_conversion_read_failure(self, mock_db_cls):
        db = Mock()
        db.get_downloads.return_value = []
        db.get_conversions.side_effect = RuntimeError("conv fail")
        mock_db_cls.return_value = db

        result = self.runner.invoke(cli, ["history", "--type", "convert", "--json"])
        assert result.exit_code == 1
        assert "Failed to read conversion history" in result.output

    @patch("ravn_app.cli.DatabaseManager")
    def test_history_non_json_prints_records(self, mock_db_cls):
        db = Mock()
        db.get_downloads.return_value = [
            Mock(
                id=1,
                url="https://example.com",
                title="Title",
                format="mp4",
                quality="best",
                file_path="x.mp4",
                download_date="2024-01-02",
                status="completed",
            )
        ]
        db.get_conversions.return_value = [
            Mock(
                id=2,
                input_file="in.mp4",
                output_file="out.mkv",
                input_codec="h264",
                output_codec="h265",
                conversion_date="2024-01-03",
                status="completed",
            )
        ]
        mock_db_cls.return_value = db

        result = self.runner.invoke(cli, ["history"])
        assert result.exit_code == 0
        assert "DOWNLOAD" in result.output
        assert "CONVERT" in result.output

    def test_serve_non_json(self):
        result = self.runner.invoke(cli, ["serve"])
        assert result.exit_code == 0
        assert "REST API server not yet implemented" in result.output

