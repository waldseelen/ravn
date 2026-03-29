"""
Ses normalizasyonu ve video birleştirme modülü - Faz 3: Orta Vadeli Özellikler
FFmpegRunner üzerinden çalışır
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass

from ravn_app.core.runners import FFmpegRunner, RunnerResult


logger = logging.getLogger(__name__)


@dataclass
class AudioNormalizationSettings:
    """Ses normalizasyonu ayarları"""
    input_file: str
    output_file: str
    target_loudness: float = -23.0  # LUFS (Loudness Units relative to Full Scale)
    target_peak: float = -1.0  # dB
    method: str = "loudnorm"  # loudnorm, volume, dynaudnorm
    enable_compression: bool = False


class AudioNormalizer:
    """Ses normalizasyonu motoru - FFmpegRunner kullanır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """AudioNormalizer'ı başlat"""
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)
        logger.info(f"AudioNormalizer başlatıldı: {ffmpeg_path}")

    def analyze_loudness(self, input_file: str) -> Optional[Dict]:
        """
        Ses dosyasının LUFS seviyesini analiz et

        Args:
            input_file: Analiz edilecek dosya

        Returns:
            dict: Loudness analiz sonuçları (integrated_loudness, true_peak, etc)
        """
        if not os.path.exists(input_file):
            logger.error(f"Dosya bulunamadı: {input_file}")
            return None

        # FFprobe ile analiz
        probe_result = self._runner.probe(input_file)
        if probe_result:
            logger.info(f"Ses analizi başarılı: {input_file}")
            return {"status": "analyzed", "probe_data": probe_result}
        else:
            logger.error(f"Ses analizi hatası")
            return None

    def _build_audio_filter(self, settings: AudioNormalizationSettings) -> str:
        """Ses filtresi oluştur"""
        if settings.method == "loudnorm":
            audio_filter = f"loudnorm=I={settings.target_loudness}:TP={settings.target_peak}:LRA=11"
        elif settings.method == "dynaudnorm":
            audio_filter = "dynaudnorm=f=500:g=31:p=0.95"
        else:  # volume
            audio_filter = "volume=1.0"

        if settings.enable_compression:
            audio_filter += ",acompressor=threshold=-50dB:ratio=4:attack=0.005:release=0.05"

        return audio_filter

    def normalize(
        self,
        settings: AudioNormalizationSettings,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Ses normalizasyonu yap

        Args:
            settings: Normalizasyon ayarları
            progress_callback: İlerleme callback'i

        Returns:
            bool: Başarılı ise True
        """
        if not os.path.exists(settings.input_file):
            logger.error(f"Giriş dosyası bulunamadı: {settings.input_file}")
            return False

        logger.info(f"Ses normalizasyonu başlanıyor: {settings.input_file}")
        logger.info(f"Hedef loudness: {settings.target_loudness} LUFS")

        # Ses filtresini oluştur
        audio_filter = self._build_audio_filter(settings)

        # FFmpegRunner kullanarak çalıştır
        result = self._runner.run(
            input_file=settings.input_file,
            output_file=settings.output_file,
            video_args=['-c:v', 'copy'],  # Video'yu kopyala
            extra_args=['-af', audio_filter],
            progress_callback=progress_callback
        )

        if result.success:
            logger.info(f"Ses normalizasyonu başarılı: {settings.output_file}")
            if progress_callback:
                progress_callback(100, "Tamamlandı")
            return True
        else:
            logger.error(f"Ses normalizasyonu hatası: {result.error_message}")
            return False


@dataclass
class VideoMergeSettings:
    """Video birleştirme ayarları"""
    input_files: List[str]
    output_file: str
    preserve_audio: bool = True
    transition_duration: float = 0.0  # Geçiş süresi (saniye)


class VideoMerger:
    """Video birleştirme motoru - FFmpegRunner kullanır"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """VideoMerger'ı başlat"""
        self.ffmpeg_path = ffmpeg_path
        self._runner = FFmpegRunner(ffmpeg_path, ffprobe_path)
        logger.info(f"VideoMerger başlatıldı: {ffmpeg_path}")

    def merge(
        self,
        settings: VideoMergeSettings,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Birden fazla videoyu birleştir (concat demuxer)

        Args:
            settings: Birleştirme ayarları
            progress_callback: İlerleme callback'i

        Returns:
            bool: Başarılı ise True
        """
        # Dosya varlığını kontrol et
        for f in settings.input_files:
            if not os.path.exists(f):
                logger.error(f"Dosya bulunamadı: {f}")
                return False

        if len(settings.input_files) < 2:
            logger.error("Birleştirmek için en az 2 dosya gerekli")
            return False

        logger.info(f"Video birleştirmesi başlanıyor: {len(settings.input_files)} dosya")
        logger.info(f"Geçiş süresi: {settings.transition_duration}s")

        # Concat demuxer input dosyası oluştur
        concat_file = settings.output_file + ".concat.txt"
        try:
            with open(concat_file, 'w') as f:
                for input_file in settings.input_files:
                    f.write(f"file '{os.path.abspath(input_file)}'\n")
            logger.info(f"Concat dosyası oluşturuldu: {concat_file}")
        except Exception as e:
            logger.error(f"Concat dosyası oluşturulamadı: {str(e)}")
            return False

        if progress_callback:
            progress_callback(10, "Dosya listesi hazırlandı")

        if progress_callback:
            progress_callback(20, "Birleştirme başladı")

        # FFmpegRunner ile concat dosyasını işle
        result = self._runner.run_raw(
            args=[
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                settings.output_file
            ]
        )

        # Temizle
        try:
            os.remove(concat_file)
        except Exception:
            pass

        if result.success:
            logger.info(f"Video birleştirmesi başarılı: {settings.output_file}")
            if progress_callback:
                progress_callback(100, "Tamamlandı")
            return True
        else:
            logger.error(f"Video birleştirmesi hatası: {result.error_message}")
            return False

    def merge_with_transitions(
        self,
        settings: VideoMergeSettings,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """
        Geçişli video birleştirmesi (daha yavaş ama profesyonel)

        Args:
            settings: Birleştirme ayarları
            progress_callback: İlerleme callback'i

        Returns:
            bool: Başarılı ise True
        """
        if settings.transition_duration <= 0:
            # Geçiş yoksa normal birleştirme yap
            return self.merge(settings, progress_callback)

        for f in settings.input_files:
            if not os.path.exists(f):
                logger.error(f"Dosya bulunamadı: {f}")
                return False

        if len(settings.input_files) < 2:
            logger.error("Birleştirmek için en az 2 dosya gerekli")
            return False

        logger.info(f"Geçişli video birleştirmesi başlanıyor")
        logger.info(f"Geçiş süresi: {settings.transition_duration}s")

        if len(settings.input_files) == 2:
            # İki video için basit xfade
            return self._merge_two_videos(
                settings.input_files[0],
                settings.input_files[1],
                settings.output_file,
                settings.transition_duration,
                progress_callback
            )
        else:
            # Çoklu video - sırayla birleştir
            temp_output = settings.output_file + ".tmp0.mp4"

            for i in range(1, len(settings.input_files)):
                input1 = temp_output if i > 1 else settings.input_files[0]
                input2 = settings.input_files[i]
                current_output = temp_output if i < len(settings.input_files) - 1 else settings.output_file

                if not self._merge_two_videos(
                    input1, input2, current_output,
                    settings.transition_duration,
                    progress_callback
                ):
                    return False

                # Eski temp dosyasını sil
                if i > 1:
                    try:
                        os.remove(input1)
                    except Exception:
                        pass

            return True

    def _merge_two_videos(
        self,
        input1: str,
        input2: str,
        output: str,
        transition_duration: float,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> bool:
        """İki videoyu geçişle birleştir"""
        # Xfade filtresi kullanarak geçiş ekle
        xfade_filter = (
            f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={0}[v];"
            f"[0:a][1:a]acrossfade=d={transition_duration}[a]"
        )

        logger.info(f"İki video birleştiriliyor: {Path(input1).name} + {Path(input2).name}")

        result = self._runner.run_raw(
            args=[
                '-i', input1,
                '-i', input2,
                '-filter_complex', xfade_filter,
                '-map', '[v]',
                '-map', '[a]',
                '-y',
                output
            ]
        )

        if result.success:
            logger.info(f"İki video birleştirmesi başarılı")
            return True
        else:
            logger.error(f"İki video birleştirmesi hatası: {result.error_message}")
            return False
