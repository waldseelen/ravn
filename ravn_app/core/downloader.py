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

from ravn_app.core.download_naming import apply_naming_template, template_needs_video_info
from ravn_app.core.runners import YtDlpRunner, RunnerResult, RunnerStatus
from ravn_app.core.subtitle_manager import SubtitleDownloader


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
    MP4  = ("mp4",  "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best")
    WEBM = ("webm", "bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]")
    MKV  = ("mkv",  "bestvideo+bestaudio/best")
    MP3  = ("mp3",  "bestaudio/best")
    M4A  = ("m4a",  "bestaudio[ext=m4a]/bestaudio")
    FLAC = ("flac", "bestaudio/best")
    OPUS = ("opus", "bestaudio/best")
    WAV  = ("wav",  "bestaudio/best")
    AAC  = ("aac",  "bestaudio/best")

    def __init__(self, extension: str, format_spec: str):
        self.extension = extension
        self.format_spec = format_spec


_AUDIO_FORMATS = {
    DownloadFormat.MP3, DownloadFormat.M4A,
    DownloadFormat.FLAC, DownloadFormat.OPUS,
    DownloadFormat.WAV, DownloadFormat.AAC,
}


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
                quality_data = self._runner.compute_size_by_quality(info)
                result = {
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
                result.update(quality_data)
                return result
            return None
        except Exception as e:
            logger.error(f"Bilgi alınamadı: {e}")
            raise Exception(f"Bilgi alınamadı: {str(e)}")

    def extract_playlist_entries(self, url: str, quality_label: str = "En İyi") -> List[Dict[str, Any]]:
        """Playlist içeriğini seçili kaliteye göre detaylarıyla getir."""
        try:
            # Detaylı bilgileri al (boyut, çözünürlük, format) - kaliteye göre seç.
            entries = self._runner.extract_playlist_entries(
                url,
                with_details=True,
                quality_label=quality_label,
            )
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

    @staticmethod
    def _quality_label_for_naming(quality: DownloadQuality) -> str:
        """Map internal quality enum to the labels used in size/resolution helpers."""
        quality_labels = {
            DownloadQuality.BEST: "En İyi",
            DownloadQuality.HIGH_1080P: "1080p",
            DownloadQuality.MEDIUM_720P: "720p",
            DownloadQuality.LOW_480P: "480p",
            DownloadQuality.AUDIO_ONLY: "Sadece Ses",
        }
        return quality_labels.get(quality, "En İyi")

    def _resolve_naming_resolution(
        self,
        video_info: Optional[Dict[str, Any]],
        quality: DownloadQuality,
        format_type: DownloadFormat,
    ) -> str:
        """Resolve a friendly resolution token for filename templates."""
        if format_type in _AUDIO_FORMATS or quality == DownloadQuality.AUDIO_ONLY:
            return "audio"

        if isinstance(video_info, dict):
            try:
                quality_maps = self._runner.compute_size_by_quality(video_info)
                resolution_map = quality_maps.get("resolution_by_quality") or {}
                quality_label = self._quality_label_for_naming(quality)
                resolution = str(resolution_map.get(quality_label) or "").strip()
                if resolution and resolution.lower() != "unknown":
                    return resolution
            except Exception as err:
                logger.debug(f"Çözünürlük bilgisi çözümlenemedi: {err}")

            width = video_info.get("width")
            height = video_info.get("height")
            if width and height:
                return f"{width}x{height}"

        fallback_map = {
            DownloadQuality.HIGH_1080P: "1080p",
            DownloadQuality.MEDIUM_720P: "720p",
            DownloadQuality.LOW_480P: "480p",
        }
        return fallback_map.get(quality, "best")

    def _resolve_sort_subfolder(self, video_info: Optional[Dict[str, Any]], auto_sort_mode: str) -> str:
        """Metadata'dan klasörleme için alt klasör adını üret."""
        if not isinstance(video_info, dict):
            return ""

        mode = (auto_sort_mode or "artist").strip().lower()
        if mode == "channel":
            candidates = [
                video_info.get("channel"),
                video_info.get("uploader"),
                video_info.get("creator"),
                video_info.get("artist"),
            ]
        else:
            candidates = [
                video_info.get("artist"),
                video_info.get("album_artist"),
                video_info.get("creator"),
                video_info.get("uploader"),
                video_info.get("channel"),
            ]

        for raw_value in candidates:
            if not raw_value:
                continue
            normalized = self.sanitize_filename(str(raw_value).strip()).strip(" .")
            if normalized:
                return normalized
        return ""

    def _resolve_output_dir(
        self,
        output_dir: str,
        video_info: Optional[Dict[str, Any]],
        auto_sort_enabled: bool,
        auto_sort_mode: str,
    ) -> str:
        """Otomatik klasörleme açıksa hedef klasörü metadata'ya göre güncelle."""
        if not auto_sort_enabled:
            return output_dir

        subfolder = self._resolve_sort_subfolder(video_info, auto_sort_mode)
        if not subfolder:
            return output_dir

        return str(Path(output_dir) / subfolder)

    @staticmethod
    def _collect_audio_metadata(video_info: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Audio etiketleme için normalize metadata sözlüğü hazırla."""
        if not isinstance(video_info, dict):
            return {}

        title = str(video_info.get("track") or video_info.get("title") or "").strip()
        artist = str(
            video_info.get("artist")
            or video_info.get("album_artist")
            or video_info.get("uploader")
            or video_info.get("channel")
            or ""
        ).strip()
        album = str(
            video_info.get("album")
            or video_info.get("playlist_title")
            or video_info.get("channel")
            or video_info.get("uploader")
            or ""
        ).strip()
        lyrics = str(video_info.get("description") or "").strip()

        if len(lyrics) > 10000:
            lyrics = lyrics[:10000]

        return {
            "title": title,
            "artist": artist,
            "album": album,
            "lyrics": lyrics,
        }

    def _build_audio_download_args(self, embed_metadata: bool, embed_lyrics: bool) -> List[str]:
        """yt-dlp/ffmpeg tarafında metadata gömme argümanları."""
        if not embed_metadata:
            return []

        args = [
            "--embed-metadata",
            "--add-metadata",
            "--embed-thumbnail",
            "--convert-thumbnails", "jpg",
            "--parse-metadata", "uploader:%(artist)s",
            "--parse-metadata", "channel:%(artist)s",
            "--parse-metadata", "playlist_title:%(album)s",
            "--parse-metadata", "playlist:%(album)s",
        ]

        if embed_lyrics:
            args.extend(["--parse-metadata", "description:%(meta_lyrics)s"])

        return args

    def _build_subtitle_download_args(
        self,
        video_info: Optional[Dict[str, Any]],
        format_type: DownloadFormat,
        auto_download_subtitles: bool,
        preferred_subtitle_language: str,
        subtitle_fallback_language: str,
        subtitle_include_auto_generated: bool,
        auto_embed_subtitles: bool,
    ) -> List[str]:
        """Build downloader-side subtitle automation args using shared subtitle logic."""
        if not auto_download_subtitles:
            return []

        embed_subtitles = bool(auto_embed_subtitles and format_type not in _AUDIO_FORMATS)
        return SubtitleDownloader.build_download_args(
            video_info,
            preferred_language=preferred_subtitle_language,
            fallback_language=subtitle_fallback_language,
            include_auto_generated=subtitle_include_auto_generated,
            embed_subtitles=embed_subtitles,
        )

    def _apply_audio_metadata(
        self,
        downloaded_files: List[str],
        video_info: Optional[Dict[str, Any]],
        embed_lyrics: bool,
    ) -> None:
        """İndirilen ses dosyalarına mutagen ile metadata iyileştirme uygula."""
        if not downloaded_files:
            return

        metadata = self._collect_audio_metadata(video_info)
        if not metadata:
            return

        try:
            from mutagen.id3 import ID3, ID3NoHeaderError, TALB, TIT2, TPE1, USLT
            from mutagen.mp3 import MP3
            from mutagen.mp4 import MP4
        except Exception:
            logger.debug("mutagen bulunamadı, derin metadata iyileştirmesi atlandı")
            return

        for file_path in downloaded_files:
            suffix = Path(file_path).suffix.lower()
            if suffix not in {".mp3", ".m4a"}:
                continue
            if not os.path.exists(file_path):
                continue

            try:
                if suffix == ".mp3":
                    audio = MP3(file_path, ID3=ID3)
                    if audio.tags is None:
                        try:
                            audio.add_tags()
                        except ID3NoHeaderError:
                            pass

                    if metadata.get("title"):
                        audio.tags.delall("TIT2")
                        audio.tags.add(TIT2(encoding=3, text=metadata["title"]))
                    if metadata.get("artist"):
                        audio.tags.delall("TPE1")
                        audio.tags.add(TPE1(encoding=3, text=metadata["artist"]))
                    if metadata.get("album"):
                        audio.tags.delall("TALB")
                        audio.tags.add(TALB(encoding=3, text=metadata["album"]))
                    if embed_lyrics and metadata.get("lyrics"):
                        audio.tags.delall("USLT")
                        audio.tags.add(USLT(encoding=3, lang="eng", text=metadata["lyrics"]))

                    audio.save()
                    continue

                audio = MP4(file_path)
                if metadata.get("title"):
                    audio["\u00a9nam"] = [metadata["title"]]
                if metadata.get("artist"):
                    audio["\u00a9ART"] = [metadata["artist"]]
                if metadata.get("album"):
                    audio["\u00a9alb"] = [metadata["album"]]
                if embed_lyrics and metadata.get("lyrics"):
                    audio["\u00a9lyr"] = [metadata["lyrics"]]
                audio.save()
            except Exception as err:
                logger.warning(f"Audio metadata iyileştirme atlandı ({file_path}): {err}")

    def download(
        self,
        url: str,
        output_dir: str,
        format_type: DownloadFormat = DownloadFormat.MP4,
        quality: DownloadQuality = DownloadQuality.BEST,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        retries: int = DEFAULT_RETRIES,
        embed_metadata: bool = True,
        embed_lyrics: bool = True,
        auto_sort: bool = False,
        auto_sort_enabled: Optional[bool] = None,
        auto_sort_mode: str = "artist",
        audio_bitrate: Optional[str] = None,
        naming_preset: str = "standard",
        filename_template: Optional[str] = None,
        auto_subtitle_download: bool = False,
        preferred_subtitle_language: str = "tr",
        subtitle_fallback_language: str = "en",
        subtitle_include_auto_generated: bool = True,
        auto_embed_subtitles: bool = False,
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
            embed_metadata: Ses dosyalarına ID3/metadata ve albüm kapağı göm
            embed_lyrics: Metadata gömme sırasında açıklamadan şarkı sözü alanını üretmeye çalış
            auto_sort: İndirilen dosyaları kanal/sanatçı adına göre klasörlere ayır
            auto_sort_enabled: auto_sort için yeni isimlendirme (geriye uyumlu)
            auto_sort_mode: Klasörleme modu: artist veya channel
            naming_preset: Hazır adlandırma profili (standard/clean/playlist)
            filename_template: İsteğe bağlı özel şablon ({title}, {uploader}, ...)
            auto_subtitle_download: İndirme sırasında uygun altyazıları da al
            preferred_subtitle_language: Öncelikli altyazı dili
            subtitle_fallback_language: Öncelikli dil yoksa alternatif dil
            subtitle_include_auto_generated: Gerekirse otomatik üretilen altyazıları kullan
            auto_embed_subtitles: Video indirmelerinde bulunan altyazıyı dosyaya göm

        Returns:
            DownloadResult: İndirme sonucu
        """
        logger.info(f"İndirme başlatılıyor: {url}")

        sort_enabled = auto_sort if auto_sort_enabled is None else auto_sort_enabled
        needs_video_info = bool(
            sort_enabled
            or (embed_metadata and format_type in [DownloadFormat.MP3, DownloadFormat.M4A])
            or template_needs_video_info(naming_preset, filename_template)
            or auto_subtitle_download
        )
        video_info: Optional[Dict[str, Any]] = None
        if needs_video_info:
            try:
                video_info = self._runner.extract_info(url)
            except Exception as err:
                logger.debug(f"İndirme öncesi metadata alınamadı: {err}")

        # Format spesifikasyonunu belirle
        format_spec = quality.value if quality != DownloadQuality.BEST else format_type.format_spec

        resolved_output_dir = self._resolve_output_dir(
            output_dir=output_dir,
            video_info=video_info,
            auto_sort_enabled=bool(sort_enabled),
            auto_sort_mode=auto_sort_mode,
        )

        # Ek argümanları hazırla
        extra_args = ['--merge-output-format', format_type.extension]

        if format_type in _AUDIO_FORMATS:
            extra_args.extend([
                '-x',  # Extract audio
                '--audio-format', format_type.extension,
                '--audio-quality', audio_bitrate or '0',
            ])
            extra_args.extend(self._build_audio_download_args(embed_metadata=embed_metadata, embed_lyrics=embed_lyrics))

        extra_args.extend(
            self._build_subtitle_download_args(
                video_info=video_info,
                format_type=format_type,
                auto_download_subtitles=auto_subtitle_download,
                preferred_subtitle_language=preferred_subtitle_language,
                subtitle_fallback_language=subtitle_fallback_language,
                subtitle_include_auto_generated=subtitle_include_auto_generated,
                auto_embed_subtitles=auto_embed_subtitles,
            )
        )

        result = self._runner.download(
            url=url,
            output_dir=resolved_output_dir,
            filename_template="%(title)s.%(ext)s",
            format_spec=format_spec,
            extra_args=extra_args,
            retries=retries,
            progress_callback=progress_callback
        )

        if result.success:
            downloaded_files = result.metadata.get('downloaded_files', [])

            if format_type in _AUDIO_FORMATS and embed_metadata:
                self._apply_audio_metadata(downloaded_files, video_info, embed_lyrics)

            downloaded_files = apply_naming_template(
                downloaded_files,
                output_dir=resolved_output_dir,
                naming_preset=naming_preset,
                custom_template=filename_template,
                video_info=video_info,
                resolution=self._resolve_naming_resolution(video_info, quality, format_type),
            )

            logger.info(f"İndirme tamamlandı: {downloaded_files}")
            return DownloadResult(
                success=True,
                url=url,
                output_files=downloaded_files,
                title=str((video_info or {}).get('title') or Path(downloaded_files[0]).stem if downloaded_files else ""),
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

