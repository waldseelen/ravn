"""
AudioNormalizer ve VideoMerger testleri
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import subprocess

from ravn_app.core.audio_normalizer import (
    AudioNormalizer, VideoMerger, AudioNormalizationSettings,
    VideoMergeSettings
)


class TestAudioNormalizer:
    """AudioNormalizer sınıfı için testler"""

    def test_normalizer_initialization(self):
        """AudioNormalizer'ın başlatıldığını test et"""
        normalizer = AudioNormalizer()
        assert normalizer.ffmpeg_path == "ffmpeg"
        assert normalizer.ffprobe_path == "ffprobe"

        normalizer_custom = AudioNormalizer("/custom/ffmpeg", "/custom/ffprobe")
        assert normalizer_custom.ffmpeg_path == "/custom/ffmpeg"
        assert normalizer_custom.ffprobe_path == "/custom/ffprobe"

    @patch('subprocess.run')
    @patch('os.path.exists')
    def test_analyze_loudness_success(self, mock_exists, mock_run):
        """Başarılı LUFS analizi test edilir"""
        mock_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        normalizer = AudioNormalizer()
        result = normalizer.analyze_loudness("test.mp3")

        assert result is not None
        assert result["status"] == "analyzed"

    @patch('os.path.exists')
    def test_analyze_loudness_file_not_found(self, mock_exists):
        """Dosya bulunamadı test edilir"""
        mock_exists.return_value = False

        normalizer = AudioNormalizer()
        result = normalizer.analyze_loudness("nonexistent.mp3")

        assert result is None

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_normalize_success(self, mock_exists, mock_popen):
        """Başarılı normalizasyon test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        normalizer = AudioNormalizer()
        settings = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output.mp3",
            target_loudness=-23.0,
            method="loudnorm"
        )

        result = normalizer.normalize(settings)
        assert result is True
        mock_popen.assert_called_once()

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_normalize_with_compression(self, mock_exists, mock_popen):
        """Sıkıştırma ile normalizasyon test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        normalizer = AudioNormalizer()
        settings = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output.mp3",
            enable_compression=True,
            method="loudnorm"
        )

        result = normalizer.normalize(settings)
        assert result is True

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_normalize_different_methods(self, mock_exists, mock_popen):
        """Farklı normalizasyon yöntemleri test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        normalizer = AudioNormalizer()

        # loudnorm yöntemi
        settings1 = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output1.mp3",
            method="loudnorm"
        )
        assert normalizer.normalize(settings1) is True

        # dynaudnorm yöntemi
        settings2 = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output2.mp3",
            method="dynaudnorm"
        )
        assert normalizer.normalize(settings2) is True

        # volume yöntemi
        settings3 = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output3.mp3",
            method="volume"
        )
        assert normalizer.normalize(settings3) is True


class TestVideoMerger:
    """VideoMerger sınıfı için testler"""

    def test_merger_initialization(self):
        """VideoMerger'ın başlatıldığını test et"""
        merger = VideoMerger()
        assert merger.ffmpeg_path == "ffmpeg"

        merger_custom = VideoMerger("/custom/ffmpeg")
        assert merger_custom.ffmpeg_path == "/custom/ffmpeg"

    @patch('os.path.exists')
    def test_merge_file_not_found(self, mock_exists):
        """Dosya bulunamadı test edilir"""
        mock_exists.return_value = False

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4"
        )

        result = merger.merge(settings)
        assert result is False

    @patch('os.path.exists')
    def test_merge_insufficient_files(self, mock_exists):
        """Yetersiz dosya test edilir"""
        mock_exists.return_value = True

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4"],  # Sadece 1 dosya
            output_file="merged.mp4"
        )

        result = merger.merge(settings)
        assert result is False

    @patch('subprocess.Popen')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_merge_success(self, mock_exists, mock_open, mock_popen):
        """Başarılı video birleştirmesi test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4"
        )

        result = merger.merge(settings)
        assert result is True

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_merge_with_progress(self, mock_exists, mock_popen):
        """Progress callback ile birleştirme test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        progress_updates = []

        def progress_callback(progress, status):
            progress_updates.append((progress, status))

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4"
        )

        result = merger.merge(settings, progress_callback)

        assert result is True
        # En az 2 progress update yapılmalı
        assert len(progress_updates) >= 2

    @patch('subprocess.Popen')
    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_merge_with_transitions(self, mock_exists, mock_open, mock_popen):
        """Geçişli birleştirme test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4",
            transition_duration=1.0
        )

        result = merger.merge_with_transitions(settings)
        assert result is True

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_merge_multiple_videos(self, mock_exists, mock_popen):
        """Çoklu video birleştirmesi test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4", "video3.mp4", "video4.mp4"],
            output_file="merged.mp4"
        )

        result = merger.merge_with_transitions(settings)
        assert result is True

    @patch('subprocess.Popen')
    @patch('os.path.exists')
    def test_merge_no_transitions(self, mock_exists, mock_popen):
        """Geçiş olmadan birleştirme test edilir"""
        mock_exists.return_value = True
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        merger = VideoMerger()
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4",
            transition_duration=0.0  # Geçiş yok
        )

        result = merger.merge_with_transitions(settings)
        assert result is True
