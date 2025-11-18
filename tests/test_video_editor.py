"""
VideoEditor testleri
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import subprocess

from ravn_app.core.converter import VideoEditor, AudioCodec


class TestVideoEditor:
    """VideoEditor sınıfı için testler"""

    def test_editor_initialization(self):
        """VideoEditor'ın başlatıldığını test et"""
        editor = VideoEditor()
        assert editor.ffmpeg_path == "ffmpeg"

        editor_custom = VideoEditor("/custom/path/ffmpeg")
        assert editor_custom.ffmpeg_path == "/custom/path/ffmpeg"

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_trim_success(self, mock_validate, mock_run):
        """Başarılı video kırpması test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)

        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "ffmpeg" in args
        assert "-ss" in args
        assert "10.0" in args
        assert "-t" in args
        assert "30.0" in args

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_trim_failure(self, mock_validate, mock_run):
        """Başarısız video kırpması test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        editor = VideoEditor()
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_trim_exception(self, mock_validate, mock_run):
        """Video kırpması sırasında istisna test edilir"""
        mock_validate.return_value = True
        mock_run.side_effect = Exception("Process error")

        editor = VideoEditor()
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_scale_success(self, mock_validate, mock_run):
        """Başarılı çözünürlük değiştirme test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.scale("input.mp4", "output.mp4", 1280, 720)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "scale=1280:720" in args

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_scale_failure(self, mock_validate, mock_run):
        """Başarısız çözünürlük değiştirme test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        editor = VideoEditor()
        result = editor.scale("input.mp4", "output.mp4", 1920, 1080)

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_extract_audio_success(self, mock_validate, mock_run):
        """Başarılı ses çıkartma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.extract_audio("input.mp4", "output.aac", AudioCodec.AAC)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "-vn" in args  # Video yok
        assert "-c:a" in args
        assert "aac" in args

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_extract_audio_different_codec(self, mock_validate, mock_run):
        """Farklı codec ile ses çıkartma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.extract_audio("input.mp4", "output.mp3", AudioCodec.MP3)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "libmp3lame" in args

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_extract_audio_failure(self, mock_validate, mock_run):
        """Başarısız ses çıkartma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        editor = VideoEditor()
        result = editor.extract_audio("input.mp4", "output.aac", AudioCodec.AAC)

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_create_gif_success(self, mock_validate, mock_run):
        """Başarılı GIF oluşturma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.create_gif("input.mp4", "output.gif", 0, 5, 10)

        assert result is True
        args = mock_run.call_args[0][0]
        assert "-ss" in args
        assert "0" in args
        assert "-t" in args
        assert "5" in args
        # fps parametresi -vf değerinin bir parçası olabilir
        vf_string = " ".join(args)
        assert "fps=10" in vf_string

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_create_gif_custom_params(self, mock_validate, mock_run):
        """Özel parametrelerle GIF oluşturma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()
        result = editor.create_gif("input.mp4", "output.gif", 10.5, 15.0, 15)

        assert result is True
        args = mock_run.call_args[0][0]
        # fps parametresi -vf değerinin bir parçası olabilir
        vf_string = " ".join(args)
        assert "fps=15" in vf_string

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_create_gif_failure(self, mock_validate, mock_run):
        """Başarısız GIF oluşturma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=1)

        editor = VideoEditor()
        result = editor.create_gif("input.mp4", "output.gif")

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_create_gif_exception(self, mock_validate, mock_run):
        """GIF oluşturması sırasında istisna test edilir"""
        mock_validate.return_value = True
        mock_run.side_effect = Exception("Process error")

        editor = VideoEditor()
        result = editor.create_gif("input.mp4", "output.gif")

        assert result is False

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_multiple_operations_sequence(self, mock_validate, mock_run):
        """Birbirini izleyen çeşitli işlemler test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()

        # Sırayla işlemler
        assert editor.trim("input.mp4", "trimmed.mp4", 5, 60) is True
        assert editor.scale("trimmed.mp4", "scaled.mp4", 1280, 720) is True
        assert editor.extract_audio("scaled.mp4", "audio.aac", AudioCodec.AAC) is True

        assert mock_run.call_count == 3

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_scale_boundary_values(self, mock_validate, mock_run):
        """Sınır değerler ile ölçeklendirme test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()

        # Minimum çözünürlük
        assert editor.scale("input.mp4", "output.mp4", 1, 1) is True

        # Maksimum çözünürlük
        assert editor.scale("input.mp4", "output.mp4", 7680, 4320) is True

        assert mock_run.call_count == 2

    @patch('subprocess.run')
    @patch('ravn_app.core.converter.VideoEditor._validate_files')
    def test_trim_boundary_values(self, mock_validate, mock_run):
        """Sınır değerler ile kırpma test edilir"""
        mock_validate.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        editor = VideoEditor()

        # Sıfır başlangıç
        assert editor.trim("input.mp4", "output.mp4", 0, 10) is True

        # Çok uzun videonun bir kısmı
        assert editor.trim("input.mp4", "output.mp4", 3600, 1800) is True

        assert mock_run.call_count == 2
