"""
Video format dönüştürme modülü - Faz 1: Video Converter
Desteklenen formatlar: MP4, MKV, AVI, MOV, WEBM, FLV
Desteklenen codec'ler: H.264, H.265, VP8, VP9, AV1 (video), AAC, MP3, Opus, Vorbis, FLAC (audio)
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
from threading import Thread
import queue
import logging

from ravn_app.core.runners import FFmpegRunner, RunnerResult, RunnerStatus


# Logging konfigürasyonu
logger = logging.getLogger(__name__)


# Özel Exception Sınıfları
class ConversionException(Exception):
    """Dönüştürme işlemi sırasında temel istisna"""
    pass


class InvalidFileException(ConversionException):
    """Geçersiz video dosyası"""
    pass


class CodecException(ConversionException):
    """Codec ile ilgili hata"""
    pass


class FFmpegException(ConversionException):
    """FFmpeg ile ilgili hata"""
    pass


class VideoCodec(Enum):
    """Desteklenen video codec'leri"""
    H264 = ("libx264", "mp4", "fast")
    H265 = ("libx265", "mp4", "medium")
    VP8 = ("libvpx", "webm", "slow")
    VP9 = ("libvpx-vp9", "webm", "slow")
    AV1 = ("libaom-av1", "mkv", "very_slow")

    def __init__(self, lib: str, container: str, default_preset: str):
        self.lib = lib
        self.container = container
        self.default_preset = default_preset


class AudioCodec(Enum):
    """Desteklenen ses codec'leri"""
    AAC = ("aac", "mp4")
    MP3 = ("libmp3lame", "mp3")
    OPUS = ("libopus", "webm")
    VORBIS = ("libvorbis", "webm")
    FLAC = ("flac", "mkv")

    def __init__(self, lib: str, container: str):
        self.lib = lib
        self.container = container


class VideoQuality(Enum):
    """Video kalite seviyeleri (CRF değerleri)"""
    LOSSLESS = 0      # Kayıpsız (H.264/H.265)
    VERYHIGH = 18     # Çok yüksek (varsayılan YouTube)
    HIGH = 23         # Yüksek
    MEDIUM = 28       # Orta
    LOW = 33          # Düşük
    VERYLOW = 51      # Çok düşük


class AudioBitrate(Enum):
    """Ses bitrate seviyeleri"""
    VERY_HIGH = "320k"
    HIGH = "192k"
    MEDIUM = "128k"
    LOW = "96k"
    VERYLOW = "64k"


@dataclass
class ConversionSettings:
    """Dönüştürme ayarları"""
    input_file: str
    output_file: str
    video_codec: VideoCodec
    audio_codec: AudioCodec
    video_quality: VideoQuality = VideoQuality.HIGH
    audio_bitrate: AudioBitrate = AudioBitrate.MEDIUM
    preset: Optional[str] = None  # fast, medium, slow
    bitrate_mode: str = "crf"  # crf, cbr, vbr
    two_pass: bool = False
    hardware_accel: Optional[str] = None  # nvenc, quicksync, none
    fps: Optional[int] = None  # Değiştirme yapılmayacaksa None
    scale: Optional[Tuple[int, int]] = None  # (width, height)
    audio_only: bool = False
    video_only: bool = False


