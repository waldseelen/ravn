"""
Video Converter Test Suit'i - Faz 1 (1.1, 1.2, 1.3)
"""


from ravn_app.core.converter import (
    AudioBitrate,
    AudioCodec,
    BatchConverter,
    CodecManager,
    ConversionSettings,
    VideoCodec,
    VideoConverter,
    VideoQuality,
)


class TestCodecManager:
    """CodecManager testleri"""

    def test_get_video_codec(self):
        """Video codec'i al"""
        assert CodecManager.get_video_codec('h264') == VideoCodec.H264
        assert CodecManager.get_video_codec('h265') == VideoCodec.H265
        assert CodecManager.get_video_codec('vp9') == VideoCodec.VP9
        assert CodecManager.get_video_codec('invalid') is None

    def test_get_audio_codec(self):
        """Ses codec'i al"""
        assert CodecManager.get_audio_codec('aac') == AudioCodec.AAC
        assert CodecManager.get_audio_codec('mp3') == AudioCodec.MP3
        assert CodecManager.get_audio_codec('opus') == AudioCodec.OPUS
        assert CodecManager.get_audio_codec('invalid') is None

    def test_get_default_codecs(self):
        """Format için varsayılan codec'leri al"""
        defaults = CodecManager.get_default_codecs('mp4')
        assert defaults['video'] == VideoCodec.H264
        assert defaults['audio'] == AudioCodec.AAC

        defaults = CodecManager.get_default_codecs('mkv')
        assert defaults['video'] == VideoCodec.H265
        assert defaults['audio'] == AudioCodec.AAC

        defaults = CodecManager.get_default_codecs('webm')
        assert defaults['video'] == VideoCodec.VP9
        assert defaults['audio'] == AudioCodec.OPUS

    def test_video_codec_properties(self):
        """Video codec özelliklerini kontrol et"""
        assert VideoCodec.H264.lib == "libx264"
        assert VideoCodec.H264.container == "mp4"
        assert VideoCodec.H265.lib == "libx265"
        assert VideoCodec.VP9.container == "webm"
        assert VideoCodec.AV1.lib == "libaom-av1"

    def test_audio_codec_properties(self):
        """Ses codec özelliklerini kontrol et"""
        assert AudioCodec.AAC.lib == "aac"
        assert AudioCodec.MP3.lib == "libmp3lame"
        assert AudioCodec.OPUS.lib == "libopus"
        assert AudioCodec.FLAC.container == "mkv"

    def test_video_codec_command(self):
        """Video codec komutunu test et"""
        cmd = CodecManager.get_video_codec_command(
            VideoCodec.H264,
            VideoQuality.HIGH
        )
        assert '-c:v' in cmd
        assert 'libx264' in cmd
        assert '-crf' in cmd
        assert str(VideoQuality.HIGH.value) in cmd

    def test_audio_codec_command(self):
        """Ses codec komutunu test et"""
        cmd = CodecManager.get_audio_codec_command(
            AudioCodec.AAC,
            AudioBitrate.MEDIUM
        )
        assert '-c:a' in cmd
        assert 'aac' in cmd

        cmd = CodecManager.get_audio_codec_command(
            AudioCodec.MP3,
            AudioBitrate.HIGH
        )
        assert '-c:a' in cmd
        assert 'libmp3lame' in cmd
        assert '-b:a' in cmd


class TestVideoQuality:
    """VideoQuality enum testleri"""

    def test_quality_values(self):
        """Kalite değerlerini kontrol et"""
        assert VideoQuality.LOSSLESS.value == 0
        assert VideoQuality.VERYHIGH.value == 18
        assert VideoQuality.HIGH.value == 23
        assert VideoQuality.MEDIUM.value == 28
        assert VideoQuality.LOW.value == 33
        assert VideoQuality.VERYLOW.value == 51

    def test_quality_ordering(self):
        """Kalite sırasını kontrol et"""
        qualities = [
            VideoQuality.LOSSLESS,
            VideoQuality.VERYHIGH,
            VideoQuality.HIGH,
            VideoQuality.MEDIUM,
            VideoQuality.LOW,
            VideoQuality.VERYLOW
        ]
        values = [q.value for q in qualities]
        assert values == sorted(values)  # Artan sırada


