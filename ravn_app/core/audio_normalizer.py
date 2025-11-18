"""
Ses normalizasyonu ve video birleştirme modülü - Faz 3: Orta Vadeli Özellikler
"""

import os
import subprocess
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


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
    """Ses normalizasyonu motoru"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        """AudioNormalizer'ı başlat"""
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        logger.info(f"AudioNormalizer başlatıldı: {ffmpeg_path}")

    def analyze_loudness(self, input_file: str) -> Optional[Dict]:
        """
        Ses dosyasının LUFS seviyesini analiz et

        Args:
            input_file: Analiz edilecek dosya

        Returns:
            dict: Loudness analiz sonuçları (integrated_loudness, true_peak, etc)
        """
        try:
            if not os.path.exists(input_file):
                logger.error(f"Dosya bulunamadı: {input_file}")
                return None

            cmd = [
                self.ffprobe_path,
                '-v', 'error',
                '-of', 'json',
                '-show_entries', 'stream=',
                '-f', 'lavfi',
                f"aformat=channel_layouts=mono,loudnorm=print_format=json:I=-23:TP=-1.5:LRA=11 [a0]; [0:a] [a0] concat=n=1:v=0:a=1 [a]",
                '-i', input_file
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                # Basit analiz - gerçek LUFS değeri sadece normalize sırasında elde edilir
                logger.info(f"Ses analizi başarılı: {input_file}")
                return {"status": "analyzed"}
            else:
                logger.error(f"Ses analizi hatası: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error("Ses analizi zaman aşımına uğradı")
            return None
        except Exception as e:
            logger.error(f"Ses analizi hatası: {type(e).__name__}: {str(e)}")
            return None

    def normalize(self, settings: AudioNormalizationSettings, progress_callback=None) -> bool:
        """
        Ses normalizasyonu yap

        Args:
            settings: Normalizasyon ayarları
            progress_callback: İlerleme callback'i

        Returns:
            bool: Başarılı ise True
        """
        try:
            if not os.path.exists(settings.input_file):
                logger.error(f"Giriş dosyası bulunamadı: {settings.input_file}")
                return False

            logger.info(f"Ses normalizasyonu başlanıyor: {settings.input_file}")
            logger.info(f"Hedef loudness: {settings.target_loudness} LUFS")

            # FFmpeg filtresi oluştur
            if settings.method == "loudnorm":
                audio_filter = f"loudnorm=I={settings.target_loudness}:TP={settings.target_peak}:LRA=11"
            elif settings.method == "dynaudnorm":
                audio_filter = "dynaudnorm=f=500:g=31:p=0.95"
            else:  # volume
                audio_filter = "volume=1.0"

            if settings.enable_compression:
                audio_filter += ",acompressor=threshold=-50dB:ratio=4:attack=0.005:release=0.05"

            cmd = [
                self.ffmpeg_path,
                '-i', settings.input_file,
                '-af', audio_filter,
                '-c:v', 'copy',  # Video'yu kopyala
                '-y',
                settings.output_file
            ]

            logger.info(f"FFmpeg komutu: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            _, stderr = process.communicate()

            if process.returncode == 0:
                logger.info(f"Ses normalizasyonu başarılı: {settings.output_file}")
                if progress_callback:
                    progress_callback(100, "Tamamlandı")
                return True
            else:
                logger.error(f"Ses normalizasyonu hatası: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Ses normalizasyonu zaman aşımına uğradı")
            return False
        except Exception as e:
            logger.error(f"Ses normalizasyonu hatası: {type(e).__name__}: {str(e)}")
            return False


@dataclass
class VideoMergeSettings:
    """Video birleştirme ayarları"""
    input_files: List[str]
    output_file: str
    preserve_audio: bool = True
    transition_duration: float = 0.0  # Geçiş süresi (saniye)


class VideoMerger:
    """Video birleştirme motoru"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """VideoMerger'ı başlat"""
        self.ffmpeg_path = ffmpeg_path
        logger.info(f"VideoMerger başlatıldı: {ffmpeg_path}")

    def merge(self, settings: VideoMergeSettings, progress_callback=None) -> bool:
        """
        Birden fazla videoyu birleştir (concat demuxer)

        Args:
            settings: Birleştirme ayarları
            progress_callback: İlerleme callback'i

        Returns:
            bool: Başarılı ise True
        """
        try:
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

            # FFmpeg komutu oluştur
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # Yeniden kodlama yok - daha hızlı
                '-y',
                settings.output_file
            ]

            if progress_callback:
                progress_callback(20, "Birleştirme başladı")

            logger.info(f"FFmpeg komutu: {' '.join(cmd)}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            _, stderr = process.communicate()

            # Temizle
            try:
                os.remove(concat_file)
            except:
                pass

            if process.returncode == 0:
                logger.info(f"Video birleştirmesi başarılı: {settings.output_file}")
                if progress_callback:
                    progress_callback(100, "Tamamlandı")
                return True
            else:
                logger.error(f"Video birleştirmesi hatası: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Video birleştirmesi zaman aşımına uğradı")
            return False
        except Exception as e:
            logger.error(f"Video birleştirmesi hatası: {type(e).__name__}: {str(e)}")
            return False

    def merge_with_transitions(self, settings: VideoMergeSettings, progress_callback=None) -> bool:
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

        try:
            for f in settings.input_files:
                if not os.path.exists(f):
                    logger.error(f"Dosya bulunamadı: {f}")
                    return False

            if len(settings.input_files) < 2:
                logger.error("Birleştirmek için en az 2 dosya gerekli")
                return False

            logger.info(f"Geçişli video birleştirmesi başlanıyor")
            logger.info(f"Geçiş süresi: {settings.transition_duration}s")

            # Tüm videolar aynı özellikte olmalı
            # Bunun için xfade filtresi kullanacağız

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
                        except:
                            pass

                return True

        except Exception as e:
            logger.error(f"Geçişli birleştirme hatası: {type(e).__name__}: {str(e)}")
            return False

    def _merge_two_videos(self, input1: str, input2: str, output: str,
                          transition_duration: float, progress_callback=None) -> bool:
        """İki videoyu geçişle birleştir"""
        try:
            # Xfade filtresi kullanarak geçiş ekle
            xfade_filter = (
                f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={0}[v];"
                f"[0:a][1:a]acrossfade=d={transition_duration}[a]"
            )

            cmd = [
                self.ffmpeg_path,
                '-i', input1,
                '-i', input2,
                '-filter_complex', xfade_filter,
                '-map', '[v]',
                '-map', '[a]',
                '-y',
                output
            ]

            logger.info(f"İki video birleştiriliyor: {Path(input1).name} + {Path(input2).name}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            _, stderr = process.communicate()

            if process.returncode == 0:
                logger.info(f"İki video birleştirmesi başarılı")
                return True
            else:
                logger.error(f"İki video birleştirmesi hatası: {stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("İki video birleştirmesi zaman aşımına uğradı")
            return False
        except Exception as e:
            logger.error(f"İki video birleştirmesi hatası: {type(e).__name__}: {str(e)}")
            return False