class CodecManager:
    """Codec'ler ve FFmpeg parametrelerini yönet"""

    # Desteklenen video codec'leri
    VIDEO_CODECS = {
        'h264': VideoCodec.H264,
        'h265': VideoCodec.H265,
        'hevc': VideoCodec.H265,
        'vp8': VideoCodec.VP8,
        'vp9': VideoCodec.VP9,
        'av1': VideoCodec.AV1,
    }

    # Desteklenen ses codec'leri
    AUDIO_CODECS = {
        'aac': AudioCodec.AAC,
        'mp3': AudioCodec.MP3,
        'opus': AudioCodec.OPUS,
        'vorbis': AudioCodec.VORBIS,
        'flac': AudioCodec.FLAC,
    }

    # Format -> Varsayılan Codec
    FORMAT_DEFAULTS = {
        'mp4': {'video': VideoCodec.H264, 'audio': AudioCodec.AAC},
        'mkv': {'video': VideoCodec.H265, 'audio': AudioCodec.AAC},
        'webm': {'video': VideoCodec.VP9, 'audio': AudioCodec.OPUS},
        'avi': {'video': VideoCodec.H264, 'audio': AudioCodec.MP3},
        'mov': {'video': VideoCodec.H264, 'audio': AudioCodec.AAC},
        'flv': {'video': VideoCodec.H264, 'audio': AudioCodec.MP3},
    }

    @staticmethod
    def get_video_codec(codec_name: str) -> Optional[VideoCodec]:
        """Video codec'i al"""
        return CodecManager.VIDEO_CODECS.get(codec_name.lower())

    @staticmethod
    def get_audio_codec(codec_name: str) -> Optional[AudioCodec]:
        """Ses codec'i al"""
        return CodecManager.AUDIO_CODECS.get(codec_name.lower())

    @staticmethod
    def get_default_codecs(format_ext: str) -> Dict:
        """Format için varsayılan codec'leri al"""
        return CodecManager.FORMAT_DEFAULTS.get(format_ext.lower(), {
            'video': VideoCodec.H264,
            'audio': AudioCodec.AAC
        })

    @staticmethod
    def get_video_codec_command(codec: VideoCodec, quality: VideoQuality,
                               preset: Optional[str] = None) -> List[str]:
        """Video codec FFmpeg parametrelerini döndür"""
        preset = preset or codec.default_preset
        cmd = ['-c:v', codec.lib]

        if codec in [VideoCodec.H264, VideoCodec.H265]:
            cmd.extend(['-preset', preset, '-crf', str(quality.value)])
        elif codec == VideoCodec.VP8:
            cmd.extend(['-deadline', preset, '-crf', str(quality.value)])
        elif codec == VideoCodec.VP9:
            cmd.extend(['-deadline', preset, '-crf', str(quality.value)])
        elif codec == VideoCodec.AV1:
            cmd.extend(['-cpu-used', str(8 if preset == 'very_slow' else 4)])

        return cmd

    @staticmethod
    def get_audio_codec_command(codec: AudioCodec, bitrate: AudioBitrate) -> List[str]:
        """Ses codec FFmpeg parametrelerini döndür"""
        cmd = ['-c:a', codec.lib]

        if codec == AudioCodec.AAC:
            cmd.extend(['-q:a', '2'])  # Kalite
        elif codec == AudioCodec.MP3:
            cmd.extend(['-b:a', bitrate.value])
        elif codec == AudioCodec.OPUS:
            cmd.extend(['-b:a', bitrate.value])
        elif codec == AudioCodec.VORBIS:
            cmd.extend(['-q:a', '6'])  # Kalite (0-10)
        elif codec == AudioCodec.FLAC:
            cmd.extend(['-compression_level', '8'])

        return cmd


