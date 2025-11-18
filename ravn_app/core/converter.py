"""
Video format dönüştürme modülü - Faz 1: Video Converter
Desteklenen formatlar: MP4, MKV, AVI, MOV, WEBM, FLV
Desteklenen codec'ler: H.264, H.265, VP8, VP9, AV1 (video), AAC, MP3, Opus, Vorbis, FLAC (audio)
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from threading import Thread
import queue


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
    """Video format dönüştürücü"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """
        VideoConverter'ı başlat
        
        Args:
            ffmpeg_path (str): FFmpeg yürütülebilir dosyasının yolu
        """
        self.ffmpeg_path = ffmpeg_path
        self.current_process = None
        self.is_running = False
        self.progress = 0
        self.status_callback = None
    
    def set_status_callback(self, callback):
        """İlerleme güncellemeleri için callback ayarla"""
        self.status_callback = callback
    
    def _log(self, message: str, level: str = "info"):
        """Günlük mesajı yazdır"""
        if self.status_callback:
            self.status_callback(f"[{level.upper()}] {message}")
        else:
            print(f"[{level.upper()}] {message}")
    
    def convert(self, settings: ConversionSettings) -> bool:
        """
        Videoyu dönüştür
        
        Args:
            settings (ConversionSettings): Dönüştürme ayarları
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            self.is_running = True
            
            # Giriş dosyasını kontrol et
            if not os.path.exists(settings.input_file):
                self._log(f"Giriş dosyası bulunamadı: {settings.input_file}", "error")
                return False
            
            # Çıkış dizinini oluştur
            output_dir = os.path.dirname(settings.output_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            self._log(f"Dönüştürme başlanıyor: {settings.input_file}")
            self._log(f"Format: {settings.video_codec.name} / {settings.audio_codec.name}")
            
            # FFmpeg komutunu oluştur
            command = self._build_command(settings)
            
            # İşlemi çalıştır
            self.current_process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Çıkıyı izle
            _, stderr = self.current_process.communicate()
            
            if self.current_process.returncode == 0:
                self._log(f"Dönüştürme tamamlandı: {settings.output_file}", "success")
                self.is_running = False
                return True
            else:
                self._log(f"Dönüştürme hatası: {stderr}", "error")
                self.is_running = False
                return False
                
        except Exception as e:
            self._log(f"Dönüştürme hatası: {str(e)}", "error")
            self.is_running = False
            return False
    
    def _build_command(self, settings: ConversionSettings) -> List[str]:
        """FFmpeg komutunu oluştur"""
        cmd = [self.ffmpeg_path, '-i', settings.input_file]
        
        # Video codec
        if not settings.audio_only:
            codec_cmd = CodecManager.get_video_codec_command(
                settings.video_codec,
                settings.video_quality,
                settings.preset
            )
            cmd.extend(codec_cmd)
            
            # FPS değiştirme
            if settings.fps:
                cmd.extend(['-r', str(settings.fps)])
            
            # Çözünürlük değiştirme
            if settings.scale:
                width, height = settings.scale
                cmd.extend(['-vf', f'scale={width}:{height}'])
        else:
            cmd.append('-vn')  # Video yok
        
        # Ses codec
        if not settings.video_only:
            codec_cmd = CodecManager.get_audio_codec_command(
                settings.audio_codec,
                settings.audio_bitrate
            )
            cmd.extend(codec_cmd)
        else:
            cmd.append('-an')  # Ses yok
        
        # Hardware acceleration
        if settings.hardware_accel and settings.hardware_accel != 'none':
            cmd.extend(['-hwaccel', settings.hardware_accel])
        
        # Çıkış dosyası
        cmd.extend(['-y', settings.output_file])
        
        return cmd
    
    def stop(self):
        """Dönüştürmeyi durdur"""
        if self.current_process:
            self.current_process.terminate()
            self.is_running = False
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
