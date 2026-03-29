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
from ravn_app.core.runners import RunnerResult, RunnerStatus


class TestAudioNormalizer:
    """AudioNormalizer sınıfı için testler"""

    def _create_mock_result(self, success=True, stdout="", stderr="", metadata=None):
        """Helper to create RunnerResult for mocking"""
        return RunnerResult(
            success=success,
            return_code=0 if success else 1,
            stdout=stdout,
            stderr=stderr,
            error_message="" if success else "Process failed",
            duration_seconds=0.1,
            metadata=metadata or {}
        )

    def test_normalizer_initialization(self):
        """AudioNormalizer'ın başlatıldığını test et"""
        normalizer = AudioNormalizer()
        assert normalizer.ffmpeg_path == "ffmpeg"
        assert normalizer.ffprobe_path == "ffprobe"

        normalizer_custom = AudioNormalizer("/custom/ffmpeg", "/custom/ffprobe")
        assert normalizer_custom.ffmpeg_path == "/custom/ffmpeg"
        assert normalizer_custom.ffprobe_path == "/custom/ffprobe"

    @patch('os.path.exists')
    def test_analyze_loudness_success(self, mock_exists):
        """Başarılı LUFS analizi test edilir"""
        mock_exists.return_value = True
        
        normalizer = AudioNormalizer()
        probe_result = self._create_mock_result(
            success=True,
            metadata={'probe_data': {'format': {'duration': '120.5'}}}
        )
        
        with patch.object(normalizer._runner, 'probe', return_value=probe_result):
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

    @patch('os.path.exists')
    def test_normalize_success(self, mock_exists):
        """Başarılı normalizasyon test edilir"""
        mock_exists.return_value = True

        normalizer = AudioNormalizer()
        mock_result = self._create_mock_result(success=True)
        
        settings = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output.mp3",
            target_loudness=-23.0,
            method="loudnorm"
        )

        with patch.object(normalizer._runner, 'run', return_value=mock_result):
            result = normalizer.normalize(settings)
        
        assert result is True

    @patch('os.path.exists')
    def test_normalize_with_compression(self, mock_exists):
        """Sıkıştırma ile normalizasyon test edilir"""
        mock_exists.return_value = True

        normalizer = AudioNormalizer()
        mock_result = self._create_mock_result(success=True)
        
        settings = AudioNormalizationSettings(
            input_file="input.mp3",
            output_file="output.mp3",
            enable_compression=True,
            method="loudnorm"
        )

        with patch.object(normalizer._runner, 'run', return_value=mock_result):
            result = normalizer.normalize(settings)
        
        assert result is True

    @patch('os.path.exists')
    def test_normalize_different_methods(self, mock_exists):
        """Farklı normalizasyon yöntemleri test edilir"""
        mock_exists.return_value = True

        normalizer = AudioNormalizer()
        mock_result = self._create_mock_result(success=True)

        with patch.object(normalizer._runner, 'run', return_value=mock_result):
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

    def _create_mock_result(self, success=True, stdout="", stderr="", metadata=None):
        """Helper to create RunnerResult for mocking"""
        return RunnerResult(
            success=success,
            return_code=0 if success else 1,
            stdout=stdout,
            stderr=stderr,
            error_message="" if success else "Process failed",
            duration_seconds=0.1,
            metadata=metadata or {}
        )

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

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_merge_success(self, mock_exists, mock_open):
        """Başarılı video birleştirmesi test edilir"""
        mock_exists.return_value = True

        merger = VideoMerger()
        mock_result = self._create_mock_result(success=True)
        
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4"
        )

        with patch.object(merger._runner, 'run_raw', return_value=mock_result):
            result = merger.merge(settings)
        
        assert result is True

    @patch('os.path.exists')
    def test_merge_with_progress(self, mock_exists):
        """Progress callback ile birleştirme test edilir"""
        mock_exists.return_value = True

        progress_updates = []

        def progress_callback(progress, status):
            progress_updates.append((progress, status))

        merger = VideoMerger()
        mock_result = self._create_mock_result(success=True)
        
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4"
        )

        with patch.object(merger._runner, 'run_raw', return_value=mock_result):
            with patch('builtins.open', create=True):
                result = merger.merge(settings, progress_callback)

        assert result is True
        # En az 2 progress update yapılmalı
        assert len(progress_updates) >= 2

    @patch('builtins.open', create=True)
    @patch('os.path.exists')
    def test_merge_with_transitions(self, mock_exists, mock_open):
        """Geçişli birleştirme test edilir"""
        mock_exists.return_value = True

        merger = VideoMerger()
        mock_result = self._create_mock_result(success=True)
        
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4",
            transition_duration=1.0
        )

        with patch.object(merger._runner, 'run_raw', return_value=mock_result):
            result = merger.merge_with_transitions(settings)
        
        assert result is True

    @patch('os.path.exists')
    def test_merge_multiple_videos(self, mock_exists):
        """Çoklu video birleştirmesi test edilir"""
        mock_exists.return_value = True

        merger = VideoMerger()
        mock_result = self._create_mock_result(success=True)
        
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4", "video3.mp4", "video4.mp4"],
            output_file="merged.mp4"
        )

        with patch.object(merger._runner, 'run_raw', return_value=mock_result):
            result = merger.merge_with_transitions(settings)
        
        assert result is True

    @patch('os.path.exists')
    def test_merge_no_transitions(self, mock_exists):
        """Geçiş olmadan birleştirme test edilir"""
        mock_exists.return_value = True

        merger = VideoMerger()
        mock_result = self._create_mock_result(success=True)
        
        settings = VideoMergeSettings(
            input_files=["video1.mp4", "video2.mp4"],
            output_file="merged.mp4",
            transition_duration=0.0  # Geçiş yok
        )

        with patch.object(merger._runner, 'run_raw', return_value=mock_result):
            with patch('builtins.open', create=True):
                result = merger.merge_with_transitions(settings)
        
        assert result is True