class VideoConverter:
    """Video format dönüştürücü - FFmpegRunner üzerinden çalışır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """
        VideoConverter'ı başlat

        Args:
            ffmpeg_path (str): FFmpeg yürütülebilir dosyasının yolu
            ffprobe_path (str): FFprobe yürütülebilir dosyasının yolu
        """
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)
        self.is_running = False
        self.progress = 0
        self.status_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[float, str], None]] = None

    @property
    def current_process(self):
        """Backwards compatibility: access runner's current process"""
        return self._runner.current_process

    def set_status_callback(self, callback: Optional[Callable[[str], None]]):
        """İlerleme güncellemeleri için callback ayarla"""
        self.status_callback = callback

    def set_progress_callback(self, callback: Optional[Callable[[float, str], None]]):
        """İlerleme yüzdesini güncellemek için callback ayarla

        Callback fonksiyonu şu parametrelerle çağırılır:
        - progress: 0-100 arası yüzde
        - status: Durumu tanımlayan string
        """
        self.progress_callback = callback

    def _log(self, message: str, level: str = "info"):
        """Günlük mesajı yazdır"""
        if self.status_callback:
            self.status_callback(f"[{level.upper()}] {message}")
        else:
            log_func = getattr(logger, level, logger.info)
            log_func(message)

    def _update_progress(self, progress: float, status: str = ""):
        """İlerleme güncellemesi yap"""
        self.progress = min(100, max(0, progress))
        if self.progress_callback:
            self.progress_callback(self.progress, status)

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Dosya boyutunu insan okunur formata çevir"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} TB"

    def convert(self, settings: ConversionSettings) -> bool:
        """
        Videoyu dönüştür - FFmpegRunner kullanır

        Args:
            settings (ConversionSettings): Dönüştürme ayarları

        Returns:
            bool: Başarılı ise True

        Raises:
            InvalidFileException: Giriş dosyası geçersizse
            CodecException: Codec geçersizse
            FFmpegException: FFmpeg hatası oluşursa
        """
        try:
            self.is_running = True
            self._update_progress(0, "Başlangıç")

            # Giriş dosyasını kontrol et
            if not os.path.exists(settings.input_file):
                error_msg = f"Giriş dosyası bulunamadı: {settings.input_file}"
                self._log(error_msg, "error")
                self._update_progress(0, "Hata: Dosya bulunamadı")
                raise InvalidFileException(error_msg)

            # Dosya boyutu kontrol et
            file_size = os.path.getsize(settings.input_file)
            if file_size == 0:
                error_msg = f"Giriş dosyası boş: {settings.input_file}"
                self._log(error_msg, "error")
                self._update_progress(0, "Hata: Dosya boş")
                raise InvalidFileException(error_msg)

            # Codec doğrulaması
            if not isinstance(settings.video_codec, VideoCodec):
                error_msg = f"Geçersiz video codec: {settings.video_codec}"
                self._log(error_msg, "error")
                self._update_progress(0, "Hata: Geçersiz codec")
                raise CodecException(error_msg)

            if not isinstance(settings.audio_codec, AudioCodec):
                error_msg = f"Geçersiz ses codec: {settings.audio_codec}"
                self._log(error_msg, "error")
                self._update_progress(0, "Hata: Geçersiz codec")
                raise CodecException(error_msg)

            self._log(f"Dönüştürme başlanıyor: {settings.input_file}")
            self._log(f"Format: {settings.video_codec.name} / {settings.audio_codec.name}")
            self._log(f"Giriş dosyası boyutu: {self._format_size(file_size)}")
            self._update_progress(5, "Hazırlanıyor...")

            # Video ve ses argümanlarını hazırla
            video_args, audio_args = self._build_codec_args(settings)
            extra_args = self._build_extra_args(settings)

            self._update_progress(10, "Dönüştürme işlemi başladı...")

            # FFmpegRunner kullanarak çalıştır (gerçek zamanlı ilerleme ile)
            result = self._runner.run(
                input_file=settings.input_file,
                output_file=settings.output_file,
                video_args=video_args,
                audio_args=audio_args,
                extra_args=extra_args,
                progress_callback=self.progress_callback,
                use_realtime_progress=True  # Gerçek zamanlı ilerleme aktif
            )

            if result.success:
                output_size = result.metadata.get('output_size', 0)
                self._log(f"Dönüştürme tamamlandı: {settings.output_file}", "success")
                self._log(f"Çıkış dosyası boyutu: {self._format_size(output_size)}", "success")
                compression_ratio = (1 - output_size / file_size) * 100 if file_size > 0 else 0
                self._log(f"Sıkıştırma oranı: {compression_ratio:.1f}%", "success")
                self._update_progress(100, "Tamamlandı!")
                self.is_running = False
                return True
            else:
                error_msg = f"FFmpeg hatası: {result.error_message}"
                self._log(error_msg, "error")
                self._update_progress(0, "Hata oluştu")
                raise FFmpegException(error_msg)

        except ConversionException:
            self.is_running = False
            raise
        except Exception as e:
            error_msg = f"Beklenmeyen hata: {type(e).__name__}: {str(e)}"
            self._log(error_msg, "error")
            logger.exception("Dönüştürme işleminde beklenmeyen hata")
            self.is_running = False
            return False

    def _build_codec_args(self, settings: ConversionSettings) -> Tuple[List[str], List[str]]:
        """Video ve ses codec argümanlarını oluştur"""
        video_args = []
        audio_args = []

        # Video codec
        if not settings.audio_only:
            video_args = CodecManager.get_video_codec_command(
                settings.video_codec,
                settings.video_quality,
                settings.preset
            )
        else:
            video_args = ['-vn']

        # Ses codec
        if not settings.video_only:
            audio_args = CodecManager.get_audio_codec_command(
                settings.audio_codec,
                settings.audio_bitrate
            )
        else:
            audio_args = ['-an']

        return video_args, audio_args

    def _build_extra_args(self, settings: ConversionSettings) -> List[str]:
        """Ek FFmpeg argümanlarını oluştur"""
        extra_args = []

        # FPS değiştirme
        if settings.fps and not settings.audio_only:
            extra_args.extend(['-r', str(settings.fps)])

        # Çözünürlük değiştirme
        if settings.scale and not settings.audio_only:
            width, height = settings.scale
            extra_args.extend(['-vf', f'scale={width}:{height}'])

        # Hardware acceleration
        if settings.hardware_accel and settings.hardware_accel != 'none':
            extra_args.extend(['-hwaccel', settings.hardware_accel])

        return extra_args

    def _build_command(self, settings: ConversionSettings) -> List[str]:
        """FFmpeg komutunu oluştur (legacy/backwards compatibility)"""
        cmd = [self.ffmpeg_path, '-i', settings.input_file]

        video_args, audio_args = self._build_codec_args(settings)
        extra_args = self._build_extra_args(settings)

        cmd.extend(video_args)
        cmd.extend(audio_args)
        cmd.extend(extra_args)
        cmd.extend(['-y', settings.output_file])

        return cmd

    def stop(self):
        """Dönüştürmeyi durdur"""
        cancelled = self._runner.cancel()
        self.is_running = False
        if cancelled:
            self._log("Dönüştürme durduruldu", "warning")


