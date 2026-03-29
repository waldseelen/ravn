"""
Platform desteği genişlemesi.

Yeni platformlar:
- TikTok
- Instagram (post + reel)
- Twitch (VOD + clip)
- Twitter/X
- Genel yt-dlp URL fallback
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from ravn_app.core.runners import YtDlpRunner


logger = logging.getLogger(__name__)


class Platform(Enum):
    """Desteklenen video platformları."""

    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    DAILYMOTION = "dailymotion"
    TWITCH = "twitch"
    BILIBILI = "bilibili"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    TWITTER = "twitter"
    GENERIC = "generic"


class PlatformDownloader(ABC):
    """Platform indirici arayüzü."""

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Platform türü."""

    @abstractmethod
    def can_download(self, url: str) -> bool:
        """URL'nin bu platform tarafından desteklenip desteklenmediğini kontrol et."""

    @abstractmethod
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Video bilgilerini al."""

    @abstractmethod
    def download(self, url: str, output_path: str, options: Dict[str, Any]) -> bool:
        """Videoyu indir."""


class YtDlpPlatformDownloader(PlatformDownloader):
    """YtDlpRunner tabanlı genel platform indirici."""

    def __init__(
        self,
        platform: Platform,
        platform_label: str,
        domains: List[str],
        yt_dlp_path: str = "yt-dlp",
        url_patterns: Optional[List[str]] = None,
    ):
        self._platform = platform
        self._platform_label = platform_label
        self._domains = [domain.lower() for domain in domains]
        self._url_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in (url_patterns or [])
        ]
        self._runner = YtDlpRunner(yt_dlp_path)

    @property
    def platform(self) -> Platform:
        return self._platform

    def can_download(self, url: str) -> bool:
        normalized = (url or "").strip().lower()
        if not normalized.startswith(("http://", "https://")):
            return False

        if any(domain in normalized for domain in self._domains):
            return True

        return any(pattern.search(normalized) for pattern in self._url_patterns)

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        info = self._runner.extract_info(url)
        if info is None:
            return None

        return {
            "title": info.get("title", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "thumbnail": info.get("thumbnail", ""),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "formats": len(info.get("formats", [])),
            "ext": info.get("ext", ""),
            "platform": self.platform.value,
            "extractor": info.get("extractor", ""),
            "platform_label": self._platform_label,
        }

    def download(self, url: str, output_path: str, options: Dict[str, Any]) -> bool:
        os.makedirs(output_path, exist_ok=True)
        options = options or {}

        extra_args: List[str] = []
        if options.get("save_info"):
            extra_args.append("--write-info-json")
        if options.get("subtitles"):
            extra_args.append("--write-subs")
        if options.get("subtitle_langs"):
            extra_args.extend(["--sub-langs", str(options["subtitle_langs"])])
        if options.get("thumbnail"):
            extra_args.append("--write-thumbnail")
        extra_args.append("--skip-unavailable-fragments")

        result = self._runner.download(
            url=url,
            output_dir=output_path,
            filename_template=options.get("filename_template", "%(title)s.%(ext)s"),
            format_spec=options.get("format", "best"),
            extra_args=extra_args,
            retries=int(options.get("retries", YtDlpRunner.DEFAULT_RETRIES)),
            timeout=int(options.get("timeout", YtDlpRunner.DEFAULT_TIMEOUT)),
        )

        if result.success:
            logger.info("%s indirmesi başarılı: %s", self._platform_label, output_path)
            return True

        logger.error("%s indirme hatası: %s", self._platform_label, result.error_message)
        return False


class YouTubeDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.YOUTUBE,
            platform_label="YouTube",
            domains=["youtube.com", "youtu.be"],
            yt_dlp_path=yt_dlp_path,
        )


class VimeoDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.VIMEO,
            platform_label="Vimeo",
            domains=["vimeo.com"],
            yt_dlp_path=yt_dlp_path,
        )


class DailymotionDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.DAILYMOTION,
            platform_label="Dailymotion",
            domains=["dailymotion.com", "dai.ly"],
            yt_dlp_path=yt_dlp_path,
        )


class TikTokDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.TIKTOK,
            platform_label="TikTok",
            domains=["tiktok.com", "vm.tiktok.com"],
            yt_dlp_path=yt_dlp_path,
        )


class InstagramDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.INSTAGRAM,
            platform_label="Instagram",
            domains=["instagram.com"],
            yt_dlp_path=yt_dlp_path,
            url_patterns=[r"instagram\.com/(reel|p)/"],
        )

    def can_download(self, url: str) -> bool:
        normalized = (url or "").strip().lower()
        if not normalized.startswith(("http://", "https://")):
            return False
        return bool(re.search(r"instagram\.com/(reel|p)/", normalized))


class TwitchDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.TWITCH,
            platform_label="Twitch",
            domains=["twitch.tv", "clips.twitch.tv"],
            yt_dlp_path=yt_dlp_path,
            url_patterns=[
                r"twitch\.tv/videos/\d+",
                r"clips\.twitch\.tv/[A-Za-z0-9_-]+",
            ],
        )

    def can_download(self, url: str) -> bool:
        normalized = (url or "").strip().lower()
        if not normalized.startswith(("http://", "https://")):
            return False
        return bool(
            re.search(r"twitch\.tv/videos/\d+", normalized)
            or re.search(r"clips\.twitch\.tv/[A-Za-z0-9_-]+", normalized)
        )


class TwitterXDownloader(YtDlpPlatformDownloader):
    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.TWITTER,
            platform_label="Twitter/X",
            domains=["twitter.com", "x.com"],
            yt_dlp_path=yt_dlp_path,
        )


class GenericYtDlpDownloader(YtDlpPlatformDownloader):
    """Bilinen platform eşleşmezse tüm yt-dlp URL'leri için fallback."""

    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        super().__init__(
            platform=Platform.GENERIC,
            platform_label="Generic URL",
            domains=[],
            yt_dlp_path=yt_dlp_path,
            url_patterns=[r"^https?://"],
        )

    def can_download(self, url: str) -> bool:
        normalized = (url or "").strip().lower()
        return bool(re.match(r"^https?://", normalized))