class TestAudioBitrate:
    """AudioBitrate enum testleri"""

    def test_bitrate_values(self):
        """Bitrate değerlerini kontrol et"""
        assert AudioBitrate.VERY_HIGH.value == "320k"
        assert AudioBitrate.HIGH.value == "192k"
        assert AudioBitrate.MEDIUM.value == "128k"
        assert AudioBitrate.LOW.value == "96k"
        assert AudioBitrate.VERYLOW.value == "64k"


class TestConversionSettings:
    """ConversionSettings testleri"""

    def test_creation(self):
        """Ayar nesnesi oluşturma"""
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mkv",
            video_codec=VideoCodec.H265,
            audio_codec=AudioCodec.AAC,
            video_quality=VideoQuality.HIGH,
            audio_bitrate=AudioBitrate.MEDIUM
        )

        assert settings.input_file == "input.mp4"
        assert settings.output_file == "output.mkv"
        assert settings.video_codec == VideoCodec.H265
        assert settings.audio_codec == AudioCodec.AAC
        assert settings.video_quality == VideoQuality.HIGH
        assert settings.audio_bitrate == AudioBitrate.MEDIUM
        assert settings.preset is None

    def test_with_advanced_options(self):
        """İleri seçeneklerle ayar"""
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.webm",
            video_codec=VideoCodec.VP9,
            audio_codec=AudioCodec.OPUS,
            preset="slow",
            two_pass=True,
            hardware_accel="nvenc",
            fps=24,
            scale=(1280, 720)
        )

        assert settings.preset == "slow"
        assert settings.two_pass is True
        assert settings.hardware_accel == "nvenc"
        assert settings.fps == 24
        assert settings.scale == (1280, 720)


class TestVideoConverter:
    """VideoConverter testleri"""

    def test_initialization(self):
        """Converter başlatma"""
        converter = VideoConverter()
        assert converter.is_running is False
        assert converter.current_process is None
        assert converter.progress == 0

    def test_build_command_basic(self):
        """Temel FFmpeg komutu oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mkv",
            video_codec=VideoCodec.H265,
            audio_codec=AudioCodec.AAC,
            video_quality=VideoQuality.HIGH
        )

        cmd = converter._build_command(settings)

        assert "ffmpeg" in cmd
        assert "-i" in cmd
        assert "input.mp4" in cmd
        assert "-c:v" in cmd
        assert "libx265" in cmd
        assert "-c:a" in cmd
        assert "aac" in cmd
        assert "-y" in cmd
        assert "output.mkv" in cmd

    def test_build_command_with_preset(self):
        """Preset ile komut oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            preset="fast"
        )

        cmd = converter._build_command(settings)
        assert "-preset" in cmd
        assert "fast" in cmd

    def test_build_command_with_scale(self):
        """Ölçeklendirme ile komut oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            scale=(1280, 720)
        )

        cmd = converter._build_command(settings)
        assert "-vf" in cmd
        assert "scale=1280:720" in cmd

    def test_build_command_with_fps(self):
        """FPS değişikliği ile komut oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            fps=24
        )

        cmd = converter._build_command(settings)
        assert "-r" in cmd
        assert "24" in cmd

    def test_build_command_audio_only(self):
        """Yalnızca ses modunda komut oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mp3",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.MP3,
            audio_only=True
        )

        cmd = converter._build_command(settings)
        assert "-vn" in cmd  # Video yok
        assert "-an" not in cmd

    def test_build_command_video_only(self):
        """Yalnızca video modunda komut oluşturma"""
        converter = VideoConverter()
        settings = ConversionSettings(
            input_file="input.mp4",
            output_file="output.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            video_only=True
        )

        cmd = converter._build_command(settings)
        assert "-an" in cmd  # Ses yok
        assert "-vn" not in cmd

    def test_status_callback(self):
        """Status callback testi"""
        converter = VideoConverter()
        messages = []

        def callback(msg):
            messages.append(msg)

        converter.set_status_callback(callback)
        converter._log("Test mesajı")

        assert len(messages) > 0
        assert "Test mesajı" in messages[0]


class TestBatchConverter:
    """BatchConverter testleri"""

    def test_initialization(self):
        """Batch converter başlatma"""
        converter = VideoConverter()
        batch = BatchConverter(converter)

        assert batch.converter is converter
        assert batch.max_workers == 1
        assert batch.queue.empty()
        assert batch.results == []
        assert batch.is_processing is False

    def test_add_files(self):
        """Dosyaları kuyruğa ekle"""
        converter = VideoConverter()
        batch = BatchConverter(converter)

        files = ["video1.mp4", "video2.mp4"]
        settings = ConversionSettings(
            input_file="dummy.mp4",
            output_file="dummy.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC
        )

        batch.add_files(files, settings)

        assert batch.queue.qsize() == 2

    def test_add_files_output_naming(self):
        """Çıkış dosyası otomatik adlandırması"""
        converter = VideoConverter()
        batch = BatchConverter(converter)

        files = ["video.mp4"]
        settings = ConversionSettings(
            input_file="dummy.mp4",
            output_file="dummy.mp4",
            video_codec=VideoCodec.VP9,  # container: webm
            audio_codec=AudioCodec.OPUS
        )

        batch.add_files(files, settings)

        queued_settings = batch.queue.get()
        assert queued_settings.output_file.endswith(".webm")

    def test_results_structure(self):
        """Sonuç yapısını kontrol et"""
        converter = VideoConverter()
        batch = BatchConverter(converter)

        # Boş kuyruk ile process
        results = batch.process()

        assert 'total' in results
        assert 'successful' in results
        assert 'failed' in results
        assert 'results' in results
        assert results['total'] == 0


class TestVideoCodecEnum:
    """VideoCodec enum testleri"""

    def test_all_codecs_have_properties(self):
        """Tüm codec'lerin özelliklerine sahip olduğunu kontrol et"""
        for codec in VideoCodec:
            assert codec.lib is not None
            assert codec.container is not None
            assert codec.default_preset is not None
            assert isinstance(codec.lib, str)
            assert isinstance(codec.container, str)
            assert isinstance(codec.default_preset, str)