class BatchConverter:
    """Toplu dönüştürme yöneticisi"""

    def __init__(self, converter: VideoConverter, max_workers: int = 1):
        """
        BatchConverter'ı başlat

        Args:
            converter (VideoConverter): Kullanılacak converter
            max_workers (int): Eşzamanlı işçi sayısı (1 = sırasız)
        """
        self.converter = converter
        self.max_workers = max_workers
        self.queue = queue.Queue()
        self.results = []
        self.is_processing = False

    def add_files(self, files: List[str], settings_template: ConversionSettings):
        """
        Dönüştürme kuyruğuna dosya ekle

        Args:
            files (List[str]): İşlenecek dosyaların listesi
            settings_template (ConversionSettings): Ayarlar şablonu
        """
        for file in files:
            # Çıkış dosyasını adlandır
            input_path = Path(file)
            output_ext = settings_template.video_codec.container
            output_file = str(input_path.with_suffix(f'.{output_ext}'))

            # Ayarları klonla
            settings = ConversionSettings(
                input_file=file,
                output_file=output_file,
                video_codec=settings_template.video_codec,
                audio_codec=settings_template.audio_codec,
                video_quality=settings_template.video_quality,
                audio_bitrate=settings_template.audio_bitrate,
                preset=settings_template.preset,
                fps=settings_template.fps,
                scale=settings_template.scale
            )

            self.queue.put(settings)

    def process(self, progress_callback=None) -> Dict:
        """
        Kuyruktaki tüm dosyaları işle

        Args:
            progress_callback: İlerleme callback'i

        Returns:
            Dict: İşlem sonuçları
        """
        self.is_processing = True
        self.results = []
        total = self.queue.qsize()
        processed = 0

        while not self.queue.empty() and self.is_processing:
            settings = self.queue.get()

            if progress_callback:
                progress_callback(f"İşleniyor: {processed + 1}/{total}")

            success = self.converter.convert(settings)
            self.results.append({
                'input': settings.input_file,
                'output': settings.output_file,
                'success': success
            })

            processed += 1

        self.is_processing = False

        return {
            'total': total,
            'successful': sum(1 for r in self.results if r['success']),
            'failed': sum(1 for r in self.results if not r['success']),
            'results': self.results
        }

    def cancel(self):
        """İşlemi iptal et"""
        self.is_processing = False
        self.converter.stop()


