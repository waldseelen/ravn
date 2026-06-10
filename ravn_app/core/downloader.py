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
from typing import Dict, List, Optional, Callable, Any, Iterable, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from ravn_app.core.config_paths import get_download_archive_file_path
from ravn_app.core.converter import (
    AudioBitrate,
    AudioCodec,
    ConversionSettings,
    VideoCodec,
    VideoConverter,
    VideoQuality,
)
from ravn_app.core.download_metadata import build_enriched_download_metadata
from ravn_app.core.download_naming import apply_naming_template, template_needs_video_info
from ravn_app.core.media_helpers import MediaHelpers
from ravn_app.core.runners import YtDlpRunner, RunnerResult
from ravn_app.core.subtitle_manager import SubtitleDownloader, SubtitleEmbedder


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
class DownloadRequest:
    """Tekil indirme isteği konfigürasyonunu sarmalar"""
    url: str
    output_dir: str
    format: DownloadFormat = DownloadFormat.MP4
    quality: DownloadQuality = DownloadQuality.BEST
    progress_callback: Optional[Callable[[int, str], None]] = None
    retries: int = 3
    embed_metadata: bool = True
    embed_lyrics: bool = True
    auto_sort: bool = False
    auto_sort_enabled: Optional[bool] = None
    auto_sort_mode: str = "artist"
    audio_bitrate: Optional[str] = None
    naming_preset: str = "standard"
    filename_template: Optional[str] = None
    auto_subtitle_download: bool = False
    preferred_subtitle_language: str = "tr"
    subtitle_fallback_language: str = "en"
    subtitle_include_auto_generated: bool = True
    auto_embed_subtitles: bool = False
    postprocess_profile: Optional[Union[Dict[str, Any], 'DownloadPostProcessProfile']] = None
    robustness_profile: Optional[Union[Dict[str, Any], 'DownloadRobustnessProfile']] = None
    advanced_profile: Optional[Union[Dict[str, Any], 'DownloadAdvancedProfile']] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DownloadResult:
    """İndirme sonucu"""
    success: bool
    url: str
    output_files: List[str]
    error_message: str = ""
    title: str = ""
    duration: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass(frozen=True)
class DownloadPostProcessProfile:
    """Settings-backed post-download automation profile."""

    extract_audio: bool = False
    audio_format: str = "mp3"
    audio_bitrate: str = "192k"
    convert_enabled: bool = False
    convert_format: str = ""
    embed_subtitles: bool = False

    @property
    def enabled(self) -> bool:
        return bool(self.extract_audio or self.convert_enabled or self.embed_subtitles)


@dataclass
class PostProcessPipelineResult:
    """Outcome of applying post-download automation steps."""

    success: bool
    output_files: List[str] = field(default_factory=list)
    supporting_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""


@dataclass(frozen=True)
class DownloadRobustnessProfile:
    """Settings-backed robustness controls for yt-dlp acquisition."""

    enable_archive: bool = True
    detect_duplicates: bool = True
    continue_partial: bool = True
    format_fallback: bool = True
    rate_limit_kbps: int = 0

    @property
    def archive_path(self) -> str:
        return str(get_download_archive_file_path())


@dataclass(frozen=True)
class DownloadAdvancedProfile:
    """Collapsed power-user acquisition controls mapped to safe yt-dlp args."""

    cookies_mode: str = "none"
    cookies_browser: str = "chrome"
    cookies_profile: str = ""
    cookies_file: str = ""
    concurrent_fragments: int = 1
    fragment_retries: int = 0
    socket_timeout_seconds: int = 0


_MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv",
    ".mp3", ".m4a", ".aac", ".flac", ".opus", ".wav", ".ogg",
}
_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".flv"}
_SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa", ".sub"}
_POSTPROCESS_AUDIO_FORMATS = {"mp3", "m4a", "aac", "flac", "opus", "wav"}
_POSTPROCESS_CONVERT_FORMATS = {"mp4", "mkv", "webm", "mp3", "m4a", "aac", "flac", "opus"}
_AUDIO_CODEC_BY_EXTENSION = {
    "mp3": "libmp3lame",
    "m4a": "aac",
    "aac": "aac",
    "flac": "flac",
    "opus": "libopus",
    "wav": "pcm_s16le",
}
_CONVERSION_PRESETS = {
    "mp4": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.AAC,
        "audio_only": False,
    },
    "mkv": {
        "video_codec": VideoCodec.H265,
        "audio_codec": AudioCodec.AAC,
        "audio_only": False,
    },
    "webm": {
        "video_codec": VideoCodec.VP9,
        "audio_codec": AudioCodec.OPUS,
        "audio_only": False,
    },
    "mp3": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.MP3,
        "audio_only": True,
    },
    "m4a": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.AAC,
        "audio_only": True,
    },
    "aac": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.AAC,
        "audio_only": True,
    },
    "flac": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.FLAC,
        "audio_only": True,
    },
    "opus": {
        "video_codec": VideoCodec.H264,
        "audio_codec": AudioCodec.OPUS,
        "audio_only": True,
    },
}
_AUDIO_BITRATE_MAP = {
    "64k": AudioBitrate.VERYLOW,
    "96k": AudioBitrate.LOW,
    "128k": AudioBitrate.MEDIUM,
    "192k": AudioBitrate.HIGH,
    "320k": AudioBitrate.VERY_HIGH,
}


