"""
YouTube indirme motoru - yt-dlp entegrasyonu
YtDlpRunner üzerinden çalışır
"""

import os
import re
import threading
import queue
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum

from ravn_app.core.runners import YtDlpRunner, RunnerResult, RunnerStatus


logger = logging.getLogger(__name__)


class DownloadQuality(Enum):
    """İndirme kalite seçenekleri"""
    BEST = "bestvideo+bestaudio/best"
    HIGH_1080P = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    MEDIUM_720P = "bestvideo[height<=720]+bestaudio/best[height<=720]"
    LOW_480P = "bestvideo[height<=480]+bestaudio/best[height<=480]"
    AUDIO_ONLY = "bestaudio/best"


class DownloadFormat(Enum):
    """İndirme format seçenekleri"""
    MP4 = ("mp4", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
    WEBM = ("webm", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]")
    MKV = ("mkv", "bestvideo+bestaudio/best")
    MP3 = ("mp3", "bestaudio/best")
    M4A = ("m4a", "bestaudio[ext=m4a]/bestaudio")

    def __init__(self, extension: str, format_spec: str):
        self.extension = extension
        self.format_spec = format_spec


@dataclass
class DownloadTask:
    """İndirme görevi bilgileri"""
    url: str
    output_dir: str
    format: DownloadFormat = DownloadFormat.MP4
    quality: DownloadQuality = DownloadQuality.BEST
    progress_callback: Optional[Callable[[int, str], None]] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class DownloadResult:
    """İndirme sonucu"""
    success: bool
    url: str
    output_files: List[str]
    error_message: str = ""
    title: str = ""
    duration: float = 0.0


class YouTubeDownloader:
    """YouTube videolarını indirmek için ana sınıf - YtDlpRunner kullanır"""

    DEFAULT_RETRIES = 3

    def __init__(self, ytdlp_path: str = "yt-dlp"):
        self._runner = YtDlpRunner(ytdlp_path)
        self.download_queue: queue.Queue[DownloadTask] = queue.Queue()
        self.is_worker_active = False
        self.active_downloads: Dict[str, DownloadTask] = {}
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_requested = False

    def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Video bilgilerini çek"""
        try:
            info = self._runner.extract_info(url)
            if info:
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': info.get('formats', []),
                    'webpage_url': info.get('webpage_url', url),
                }
            return None
        except Exception as e:
            logger.error(f"Bilgi alınamadı: {e}")
            raise Exception(f"Bilgi alınamadı: {str(e)}")

    def extract_playlist_entries(self, url: str) -> List[Dict[str, Any]]:
        """Playlist içeriğini indirime başlamadan önce getir."""
        try:
            entries = self._runner.extract_playlist_entries(url)
            return entries if entries else []
        except Exception as e:
            logger.error(f"Playlist bilgisi alınamadı: {e}")
            return []

    def get_video_format_options(self) -> Dict[str, Dict]:
        """Desteklenen format seçenekleri"""
        return {
            "MP4 (Video)": {
                "format": DownloadFormat.MP4.format_spec,
                "postprocessors": []
            },
            "WebM (Video)": {
                "format": DownloadFormat.WEBM.format_spec,
                "postprocessors": []
            },
            "MKV (Video)": {
                "format": DownloadFormat.MKV.format_spec,
                "postprocessors": []
            },
            "MP3 (Ses)": {
                "format": DownloadFormat.MP3.format_spec,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192"
                }]
            },
            "M4A (Ses)": {
                "format": DownloadFormat.M4A.format_spec,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "192"
                }]
            }
        }

    def get_quality_options(self) -> List[str]:
        """Kalite seçenekleri"""
        return ["En İyi", "1080p", "720p", "480p", "Sadece Ses"]

    @staticmethod
    def sanitize_filename(name: str) -> str:
        """Dosya adını temizle"""
        return re.sub(r'[\/*?:"<>|]', "", name)

    def download(
        self,
        url: str,
        output_dir: str,
        format_type: DownloadFormat = DownloadFormat.MP4,
        quality: DownloadQuality = DownloadQuality.BEST,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        retries: int = DEFAULT_RETRIES
    ) -> DownloadResult:
        """
        Video indir

        Args:
            url: Video URL'si
            output_dir: Çıkış dizini
            format_type: İndirme formatı
            quality: Kalite seviyesi
            progress_callback: İlerleme callback'i
            retries: Deneme sayısı

        Returns:
            DownloadResult: İndirme sonucu
        """
        logger.info(f"İndirme başlatılıyor: {url}")

        # Format spesifikasyonunu belirle
        format_spec = quality.value if quality != DownloadQuality.BEST else format_type.format_spec

        # Ek argümanları hazırla
        extra_args = ['--merge-output-format', format_type.extension]

        if format_type in [DownloadFormat.MP3, DownloadFormat.M4A]:
            extra_args.extend([
                '-x',  # Extract audio
                '--audio-format', format_type.extension,
                '--audio-quality', '0'
            ])

        result = self._runner.download(
            url=url,
            output_dir=output_dir,
            format_spec=format_spec,
            extra_args=extra_args,
            retries=retries,
            progress_callback=progress_callback
        )

        if result.success:
            downloaded_files = result.metadata.get('downloaded_files', [])
            logger.info(f"İndirme tamamlandı: {downloaded_files}")
            return DownloadResult(
                success=True,
                url=url,
                output_files=downloaded_files
            )
        else:
            logger.error(f"İndirme başarısız: {result.error_message}")
            return DownloadResult(
                success=False,
                url=url,
                output_files=[],
                error_message=result.error_message
            )

    def queue_download(self, task: DownloadTask) -> None:
        """İndirme kuyruğuna görev ekle"""
        self.download_queue.put(task)
        logger.info(f"Kuyruğa eklendi: {task.url}")

        # Worker aktif değilse başlat
        if not self.is_worker_active:
            self._start_worker()

    def _start_worker(self) -> None:
        """Arka plan worker'ını başlat"""
        if self._worker_thread and self._worker_thread.is_alive():
            return

        self._stop_requested = False
        self.is_worker_active = True
        self._worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()
        logger.info("Download worker başlatıldı")

    def _process_queue(self) -> None:
        """Kuyruktan görevleri işle"""
        while not self._stop_requested:
            try:
                task = self.download_queue.get(timeout=1.0)
                self.active_downloads[task.url] = task

                result = self.download(
                    url=task.url,
                    output_dir=task.output_dir,
                    format_type=task.format,
                    quality=task.quality,
                    progress_callback=task.progress_callback
                )

                del self.active_downloads[task.url]
                self.download_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Kuyruk işleme hatası: {e}")

        self.is_worker_active = False
        logger.info("Download worker durduruldu")

    def stop_worker(self) -> None:
        """Worker'ı durdur"""
        self._stop_requested = True
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)

    def cancel_download(self, url: str) -> bool:
        """Aktif indirmeyi iptal et"""
        if url in self.active_downloads:
            cancelled = self._runner.cancel()
            if cancelled:
                del self.active_downloads[url]
                logger.info(f"İndirme iptal edildi: {url}")
            return cancelled
        return False

    def get_version(self) -> Optional[str]:
        """yt-dlp versiyonunu al"""
        return self._runner.get_version()

    def update_ytdlp(self) -> bool:
        """yt-dlp'yi güncelle"""
        return self._runner.update()

    def list_formats(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """URL için mevcut formatları listele"""
        return self._runner.list_formats(url)

