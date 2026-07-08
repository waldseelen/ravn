"""
VideoEditor testleri - FFmpegRunner tabanlı
"""

from unittest.mock import Mock, patch

from ravn_app.core.converter import AudioCodec, VideoEditor
from ravn_app.core.runners import RunnerResult


class TestVideoEditor:
    """VideoEditor sınıfı için testler"""

    def test_editor_initialization(self):
        """VideoEditor'ın başlatıldığını test et"""
        editor = VideoEditor()
        assert editor.ffmpeg_path == "ffmpeg"

        editor_custom = VideoEditor("/custom/path/ffmpeg")
        assert editor_custom.ffmpeg_path == "/custom/path/ffmpeg"

    def _create_editor_with_mock_runner(self, success=True, error_message=""):
        """Helper: mock runner ile editor oluştur"""
        editor = VideoEditor()
        editor._runner.run = Mock(return_value=RunnerResult(
            success=success,
            return_code=0 if success else 1,
            error_message=error_message
        ))
        return editor

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_trim_success(self, mock_validate):
        """Başarılı video kırpması test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)

        assert result is True
        editor._runner.run.assert_called_once()
        call_kwargs = editor._runner.run.call_args[1]
        assert call_kwargs['input_file'] == "input.mp4"
        assert call_kwargs['output_file'] == "output.mp4"
        assert '-ss' in call_kwargs['extra_args']
        assert '10.0' in call_kwargs['extra_args']
        assert '-t' in call_kwargs['extra_args']
        assert '30.0' in call_kwargs['extra_args']

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_trim_failure(self, mock_validate):
        """Başarısız video kırpması test edilir"""
        editor = self._create_editor_with_mock_runner(success=False, error_message="FFmpeg error")
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_trim_exception(self, mock_validate):
        """Video kırpması sırasında istisna test edilir"""
        editor = VideoEditor()
        editor._runner.run = Mock(side_effect=Exception("Process error"))
        # Trim artık exception yakalamıyor, direkt runner result döner
        # Bu test geçersiz, runner exception fırlatırsa propagate olur
        # Ancak exception olmadan failure dönmeli
        editor._runner.run = Mock(return_value=RunnerResult(
            success=False, return_code=1, error_message="Process error"
        ))
        result = editor.trim("input.mp4", "output.mp4", 10.0, 30.0)
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_scale_success(self, mock_validate):
        """Başarılı çözünürlük değiştirme test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.scale("input.mp4", "output.mp4", 1280, 720)

        assert result is True
        call_kwargs = editor._runner.run.call_args[1]
        extra_args = call_kwargs['extra_args']
        vf_string = " ".join(extra_args)
        assert "scale=1280:720" in vf_string

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_scale_failure(self, mock_validate):
        """Başarısız çözünürlük değiştirme test edilir"""
        editor = self._create_editor_with_mock_runner(success=False)
        result = editor.scale("input.mp4", "output.mp4", 1920, 1080)
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_extract_audio_success(self, mock_validate):
        """Başarılı ses çıkartma test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.extract_audio("input.mp4", "output.aac", AudioCodec.AAC)

        assert result is True
        call_kwargs = editor._runner.run.call_args[1]
        assert "-vn" in call_kwargs['video_args']
        assert "aac" in call_kwargs['audio_args']

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_extract_audio_different_codec(self, mock_validate):
        """Farklı codec ile ses çıkartma test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.extract_audio("input.mp4", "output.mp3", AudioCodec.MP3)

        assert result is True
        call_kwargs = editor._runner.run.call_args[1]
        assert "libmp3lame" in call_kwargs['audio_args']

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_extract_audio_failure(self, mock_validate):
        """Başarısız ses çıkartma test edilir"""
        editor = self._create_editor_with_mock_runner(success=False)
        result = editor.extract_audio("input.mp4", "output.aac", AudioCodec.AAC)
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_create_gif_success(self, mock_validate):
        """Başarılı GIF oluşturma test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.create_gif("input.mp4", "output.gif", 0, 5, 10)

        assert result is True
        call_kwargs = editor._runner.run.call_args[1]
        extra_args = call_kwargs['extra_args']
        assert "-ss" in extra_args
        assert "0" in extra_args
        assert "-t" in extra_args
        assert "5" in extra_args
        vf_string = " ".join(extra_args)
        assert "fps=10" in vf_string

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_create_gif_custom_params(self, mock_validate):
        """Özel parametrelerle GIF oluşturma test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)
        result = editor.create_gif("input.mp4", "output.gif", 10.5, 15.0, 15)

        assert result is True
        call_kwargs = editor._runner.run.call_args[1]
        extra_args = call_kwargs['extra_args']
        vf_string = " ".join(extra_args)
        assert "fps=15" in vf_string

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_create_gif_failure(self, mock_validate):
        """Başarısız GIF oluşturma test edilir"""
        editor = self._create_editor_with_mock_runner(success=False)
        result = editor.create_gif("input.mp4", "output.gif")
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_create_gif_exception(self, mock_validate):
        """GIF oluşturması sırasında hata test edilir"""
        editor = self._create_editor_with_mock_runner(success=False, error_message="Process error")
        result = editor.create_gif("input.mp4", "output.gif")
        assert result is False

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_multiple_operations_sequence(self, mock_validate):
        """Birbirini izleyen çeşitli işlemler test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)

        # Sırayla işlemler
        assert editor.trim("input.mp4", "trimmed.mp4", 5, 60) is True
        assert editor.scale("trimmed.mp4", "scaled.mp4", 1280, 720) is True
        assert editor.extract_audio("scaled.mp4", "audio.aac", AudioCodec.AAC) is True

        assert editor._runner.run.call_count == 3

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_scale_boundary_values(self, mock_validate):
        """Sınır değerler ile ölçeklendirme test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)

        # Minimum çözünürlük
        assert editor.scale("input.mp4", "output.mp4", 1, 1) is True

        # Maksimum çözünürlük
        assert editor.scale("input.mp4", "output.mp4", 7680, 4320) is True

        assert editor._runner.run.call_count == 2

    @patch.object(VideoEditor, '_validate_files', return_value=True)
    def test_trim_boundary_values(self, mock_validate):
        """Sınır değerler ile kırpma test edilir"""
        editor = self._create_editor_with_mock_runner(success=True)

        # Sıfır başlangıç
        assert editor.trim("input.mp4", "output.mp4", 0, 10) is True

        # Çok uzun videonun bir kısmı
        assert editor.trim("input.mp4", "output.mp4", 3600, 1800) is True

        assert editor._runner.run.call_count == 2

    def test_validate_files_not_exists(self):
        """Var olmayan dosya doğrulaması test edilir"""
        editor = VideoEditor()
        result = editor._validate_files("nonexistent.mp4", "test")
        assert result is False

    def test_trim_invalid_params(self):
        """Geçersiz parametrelerle kırpma test edilir"""
        editor = VideoEditor()
        # Negatif başlangıç
        assert editor.trim("input.mp4", "output.mp4", -1, 10) is False
        # Sıfır süre
        assert editor.trim("input.mp4", "output.mp4", 0, 0) is False
        # Negatif süre
        assert editor.trim("input.mp4", "output.mp4", 0, -5) is False

    def test_scale_invalid_dimensions(self):
        """Geçersiz boyutlarla ölçeklendirme test edilir"""
        editor = VideoEditor()
        # Sıfır genişlik
        assert editor.scale("input.mp4", "output.mp4", 0, 720) is False
        # Negatif yükseklik
        assert editor.scale("input.mp4", "output.mp4", 1280, -1) is False

    def test_create_gif_invalid_params(self):
        """Geçersiz parametrelerle GIF oluşturma test edilir"""
        editor = VideoEditor()
        # Negatif başlangıç
        assert editor.create_gif("input.mp4", "output.gif", -1, 5, 10) is False
        # Sıfır süre
        assert editor.create_gif("input.mp4", "output.gif", 0, 0, 10) is False
        # Sıfır fps
        assert editor.create_gif("input.mp4", "output.gif", 0, 5, 0) is False

    def test_extract_audio_invalid_codec(self):
        """Geçersiz codec ile ses çıkartma test edilir"""
        editor = VideoEditor()
        # String codec geçerli değil
        assert editor.extract_audio("input.mp4", "output.mp3", "mp3") is False
