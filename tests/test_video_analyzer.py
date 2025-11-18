"""
VideoAnalyzer testleri
"""

import pytest
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from ravn_app.core.converter import VideoAnalyzer, VideoInfo


class TestVideoInfo:
    """VideoInfo sınıfı için testler"""

    def test_video_info_initialization(self):
        """VideoInfo'nun düzgün şekilde başlatıldığını test et"""
        info = VideoInfo()

        assert info.filename == ""
        assert info.duration == 0
        assert info.width == 0
        assert info.height == 0
        assert info.fps == 0
        assert info.bitrate == 0
        assert info.video_codec == ""
        assert info.audio_codec == ""
        assert info.file_size == 0
        assert info.container == ""
        assert info.streams == []

    def test_get_display_info(self):
        """get_display_info() yöntemi test edilir"""
        info = VideoInfo()
        info.filename = "test.mp4"
        info.duration = 3661  # 1 saat 1 dakika 1 saniye
        info.width = 1920
        info.height = 1080
        info.fps = 30.0
        info.bitrate = 5000000
        info.video_codec = "h264"
        info.audio_codec = "aac"
        info.file_size = 500000000  # 500 MB
        info.container = "mp4"

        display_info = info.get_display_info()

        assert "test.mp4" in display_info
        assert "01:01:01" in display_info
        assert "1920x1080" in display_info
        assert "30.00" in display_info
        assert "h264" in display_info
        assert "aac" in display_info

    def test_format_duration(self):
        """Süre formatını test et"""
        assert VideoInfo._format_duration(0) == "00:00:00"
        assert VideoInfo._format_duration(61) == "00:01:01"
        assert VideoInfo._format_duration(3661) == "01:01:01"
        assert VideoInfo._format_duration(86399) == "23:59:59"

    def test_format_size(self):
        """Dosya boyutu formatını test et"""
        assert "B" in VideoInfo._format_size(512)
        assert "KB" in VideoInfo._format_size(1024)
        assert "MB" in VideoInfo._format_size(1024 * 1024)
        assert "GB" in VideoInfo._format_size(1024 * 1024 * 1024)


class TestVideoAnalyzer:
    """VideoAnalyzer sınıfı için testler"""

    def test_analyzer_initialization(self):
        """VideoAnalyzer'ın başlatıldığını test et"""
        analyzer = VideoAnalyzer()
        assert analyzer.ffprobe_path == "ffprobe"

        analyzer_custom = VideoAnalyzer("/custom/path/ffprobe")
        assert analyzer_custom.ffprobe_path == "/custom/path/ffprobe"

    def test_analyze_nonexistent_file(self):
        """Var olmayan dosya analiz edilirken None döndürüldüğü test edilir"""
        analyzer = VideoAnalyzer()
        result = analyzer.analyze("/nonexistent/file.mp4")
        assert result is None

    @patch('subprocess.run')
    def test_analyze_successful(self, mock_run):
        """Başarılı analiz test edilir"""
        # Mock ffprobe çıktısı
        mock_output = {
            "format": {
                "duration": "120.5",
                "bit_rate": "5000000",
                "size": "75000000",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "codec_name": "h264"
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac"
                }
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        analyzer = VideoAnalyzer()

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            result = analyzer.analyze(tmp.name)

            assert result is not None
            assert result.filename == Path(tmp.name).name
            assert result.duration == 120.5
            assert result.width == 1920
            assert result.height == 1080
            assert result.fps == 30.0
            assert result.bitrate == 5000000
            assert result.video_codec == "h264"
            assert result.audio_codec == "aac"

    @patch('subprocess.run')
    def test_analyze_ffprobe_error(self, mock_run):
        """FFprobe hatası durumunda None döndürüldüğü test edilir"""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        analyzer = VideoAnalyzer()

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            result = analyzer.analyze(tmp.name)
            assert result is None

    @patch('subprocess.run')
    def test_analyze_invalid_json(self, mock_run):
        """Geçersiz JSON çıktısı durumunda None döndürüldüğü test edilir"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="invalid json"
        )

        analyzer = VideoAnalyzer()

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            result = analyzer.analyze(tmp.name)
            assert result is None

    @patch('subprocess.run')
    def test_analyze_fps_fraction(self, mock_run):
        """FPS kesir formatında doğru şekilde hesaplandığı test edilir"""
        mock_output = {
            "format": {
                "duration": "60",
                "bit_rate": "4000000",
                "size": "30000000",
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2"
            },
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1280,
                    "height": 720,
                    "r_frame_rate": "24000/1001",  # 23.976 fps
                    "codec_name": "h265"
                }
            ]
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        analyzer = VideoAnalyzer()

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            result = analyzer.analyze(tmp.name)

            assert result is not None
            # 24000/1001 ≈ 23.976
            assert abs(result.fps - 23.976) < 0.01

    @patch('subprocess.run')
    def test_analyze_missing_streams(self, mock_run):
        """Eksik akış bilgisi durumunda test edilir"""
        mock_output = {
            "format": {
                "duration": "90",
                "bit_rate": "3000000",
                "size": "30000000"
            },
            "streams": []
        }

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(mock_output)
        )

        analyzer = VideoAnalyzer()

        with tempfile.NamedTemporaryFile(suffix='.mp4') as tmp:
            result = analyzer.analyze(tmp.name)

            assert result is not None
            assert result.width == 0
            assert result.height == 0
            assert result.video_codec == "unknown"
            assert result.audio_codec == "none"