class YouTubeDownloader:
    """YouTube videolarını indirmek için ana sınıf - YtDlpRunner kullanır"""

    DEFAULT_RETRIES = 3

    def __init__(
        self,
        ytdlp_path: str = "yt-dlp",
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
    ):
        self._runner = YtDlpRunner(ytdlp_path)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.download_queue: queue.Queue[DownloadRequest] = queue.Queue()
        self.is_worker_active = False
        self.active_downloads: Dict[str, DownloadRequest] = {}
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_requested = False
        self._media_helpers_factory = lambda: MediaHelpers(
            ffmpeg_path=self.ffmpeg_path,
            ffprobe_path=self.ffprobe_path,
        )
        self._converter_factory = lambda: VideoConverter(
            ffmpeg_path=self.ffmpeg_path,
            ffprobe_path=self.ffprobe_path,
        )
        self._subtitle_embedder_factory = lambda: SubtitleEmbedder(
            ffmpeg_path=self.ffmpeg_path,
            ffprobe_path=self.ffprobe_path,
        )

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

    def extract_playlist_entries(
        self,
        url: str,
        quality_label: str = "En İyi",
        *,
        with_details: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get playlist entries, optionally including quality/detail metadata."""
        try:
            entries = self._runner.extract_playlist_entries(
                url,
                with_details=with_details,
                quality_label=quality_label,
            )
            return entries if entries else []
        except Exception as e:
            logger.error(f"Playlist bilgisi alınamadı: {e}")
            return []

    @staticmethod
    def merge_playlist_entry_detail_fields(
        base_entries: List[Dict[str, Any]],
        detailed_entries: List[Dict[str, Any]],
    ) -> int:
        """Merge deferred playlist detail fields into the currently displayed entry list."""
        if not base_entries or not detailed_entries:
            return 0

        detail_keys = (
            "album",
            "channel",
            "uploader",
            "view_count",
            "like_count",
            "upload_date",
            "filesize_mb",
            "resolution",
            "format_note",
            "size_by_quality_mb",
            "resolution_by_quality",
            "format_note_by_quality",
        )

        def identity(entry: Dict[str, Any], index: int) -> tuple[Any, ...]:
            return (
                entry.get("url") or "",
                entry.get("title") or "",
                float(entry.get("duration") or 0.0),
                index,
            )

        detail_by_identity = {
            identity(entry, index): entry
            for index, entry in enumerate(detailed_entries)
        }

        merged_count = 0
        for index, entry in enumerate(base_entries):
            detail_entry = detail_by_identity.get(identity(entry, index))
            if detail_entry is None:
                continue

            updated = False
            for key in detail_keys:
                if key in detail_entry:
                    value = detail_entry.get(key)
                    if entry.get(key) != value:
                        entry[key] = value
                        updated = True
            if updated:
                merged_count += 1

        return merged_count

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

    @staticmethod
    def _normalize_postprocess_profile(
        profile: Optional[Union[Dict[str, Any], DownloadPostProcessProfile]],
    ) -> DownloadPostProcessProfile:
        """Normalize settings-backed post-processing config into a typed profile."""
        if isinstance(profile, DownloadPostProcessProfile):
            return profile

        raw = dict(profile or {}) if isinstance(profile, dict) else {}
        audio_format = str(raw.get("audio_format", "mp3") or "mp3").strip().lower()
        if audio_format not in _POSTPROCESS_AUDIO_FORMATS:
            audio_format = "mp3"

        convert_format = str(raw.get("convert_format", "") or "").strip().lower()
        convert_enabled = bool(raw.get("convert_enabled", raw.get("convert", False)))
        if convert_format not in _POSTPROCESS_CONVERT_FORMATS:
            convert_format = ""
            convert_enabled = False

        return DownloadPostProcessProfile(
            extract_audio=bool(raw.get("extract_audio", False)),
            audio_format=audio_format,
            audio_bitrate=str(raw.get("audio_bitrate", "192k") or "192k").strip().lower(),
            convert_enabled=convert_enabled,
            convert_format=convert_format,
            embed_subtitles=bool(raw.get("embed_subtitles", False)),
        )

    @staticmethod
    def _normalize_robustness_profile(
        profile: Optional[Union[Dict[str, Any], DownloadRobustnessProfile]],
    ) -> DownloadRobustnessProfile:
        """Normalize settings-backed robustness controls into a typed profile."""
        if isinstance(profile, DownloadRobustnessProfile):
            return profile

        raw = dict(profile or {}) if isinstance(profile, dict) else {}
        try:
            rate_limit_kbps = int(raw.get("rate_limit_kbps", 0) or 0)
        except (TypeError, ValueError):
            rate_limit_kbps = 0

        enable_archive = bool(raw.get("enable_archive", True))
        detect_duplicates = bool(raw.get("detect_duplicates", True))
        return DownloadRobustnessProfile(
            enable_archive=bool(enable_archive or detect_duplicates),
            detect_duplicates=detect_duplicates,
            continue_partial=bool(raw.get("continue_partial", True)),
            format_fallback=bool(raw.get("format_fallback", True)),
            rate_limit_kbps=max(0, rate_limit_kbps),
        )

    @staticmethod
    def _normalize_advanced_profile(
        profile: Optional[Union[Dict[str, Any], DownloadAdvancedProfile]],
    ) -> DownloadAdvancedProfile:
        """Normalize collapsed power-user download controls into a typed profile."""
        if isinstance(profile, DownloadAdvancedProfile):
            return profile

        raw = dict(profile or {}) if isinstance(profile, dict) else {}
        cookies_mode = str(raw.get("cookies_mode", "none") or "none").strip().lower()
        if cookies_mode not in {"none", "browser", "file"}:
            cookies_mode = "none"

        cookies_browser = str(raw.get("cookies_browser", "chrome") or "chrome").strip().lower()
        if cookies_browser not in {"chrome", "firefox", "edge", "safari", "brave", "chromium", "opera"}:
            cookies_browser = "chrome"

        cookies_profile = str(raw.get("cookies_profile", "") or "").strip()
        cookies_file = str(raw.get("cookies_file", "") or "").strip()

        def _to_int(key: str, default: int, minimum: int, maximum: int) -> int:
            try:
                value = int(raw.get(key, default) or default)
            except (TypeError, ValueError):
                value = default
            return max(minimum, min(maximum, value))

        return DownloadAdvancedProfile(
            cookies_mode=cookies_mode,
            cookies_browser=cookies_browser,
            cookies_profile=cookies_profile,
            cookies_file=cookies_file,
            concurrent_fragments=_to_int("concurrent_fragments", 1, 1, 8),
            fragment_retries=_to_int("fragment_retries", 0, 0, 50),
            socket_timeout_seconds=_to_int("socket_timeout_seconds", 0, 0, 600),
        )

    @staticmethod
    def _split_download_artifacts(downloaded_files: Iterable[str]) -> Tuple[List[str], List[str]]:
        """Split primary media outputs from supporting subtitle/thumbnail artifacts."""
        media_files: List[str] = []
        supporting_files: List[str] = []

        for raw_path in downloaded_files:
            file_path = str(raw_path or "").strip()
            if not file_path:
                continue
            suffix = Path(file_path).suffix.lower()
            if suffix in _MEDIA_EXTENSIONS:
                media_files.append(file_path)
            else:
                supporting_files.append(file_path)

        if media_files:
            return media_files, supporting_files
        return [str(path) for path in downloaded_files if str(path).strip()], []

    @staticmethod
    def _is_video_file(file_path: str) -> bool:
        return Path(file_path).suffix.lower() in _VIDEO_EXTENSIONS

    @staticmethod
    def _build_postprocess_output_path(
        source_file: str,
        extension: str,
        *,
        suffix_label: str = "",
    ) -> Path:
        """Create a deterministic output path for a derived post-process file."""
        source_path = Path(source_file)
        normalized_extension = str(extension or "").strip().lower().lstrip(".")
        target_extension = f".{normalized_extension}" if normalized_extension else source_path.suffix
        label = f".{suffix_label.strip().strip('.')}" if suffix_label else ""
        candidate = source_path.with_name(f"{source_path.stem}{label}{target_extension}")

        if candidate != source_path and not candidate.exists():
            return candidate

        counter = 2
        while True:
            numbered = source_path.with_name(
                f"{source_path.stem}{label} ({counter}){target_extension}"
            )
            if numbered != source_path and not numbered.exists():
                return numbered
            counter += 1

    @staticmethod
    def _audio_bitrate_enum(value: str) -> AudioBitrate:
        normalized = str(value or "192k").strip().lower()
        return _AUDIO_BITRATE_MAP.get(normalized, AudioBitrate.HIGH)

    def _find_matching_subtitle_file(
        self,
        media_file: str,
        supporting_files: Iterable[str],
        preferred_language: str,
    ) -> Optional[Tuple[str, str]]:
        """Locate the best subtitle sidecar for a media file."""
        media_path = Path(media_file)
        preferred = str(preferred_language or "").strip().lower()
        seen: set[str] = set()
        candidates: List[Tuple[int, int, str, str]] = []

        for raw_path in supporting_files:
            file_path = str(raw_path or "").strip()
            if not file_path:
                continue

            candidate_path = Path(file_path)
            if candidate_path.suffix.lower() not in _SUBTITLE_EXTENSIONS:
                continue
            key = str(candidate_path).lower()
            if key in seen:
                continue
            seen.add(key)

            matches_media = (
                candidate_path.stem == media_path.stem
                or candidate_path.name.startswith(f"{media_path.stem}.")
            )
            if not matches_media:
                continue

            suffixes = [part.lstrip(".").lower() for part in candidate_path.suffixes]
            language = suffixes[-2] if len(suffixes) >= 2 else ""
            preferred_rank = 0 if preferred and language == preferred else 1
            stem_rank = 0 if candidate_path.stem == media_path.stem else 1
            candidates.append((preferred_rank, stem_rank, str(candidate_path), language or preferred or "und"))

        if not candidates:
            return None

        candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        _preferred_rank, _stem_rank, subtitle_path, language = candidates[0]
        return subtitle_path, language

    def _run_extract_audio_step(
        self,
        source_file: str,
        *,
        audio_format: str,
        audio_bitrate: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Tuple[bool, str, str]:
        """Extract audio from a downloaded media file using shared helpers."""
        output_path = self._build_postprocess_output_path(source_file, audio_format)
        result = self._media_helpers_factory().extract_audio(
            input_file=source_file,
            output_file=str(output_path),
            audio_codec=_AUDIO_CODEC_BY_EXTENSION.get(audio_format, "aac"),
            audio_bitrate=audio_bitrate,
            progress_callback=progress_callback,
        )
        if result.success:
            return True, str(output_path), ""
        return False, "", result.error_message or f"Audio extraction failed for {source_file}"

    def _run_convert_step(
        self,
        source_file: str,
        *,
        convert_format: str,
        audio_bitrate: str,
    ) -> Tuple[bool, str, str]:
        """Convert a downloaded media file using the existing converter."""
        preset = _CONVERSION_PRESETS.get(convert_format)
        if not preset:
            return False, "", f"Unsupported conversion target: {convert_format}"

        source_path = Path(source_file)
        if source_path.suffix.lower() == f".{convert_format}":
            return True, str(source_path), ""

        output_path = self._build_postprocess_output_path(source_file, convert_format)
        converter = self._converter_factory()
        success = converter.convert(
            ConversionSettings(
                input_file=source_file,
                output_file=str(output_path),
                video_codec=preset["video_codec"],
                audio_codec=preset["audio_codec"],
                video_quality=VideoQuality.HIGH,
                audio_bitrate=self._audio_bitrate_enum(audio_bitrate),
                audio_only=bool(preset.get("audio_only", False)),
            )
        )
        if success:
            return True, str(output_path), ""
        return False, "", f"Conversion failed for {source_file}"

    def _run_embed_subtitles_step(
        self,
        source_file: str,
        *,
        supporting_files: Iterable[str],
        preferred_language: str,
    ) -> Tuple[bool, str, str, bool]:
        """Embed matching subtitle sidecars into a video file when available."""
        match = self._find_matching_subtitle_file(source_file, supporting_files, preferred_language)
        if match is None:
            return True, source_file, "", False

        subtitle_file, subtitle_language = match
        output_path = self._build_postprocess_output_path(
            source_file,
            Path(source_file).suffix.lower().lstrip("."),
            suffix_label="subtitled",
        )
        success = self._subtitle_embedder_factory().embed_soft(
            video_file=source_file,
            subtitle_file=subtitle_file,
            output_file=str(output_path),
            language=subtitle_language,
        )
        if success:
            return True, str(output_path), "", True
        return False, "", f"Subtitle embedding failed for {source_file}", True

    @staticmethod
    def _build_robustness_args(profile: DownloadRobustnessProfile) -> List[str]:
        """Build yt-dlp arguments for archive tracking, resume, and rate limiting."""
        args: List[str] = []
        if profile.enable_archive:
            args.extend(["--download-archive", profile.archive_path])
        if profile.continue_partial:
            args.extend(["--continue", "--part", "--no-abort-on-unavailable-fragments"])
        if profile.rate_limit_kbps > 0:
            args.extend(["--limit-rate", f"{profile.rate_limit_kbps}K"])
        return args

    @staticmethod
    def _build_advanced_args(profile: DownloadAdvancedProfile) -> List[str]:
        """Build yt-dlp arguments for collapsed power-user acquisition settings."""
        args: List[str] = []
        if profile.cookies_mode == "browser":
            browser_spec = profile.cookies_browser
            if profile.cookies_profile:
                browser_spec = f"{browser_spec}:{profile.cookies_profile}"
            args.extend(["--cookies-from-browser", browser_spec])
        elif profile.cookies_mode == "file" and profile.cookies_file:
            args.extend(["--cookies", profile.cookies_file])

        if profile.concurrent_fragments > 1:
            args.extend(["--concurrent-fragments", str(profile.concurrent_fragments)])
        if profile.fragment_retries > 0:
            args.extend(["--fragment-retries", str(profile.fragment_retries)])
        if profile.socket_timeout_seconds > 0:
            args.extend(["--socket-timeout", str(profile.socket_timeout_seconds)])
        return args

    @staticmethod
    def _build_fallback_format_specs(
        initial_format_spec: str,
        format_type: DownloadFormat,
        quality: DownloadQuality,
    ) -> List[str]:
        """Return fallback format specs when the preferred spec is unavailable."""
        candidates: List[str] = []
        if quality != DownloadQuality.BEST:
            candidates.append(format_type.format_spec)
        if format_type in _AUDIO_FORMATS:
            candidates.extend([DownloadQuality.AUDIO_ONLY.value, "bestaudio/best"])
        else:
            candidates.extend([DownloadQuality.BEST.value, "best"])

        fallback_specs: List[str] = []
        seen: set[str] = {initial_format_spec}
        for candidate in candidates:
            normalized = str(candidate or "").strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            fallback_specs.append(normalized)
        return fallback_specs

    def _run_postprocess_pipeline(
        self,
        media_files: List[str],
        supporting_files: List[str],
        *,
        profile: DownloadPostProcessProfile,
        preferred_subtitle_language: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> PostProcessPipelineResult:
        """Apply the ordered post-download pipeline to primary media outputs."""
        current_outputs = [str(path) for path in media_files if path]
        metadata: Dict[str, Any] = {
            "profile": {
                "extract_audio": profile.extract_audio,
                "audio_format": profile.audio_format,
                "audio_bitrate": profile.audio_bitrate,
                "convert_enabled": profile.convert_enabled,
                "convert_format": profile.convert_format,
                "embed_subtitles": profile.embed_subtitles,
            },
            "executed_steps": [],
            "skipped_steps": [],
            "generated_files": [],
        }

        if not profile.enabled or not current_outputs:
            return PostProcessPipelineResult(
                success=True,
                output_files=current_outputs,
                supporting_files=list(supporting_files),
                metadata=metadata,
            )

        if profile.extract_audio:
            if progress_callback:
                progress_callback(100, "Post-process: extract audio")
            next_outputs: List[str] = []
            generated_any = False
            for source_file in current_outputs:
                if not self._is_video_file(source_file):
                    next_outputs.append(source_file)
                    continue
                success, output_path, error_message = self._run_extract_audio_step(
                    source_file,
                    audio_format=profile.audio_format,
                    audio_bitrate=profile.audio_bitrate,
                    progress_callback=progress_callback,
                )
                if not success:
                    return PostProcessPipelineResult(
                        success=False,
                        output_files=current_outputs,
                        supporting_files=list(supporting_files),
                        metadata=metadata,
                        error_message=error_message,
                    )
                next_outputs.append(output_path)
                metadata["generated_files"].append(output_path)
                generated_any = True
            current_outputs = next_outputs
            if generated_any:
                metadata["executed_steps"].append("extract_audio")
            else:
                metadata["skipped_steps"].append("extract_audio")

        if profile.convert_enabled and profile.convert_format:
            if progress_callback:
                progress_callback(100, "Post-process: convert")
            next_outputs = []
            generated_any = False
            for source_file in current_outputs:
                success, output_path, error_message = self._run_convert_step(
                    source_file,
                    convert_format=profile.convert_format,
                    audio_bitrate=profile.audio_bitrate,
                )
                if not success:
                    return PostProcessPipelineResult(
                        success=False,
                        output_files=current_outputs,
                        supporting_files=list(supporting_files),
                        metadata=metadata,
                        error_message=error_message,
                    )
                next_outputs.append(output_path)
                if output_path != source_file:
                    metadata["generated_files"].append(output_path)
                    generated_any = True
            current_outputs = next_outputs
            if generated_any:
                metadata["executed_steps"].append("convert")
            else:
                metadata["skipped_steps"].append("convert")

        if profile.embed_subtitles:
            if progress_callback:
                progress_callback(100, "Post-process: embed subtitles")
            next_outputs = []
            embedded_any = False
            for source_file in current_outputs:
                if not self._is_video_file(source_file):
                    next_outputs.append(source_file)
                    continue
                success, output_path, error_message, attempted = self._run_embed_subtitles_step(
                    source_file,
                    supporting_files=supporting_files,
                    preferred_language=preferred_subtitle_language,
                )
                if not success:
                    return PostProcessPipelineResult(
                        success=False,
                        output_files=current_outputs,
                        supporting_files=list(supporting_files),
                        metadata=metadata,
                        error_message=error_message,
                    )
                next_outputs.append(output_path)
                if attempted and output_path != source_file:
                    metadata["generated_files"].append(output_path)
                    embedded_any = True
            current_outputs = next_outputs
            if embedded_any:
                metadata["executed_steps"].append("embed_subtitles")
            else:
                metadata["skipped_steps"].append("embed_subtitles")

        return PostProcessPipelineResult(
            success=True,
            output_files=current_outputs,
            supporting_files=list(supporting_files),
            metadata=metadata,
        )

    def download(self, request: Optional[DownloadRequest] = None, **kwargs) -> DownloadResult:
        """
        Video indir

        Args:
            request: İndirme isteği (DownloadRequest)
            **kwargs: Geriye dönük uyumluluk için eski argümanlar

        Returns:
            DownloadResult: İndirme sonucu
        """
        if request is None:
            if 'format_type' in kwargs:
                kwargs['format'] = kwargs.pop('format_type')
            request = DownloadRequest(**kwargs)

        url = request.url
        output_dir = request.output_dir
        format_type = request.format
        quality = request.quality
        progress_callback = request.progress_callback
        retries = request.retries
        embed_metadata = request.embed_metadata
        embed_lyrics = request.embed_lyrics
        auto_sort = request.auto_sort
        auto_sort_enabled = request.auto_sort_enabled
        auto_sort_mode = request.auto_sort_mode
        audio_bitrate = request.audio_bitrate
        naming_preset = request.naming_preset
        filename_template = request.filename_template
        auto_subtitle_download = request.auto_subtitle_download
        preferred_subtitle_language = request.preferred_subtitle_language
        subtitle_fallback_language = request.subtitle_fallback_language
        subtitle_include_auto_generated = request.subtitle_include_auto_generated
        auto_embed_subtitles = request.auto_embed_subtitles
        postprocess_profile = request.postprocess_profile
        robustness_profile = request.robustness_profile
        advanced_profile = request.advanced_profile

        logger.info(f"İndirme başlatılıyor: {url}")

        normalized_postprocess = self._normalize_postprocess_profile(postprocess_profile)
        normalized_robustness = self._normalize_robustness_profile(robustness_profile)
        normalized_advanced = self._normalize_advanced_profile(advanced_profile)
        sort_enabled = auto_sort if auto_sort_enabled is None else auto_sort_enabled
        needs_video_info = bool(
            sort_enabled
            or (embed_metadata and format_type in [DownloadFormat.MP3, DownloadFormat.M4A])
            or template_needs_video_info(naming_preset, filename_template)
            or auto_subtitle_download
            or normalized_robustness.detect_duplicates
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
        extra_args.extend(self._build_robustness_args(normalized_robustness))
        extra_args.extend(self._build_advanced_args(normalized_advanced))

        result = self._runner.download(
            url=url,
            output_dir=resolved_output_dir,
            filename_template="%(title)s.%(ext)s",
            format_spec=format_spec,
            extra_args=extra_args,
            retries=retries,
            progress_callback=progress_callback
        )

        if (not result.success) and normalized_robustness.format_fallback:
            for fallback_format_spec in self._build_fallback_format_specs(format_spec, format_type, quality):
                fallback_result = self._runner.download(
                    url=url,
                    output_dir=resolved_output_dir,
                    filename_template="%(title)s.%(ext)s",
                    format_spec=fallback_format_spec,
                    extra_args=extra_args,
                    retries=retries,
                    progress_callback=progress_callback,
                )
                if fallback_result.success:
                    fallback_result.metadata.setdefault("format_fallback_used", True)
                    fallback_result.metadata.setdefault("fallback_format_spec", fallback_format_spec)
                    result = fallback_result
                    break
                result = fallback_result

        if result.success:
            downloaded_files = result.metadata.get('downloaded_files', [])

            if format_type in _AUDIO_FORMATS and embed_metadata:
                self._apply_audio_metadata(downloaded_files, video_info, embed_lyrics)

            renamed_files = apply_naming_template(
                downloaded_files,
                output_dir=resolved_output_dir,
                naming_preset=naming_preset,
                custom_template=filename_template,
                video_info=video_info,
                resolution=self._resolve_naming_resolution(video_info, quality, format_type),
            )
            media_files, supporting_files = self._split_download_artifacts(renamed_files)
            postprocess_result = self._run_postprocess_pipeline(
                media_files,
                supporting_files,
                profile=normalized_postprocess,
                preferred_subtitle_language=preferred_subtitle_language,
                progress_callback=progress_callback,
            )
            if not postprocess_result.success:
                logger.error(f"İndirme sonrası işleme başarısız: {postprocess_result.error_message}")
                return DownloadResult(
                    success=False,
                    url=url,
                    output_files=postprocess_result.output_files,
                    error_message=postprocess_result.error_message,
                    title=str((video_info or {}).get('title') or Path(media_files[0]).stem if media_files else ""),
                    duration=float((video_info or {}).get('duration') or 0.0),
                    metadata={
                        "downloaded_files": downloaded_files,
                        "renamed_files": renamed_files,
                        "media_files": media_files,
                        "supporting_files": supporting_files,
                        "postprocess": postprocess_result.metadata,
                    },
                )

            final_output_files = postprocess_result.output_files or media_files or renamed_files
            metadata = {
                "downloaded_files": downloaded_files,
                "renamed_files": renamed_files,
                "media_files": media_files,
                "supporting_files": postprocess_result.supporting_files,
                "postprocess": postprocess_result.metadata,
                "robustness": {
                    "enable_archive": normalized_robustness.enable_archive,
                    "detect_duplicates": normalized_robustness.detect_duplicates,
                    "continue_partial": normalized_robustness.continue_partial,
                    "format_fallback": normalized_robustness.format_fallback,
                    "rate_limit_kbps": normalized_robustness.rate_limit_kbps,
                    "archive_skipped": bool(result.metadata.get("archive_skipped", False)),
                    "format_fallback_used": bool(result.metadata.get("format_fallback_used", False)),
                    "fallback_format_spec": str(result.metadata.get("fallback_format_spec", "") or ""),
                },
            }
            enriched_metadata = build_enriched_download_metadata(
                url=url,
                video_info=video_info,
                output_files=final_output_files,
                supporting_files=postprocess_result.supporting_files,
                format_name=format_type.extension,
                quality_name=self._quality_label_for_naming(quality),
                postprocess_metadata=postprocess_result.metadata,
            )
            metadata.update(enriched_metadata)
            normalized_title = str(
                ((metadata.get("normalized") or {}).get("title"))
                or (video_info or {}).get('title')
                or (Path(final_output_files[0]).stem if final_output_files else "")
            )

            if result.metadata.get("archive_skipped") and not final_output_files:
                logger.info("İndirme arşiv nedeniyle atlandı: %s", url)
            else:
                logger.info(f"İndirme tamamlandı: {final_output_files}")
            return DownloadResult(
                success=True,
                url=url,
                output_files=final_output_files,
                title=normalized_title,
                duration=float((video_info or {}).get('duration') or 0.0),
                metadata=metadata,
            )
        else:
            logger.error(f"İndirme başarısız: {result.error_message}")
            return DownloadResult(
                success=False,
                url=url,
                output_files=[],
                error_message=result.error_message
            )

    def queue_download(self, request: DownloadRequest) -> None:
        """İndirme kuyruğuna görev ekle"""
        self.download_queue.put(request)
        logger.info(f"Kuyruğa eklendi: {request.url}")

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
                request = self.download_queue.get(timeout=1.0)
                self.active_downloads[request.url] = request

                result = self.download(request)

                del self.active_downloads[request.url]
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