# ===== FAZ 2: Video Analiz ve Gelişmiş Özellikler =====

class VideoInfo:
    """Video dosya bilgileri"""

    def __init__(self):
        self.filename: str = ""
        self.duration: float = 0
        self.width: int = 0
        self.height: int = 0
        self.fps: float = 0
        self.bitrate: int = 0
        self.video_codec: str = ""
        self.audio_codec: str = ""
        self.file_size: int = 0
        self.container: str = ""
        self.streams: List[Dict] = []

    def get_display_info(self) -> str:
        """Görüntülenebilir bilgiler döndür"""
        return f"""
📊 Video Bilgileri:
  Dosya: {self.filename}
  Süre: {self._format_duration(self.duration)}
  Çözünürlük: {self.width}x{self.height}
  FPS: {self.fps:.2f}
  Video Codec: {self.video_codec}
  Ses Codec: {self.audio_codec}
  Bitrate: {self.bitrate / 1000:.0f} kbps
  Boyut: {self._format_size(self.file_size)}
  Konteyner: {self.container}
"""

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Süreyi HH:MM:SS formatına çevir"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _format_size(bytes_size: int) -> str:
        """Boyutu insan okunur formata çevir"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.2f} TB"


class VideoAnalyzer:
    """Video dosyalarını analiz etme motoru - FFmpegRunner kullanır"""

    def __init__(self, ffprobe_path: str = "ffprobe", ffmpeg_path: str = "ffmpeg"):
        """VideoAnalyzer'ı başlat"""
        self.ffprobe_path = ffprobe_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)

    def analyze(self, file_path: str) -> Optional[VideoInfo]:
        """Video dosyasını analiz et"""
        if not os.path.exists(file_path):
            return None

        try:
            # FFmpegRunner probe metodu kullan
            data = self._runner.probe(file_path)
            if data is None:
                return None

            format_info = data.get('format', {})
            streams = data.get('streams', [])

            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), {})
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), {})

            fps_str = video_stream.get('r_frame_rate', '30/1')
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                fps = num / den if den else 30
            else:
                fps = float(fps_str) if fps_str else 30

            info = VideoInfo()
            info.filename = os.path.basename(file_path)
            info.duration = float(format_info.get('duration', 0))
            info.width = video_stream.get('width', 0)
            info.height = video_stream.get('height', 0)
            info.fps = fps
            info.bitrate = int(format_info.get('bit_rate', 0))
            info.video_codec = video_stream.get('codec_name', 'unknown')
            info.audio_codec = audio_stream.get('codec_name', 'none')
            info.file_size = int(format_info.get('size', 0))
            info.container = os.path.splitext(file_path)[1][1:]
            info.streams = streams

            return info
        except Exception as e:
            logger.error(f"Analiz hatası: {e}")
            return None