class TestAudioCodecEnum:
    """AudioCodec enum testleri"""

    def test_all_codecs_have_properties(self):
        """Tüm ses codec'lerinin özelliklerine sahip olduğunu kontrol et"""
        for codec in AudioCodec:
            assert codec.lib is not None
            assert codec.container is not None
            assert isinstance(codec.lib, str)
            assert isinstance(codec.container, str)


class TestConverterIntegration:
    """Entegrasyon testleri"""

    def test_codec_manager_integration(self):
        """CodecManager ve Converter entegrasyonu"""
        converter = VideoConverter()
        video_codec = CodecManager.get_video_codec('h264')
        audio_codec = CodecManager.get_audio_codec('aac')

        settings = ConversionSettings(
            input_file="test.mp4",
            output_file="output.mp4",
            video_codec=video_codec,
            audio_codec=audio_codec,
            video_quality=VideoQuality.HIGH
        )

        cmd = converter._build_command(settings)

        # Komut geçerli olmalı
        assert isinstance(cmd, list)
        assert len(cmd) > 0
        assert "ffmpeg" in cmd

    def test_batch_converter_with_multiple_files(self):
        """Batch converter çoklu dosya testi"""
        from unittest.mock import Mock, patch

        from ravn_app.core.runners import RunnerResult

        converter = VideoConverter()
        # Mock the runner to avoid actual file processing
        converter._runner.run = Mock(return_value=RunnerResult(
            success=True, return_code=0
        ))

        batch = BatchConverter(converter, max_workers=1)

        files = [
            "video1.mp4",
            "video2.mp4",
            "video3.avi"
        ]

        settings = ConversionSettings(
            input_file="dummy.mp4",
            output_file="dummy.mp4",
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC
        )

        batch.add_files(files, settings)

        assert batch.queue.qsize() == 3

        # Mock os.path.exists and os.path.getsize for file validation
        with patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1000):
            results = batch.process()

        assert results['total'] == 3
        assert len(results['results']) == 3
        assert results['successful'] == 3