class PlatformManager:
    """Platform yöneticisi - tüm platform indirici yönetimi."""

    _BADGE_MAP: Dict[Platform, Dict[str, str]] = {
        Platform.YOUTUBE: {"icon": "YT", "label": "YouTube", "color": "#ef4444"},
        Platform.VIMEO: {"icon": "VI", "label": "Vimeo", "color": "#14b8a6"},
        Platform.DAILYMOTION: {"icon": "DM", "label": "Dailymotion", "color": "#6366f1"},
        Platform.TIKTOK: {"icon": "TT", "label": "TikTok", "color": "#f97316"},
        Platform.INSTAGRAM: {"icon": "IG", "label": "Instagram", "color": "#ec4899"},
        Platform.TWITCH: {"icon": "TW", "label": "Twitch", "color": "#a855f7"},
        Platform.TWITTER: {"icon": "X", "label": "Twitter/X", "color": "#60a5fa"},
        Platform.GENERIC: {"icon": "URL", "label": "Generic", "color": "#64748b"},
    }

    def __init__(self):
        self.downloaders: Dict[Platform, PlatformDownloader] = {}
        self._registration_order: List[Platform] = []
        self._register_default_downloaders()

    def _register_default_downloaders(self):
        """Varsayılan platform indiricilerini kaydet."""
        self.register_downloader(YouTubeDownloader())
        self.register_downloader(VimeoDownloader())
        self.register_downloader(DailymotionDownloader())
        self.register_downloader(TikTokDownloader())
        self.register_downloader(InstagramDownloader())
        self.register_downloader(TwitchDownloader())
        self.register_downloader(TwitterXDownloader())
        self.register_downloader(GenericYtDlpDownloader())
        logger.info("Varsayılan platform indiricileri kaydedildi")

    def register_downloader(self, downloader: PlatformDownloader):
        """Yeni platform indirici kaydet."""
        self.downloaders[downloader.platform] = downloader
        if downloader.platform not in self._registration_order:
            self._registration_order.append(downloader.platform)
        logger.info("Platform indirici kaydedildi: %s", downloader.platform.value)

    def find_downloader(self, url: str) -> Optional[PlatformDownloader]:
        """URL için uygun indiriciyi bul."""
        for platform in self._registration_order:
            downloader = self.downloaders.get(platform)
            if downloader and downloader.can_download(url):
                return downloader
        return None

    def detect_platform(self, url: str) -> Optional[Platform]:
        """URL için platformu tespit et."""
        downloader = self.find_downloader(url)
        if downloader is None:
            return None
        return downloader.platform

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Video bilgilerini al (otomatik platform tespiti)."""
        downloader = self.find_downloader(url)
        if downloader:
            return downloader.get_video_info(url)
        return None

    def download(
        self,
        url: str,
        output_path: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Videoyu indir (otomatik platform tespiti)."""
        downloader = self.find_downloader(url)
        if not downloader:
            logger.error("Desteklenmeyen platform: %s", url)
            return False

        return downloader.download(url, output_path, options or {})

    def get_supported_platforms(self) -> List[str]:
        """Desteklenen platformları listele."""
        return [platform.value for platform in self._registration_order]

    def get_platform_badge(self, url: str) -> Dict[str, str]:
        """URL için badge/icon bilgisi döndür."""
        platform = self.detect_platform(url)
        if platform is None:
            return {"icon": "?", "label": "Bilinmiyor", "color": "#64748b", "platform": "unknown"}

        badge = dict(self._BADGE_MAP.get(platform, self._BADGE_MAP[Platform.GENERIC]))
        badge["platform"] = platform.value
        return badge
