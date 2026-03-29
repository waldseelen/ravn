"""
Integration tests for download -> convert pipeline using mocks.
"""

from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.core.converter import (
    AudioCodec,
    ConversionSettings,
    VideoCodec,
    VideoConverter,
    VideoQuality,
)
from ravn_app.core.downloader import DownloadFormat, DownloadQuality, YouTubeDownloader
from ravn_app.core.runners import RunnerResult


class TestDownloadConvertPipeline:
    @patch("ravn_app.core.downloader.YtDlpRunner.download")
    @patch("ravn_app.core.converter.FFmpegRunner.run")
    def test_pipeline_success(self, mock_ffmpeg_run, mock_ytdlp_download, tmp_path):
        download_file = tmp_path / "downloaded.mp4"
        output_file = tmp_path / "converted.mkv"
        download_file.write_bytes(b"source")

        mock_ytdlp_download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(download_file)]},
        )
        mock_ffmpeg_run.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"output_size": 1000, "input_size": 1000},
        )

        downloader = YouTubeDownloader()
        dl_result = downloader.download(
            url="https://example.com/video",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
        )

        assert dl_result.success is True
        assert dl_result.output_files == [str(download_file)]

        converter = VideoConverter()
        settings = ConversionSettings(
            input_file=str(download_file),
            output_file=str(output_file),
            video_codec=VideoCodec.H265,
            audio_codec=AudioCodec.AAC,
            video_quality=VideoQuality.MEDIUM,
        )

        with patch("os.path.exists", return_value=True), patch("os.path.getsize", return_value=1000):
            assert converter.convert(settings) is True

    @patch("ravn_app.core.downloader.YtDlpRunner.download")
    def test_pipeline_download_failure(self, mock_ytdlp_download, tmp_path):
        mock_ytdlp_download.return_value = RunnerResult(
            success=False,
            return_code=1,
            error_message="download failed",
        )

        downloader = YouTubeDownloader()
        dl_result = downloader.download(
            url="https://example.com/video",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
        )
        assert dl_result.success is False