class VideoEditor:
    """Gelişmiş video düzenleme işlemleri - FFmpegRunner kullanır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """VideoEditor'ı başlat"""
        self.ffmpeg_path = ffmpeg_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)
        logger.info(f"VideoEditor başlatıldı: {ffmpeg_path}")

    def _validate_files(self, input_file: str, operation: str = "processing") -> bool:
        """Giriş dosyasını doğrula"""
        if not os.path.exists(input_file):
            logger.error(f"Dosya bulunamadı ({operation}): {input_file}")
            return False

        file_size = os.path.getsize(input_file)
        if file_size == 0:
            logger.error(f"Dosya boş ({operation}): {input_file}")
            return False

        return True

    def trim(self, input_file: str, output_file: str, start_time: float, duration: float) -> bool:
        """
        Video kırpması (trim)

        Args:
            input_file: Giriş dosyası yolu
            output_file: Çıkış dosyası yolu
            start_time: Başlangıç zamanı (saniye)
            duration: Süre (saniye)

        Returns:
            bool: Başarılı ise True
        """
        if not self._validate_files(input_file, "trim"):
            return False

        if start_time < 0 or duration <= 0:
            logger.error(f"Geçersiz zaman parametreleri: start={start_time}, duration={duration}")
            return False

        logger.info(f"Kırpma işlemi başlatılıyor: {start_time}s, süre: {duration}s")

        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            extra_args=['-ss', str(start_time), '-t', str(duration), '-c', 'copy'],
            timeout=3600
        )

        if result.success:
            logger.info(f"Kırpma başarılı: {output_file}")
            return True
        else:
            logger.error(f"Kırpma hatası: {result.error_message}")
            return False

    def scale(self, input_file: str, output_file: str, width: int, height: int) -> bool:
        """
        Çözünürlük değiştirme

        Args:
            input_file: Giriş dosyası yolu
            output_file: Çıkış dosyası yolu
            width: Hedef genişlik
            height: Hedef yükseklik

        Returns:
            bool: Başarılı ise True
        """
        if not self._validate_files(input_file, "scale"):
            return False

        if width <= 0 or height <= 0:
            logger.error(f"Geçersiz çözünürlük: {width}x{height}")
            return False

        logger.info(f"Ölçeklendirme başlatılıyor: {width}x{height}")

        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            extra_args=['-vf', f'scale={width}:{height}'],
            timeout=3600
        )

        if result.success:
            logger.info(f"Ölçeklendirme başarılı: {output_file}")
            return True
        else:
            logger.error(f"Ölçeklendirme hatası: {result.error_message}")
            return False

    def extract_audio(self, input_file: str, output_file: str, audio_codec: AudioCodec) -> bool:
        """
        Ses çıkartma

        Args:
            input_file: Giriş dosyası yolu
            output_file: Çıkış dosyası yolu
            audio_codec: Hedef ses codec'i

        Returns:
            bool: Başarılı ise True
        """
        if not self._validate_files(input_file, "extract_audio"):
            return False

        if not isinstance(audio_codec, AudioCodec):
            logger.error(f"Geçersiz ses codec: {audio_codec}")
            return False

        logger.info(f"Ses çıkartılıyor: {audio_codec.name}")

        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            video_args=['-vn'],
            audio_args=['-c:a', audio_codec.lib],
            timeout=1800
        )

        if result.success:
            logger.info(f"Ses çıkartma başarılı: {output_file}")
            return True
        else:
            logger.error(f"Ses çıkartma hatası: {result.error_message}")
            return False

    def create_gif(self, input_file: str, output_file: str, start_time: float = 0, duration: float = 5, fps: int = 10) -> bool:
        """
        Videodan GIF oluşturma

        Args:
            input_file: Giriş dosyası yolu
            output_file: Çıkış dosyası yolu
            start_time: Başlangıç zamanı (saniye)
            duration: GIF süresi (saniye)
            fps: Kare hızı

        Returns:
            bool: Başarılı ise True
        """
        if not self._validate_files(input_file, "create_gif"):
            return False

        if start_time < 0 or duration <= 0 or fps <= 0:
            logger.error(f"Geçersiz GIF parametreleri: start={start_time}, duration={duration}, fps={fps}")
            return False

        logger.info(f"GIF oluşturulüyor: {duration}s, {fps} fps")

        result = self._runner.run(
            input_file=input_file,
            output_file=output_file,
            extra_args=[
                '-ss', str(start_time),
                '-t', str(duration),
                '-vf', f'fps={fps},scale=320:-1:flags=lanczos'
            ],
            timeout=1800
        )

        if result.success:
            logger.info(f"GIF oluşturma başarılı: {output_file}")
            return True
        else:
            logger.error(f"GIF oluşturma hatası: {result.error_message}")
            return False
