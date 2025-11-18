"""
Platform desteği genişlemesi - Vimeo, Dailymotion ve diğer platformlar
"""

import os
import logging
from typing import Dict, List, Optional, Any
from enum import Enum
from abc import ABC, abstractmethod


logger = logging.getLogger(__name__)


class Platform(Enum):
    """Desteklenen video platformları"""
    YOUTUBE = "youtube"
    VIMEO = "vimeo"
    DAILYMOTION = "dailymotion"
    TWITCH = "twitch"
    BILIBILI = "bilibili"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class PlatformDownloader(ABC):
    """Platform indirici arayüzü"""

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """Platform türü"""
        pass

    @abstractmethod
    def can_download(self, url: str) -> bool:
        """URL'nin bu platform tarafından desteklenip desteklenmediğini kontrol et"""
        pass

    @abstractmethod
    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Video bilgilerini al"""
        pass

    @abstractmethod
    def download(self, url: str, output_path: str, options: Dict[str, Any]) -> bool:
        """Videoyu indir"""
        pass


class VimeoDownloader(PlatformDownloader):
    """Vimeo indirici"""

    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        self.yt_dlp_path = yt_dlp_path

    @property
    def platform(self) -> Platform:
        return Platform.VIMEO

    def can_download(self, url: str) -> bool:
        """Vimeo URL'sini kontrol et"""
        return "vimeo.com" in url.lower()

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Vimeo video bilgilerini al"""
        try:
            import subprocess
            cmd = [
                self.yt_dlp_path,
                '-j',  # JSON çıktı
                '--no-warnings',
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'formats': len(info.get('formats', [])),
                    'ext': info.get('ext', 'mp4'),
                    'platform': 'vimeo'
                }
        except Exception as e:
            logger.error(f"Vimeo bilgi hatası: {str(e)}")

        return None

    def download(self, url: str, output_path: str, options: Dict[str, Any]) -> bool:
        """Vimeo videosunu indir"""
        try:
            import subprocess

            os.makedirs(output_path, exist_ok=True)

            cmd = [
                self.yt_dlp_path,
                '-f', options.get('format', 'best'),
                '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
                '--write-info-json' if options.get('save_info') else '',
                '--write-subs' if options.get('subtitles') else '',
                '--skip-unavailable-fragments',
            ]

            # Boş argümanları kaldır
            cmd = [arg for arg in cmd if arg]
            cmd.append(url)

            logger.info(f"Vimeo indirmesi başlanıyor: {url}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                logger.info(f"Vimeo indirmesi başarılı: {output_path}")
                return True
            else:
                logger.error(f"Vimeo indirme hatası: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Vimeo indirmesi zaman aşımına uğradı")
            return False
        except Exception as e:
            logger.error(f"Vimeo indirme hatası: {str(e)}")
            return False


class DailymotionDownloader(PlatformDownloader):
    """Dailymotion indirici"""

    def __init__(self, yt_dlp_path: str = "yt-dlp"):
        self.yt_dlp_path = yt_dlp_path

    @property
    def platform(self) -> Platform:
        return Platform.DAILYMOTION

    def can_download(self, url: str) -> bool:
        """Dailymotion URL'sini kontrol et"""
        return "dailymotion.com" in url.lower() or "dai.ly" in url.lower()

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Dailymotion video bilgilerini al"""
        try:
            import subprocess
            cmd = [
                self.yt_dlp_path,
                '-j',
                '--no-warnings',
                url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', ''),
                    'thumbnail': info.get('thumbnail', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'ext': info.get('ext', 'mp4'),
                    'platform': 'dailymotion'
                }
        except Exception as e:
            logger.error(f"Dailymotion bilgi hatası: {str(e)}")

        return None

    def download(self, url: str, output_path: str, options: Dict[str, Any]) -> bool:
        """Dailymotion videosunu indir"""
        try:
            import subprocess

            os.makedirs(output_path, exist_ok=True)

            cmd = [
                self.yt_dlp_path,
                '-f', options.get('format', 'best'),
                '-o', os.path.join(output_path, '%(title)s.%(ext)s'),
                '--write-info-json' if options.get('save_info') else '',
                '--write-subs' if options.get('subtitles') else '',
                '--skip-unavailable-fragments',
            ]

            cmd = [arg for arg in cmd if arg]
            cmd.append(url)

            logger.info(f"Dailymotion indirmesi başlanıyor: {url}")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                logger.info(f"Dailymotion indirmesi başarılı: {output_path}")
                return True
            else:
                logger.error(f"Dailymotion indirme hatası: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Dailymotion indirmesi zaman aşımına uğradı")
            return False
        except Exception as e:
            logger.error(f"Dailymotion indirme hatası: {str(e)}")
            return False


class PlatformManager:
    """Platform yöneticisi - tüm platform indirici yönetimi"""

    def __init__(self):
        self.downloaders: Dict[Platform, PlatformDownloader] = {}
        self._register_default_downloaders()

    def _register_default_downloaders(self):
        """Varsayılan platform indiricilerini kaydet"""
        self.register_downloader(VimeoDownloader())
        self.register_downloader(DailymotionDownloader())
        logger.info("Varsayılan platform indiricileri kaydedildi")

    def register_downloader(self, downloader: PlatformDownloader):
        """Yeni platform indirici kaydet"""
        self.downloaders[downloader.platform] = downloader
        logger.info(f"Platform indirici kaydedildi: {downloader.platform.value}")

    def find_downloader(self, url: str) -> Optional[PlatformDownloader]:
        """URL için uygun indiriciyi bul"""
        for downloader in self.downloaders.values():
            if downloader.can_download(url):
                return downloader
        return None

    def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Video bilgilerini al (otomatik platform tespiti)"""
        downloader = self.find_downloader(url)
        if downloader:
            return downloader.get_video_info(url)
        return None

    def download(self, url: str, output_path: str, options: Dict[str, Any] = None) -> bool:
        """Videoyu indir (otomatik platform tespiti)"""
        downloader = self.find_downloader(url)
        if not downloader:
            logger.error(f"Desteklenmeyen platform: {url}")
            return False

        options = options or {}
        return downloader.download(url, output_path, options)

    def get_supported_platforms(self) -> List[str]:
        """Desteklenen platformları listele"""
        return [p.value for p in self.downloaders.keys()]
