"""
Platform desteği testleri - Vimeo, Dailymotion ve diğer platformlar
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from pathlib import Path

from ravn_app.core.platform_support import (
    Platform,
    PlatformDownloader,
    VimeoDownloader,
    DailymotionDownloader,
    PlatformManager,
)


class TestVimeoDownloader:
    """Vimeo indirici testleri"""

    def test_vimeo_platform_property(self):
        """Vimeo platform türü doğru olmalı"""
        downloader = VimeoDownloader()
        assert downloader.platform == Platform.VIMEO

    def test_vimeo_can_download_valid_url(self):
        """Geçerli Vimeo URL'si tanınmalı"""
        downloader = VimeoDownloader()
        assert downloader.can_download("https://vimeo.com/123456789")
        assert downloader.can_download("https://www.vimeo.com/channels/music/123456789")

    def test_vimeo_can_download_invalid_url(self):
        """Geçersiz URL reddedilmeli"""
        downloader = VimeoDownloader()
        assert not downloader.can_download("https://youtube.com/watch?v=123")
        assert not downloader.can_download("https://example.com")

    @patch('subprocess.run')
    def test_vimeo_get_video_info_success(self, mock_run, tmp_path):
        """Vimeo video bilgilerini başarıyla al"""
        video_info = {
            'title': 'Test Video',
            'duration': 120,
            'uploader': 'Test Creator',
            'thumbnail': 'https://example.com/thumb.jpg',
            'formats': [{'format_id': 'best'}],
            'ext': 'mp4'
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(video_info)
        )

        downloader = VimeoDownloader()
        info = downloader.get_video_info("https://vimeo.com/123456789")

        assert info is not None
        assert info['title'] == 'Test Video'
        assert info['duration'] == 120
        assert info['platform'] == 'vimeo'
        assert info['formats'] == 1

    @patch('subprocess.run')
    def test_vimeo_get_video_info_failure(self, mock_run):
        """Vimeo bilgi hatası ele alınmalı"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr='Error'
        )

        downloader = VimeoDownloader()
        info = downloader.get_video_info("https://vimeo.com/invalid")

        assert info is None

    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_vimeo_download_success(self, mock_makedirs, mock_run, tmp_path):
        """Vimeo videosunu başarıyla indir"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        downloader = VimeoDownloader()
        options = {'format': 'best', 'save_info': True, 'subtitles': True}

        result = downloader.download(
            "https://vimeo.com/123456789",
            str(tmp_path),
            options
        )

        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_vimeo_download_failure(self, mock_makedirs, mock_run):
        """Vimeo indirme hatası ele alınmalı"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr='Download failed'
        )

        downloader = VimeoDownloader()
        result = downloader.download(
            "https://vimeo.com/123456789",
            "/tmp/path",
            {}
        )

        assert result is False

    @patch('subprocess.run')
    def test_vimeo_download_timeout(self, mock_run):
        """Vimeo indirme zaman aşımı"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 3600)

        downloader = VimeoDownloader()
        result = downloader.download(
            "https://vimeo.com/123456789",
            "/tmp/path",
            {}
        )

        assert result is False


class TestDailymotionDownloader:
    """Dailymotion indirici testleri"""

    def test_dailymotion_platform_property(self):
        """Dailymotion platform türü doğru olmalı"""
        downloader = DailymotionDownloader()
        assert downloader.platform == Platform.DAILYMOTION

    def test_dailymotion_can_download_valid_url(self):
        """Geçerli Dailymotion URL'si tanınmalı"""
        downloader = DailymotionDownloader()
        assert downloader.can_download("https://www.dailymotion.com/video/x123456")
        assert downloader.can_download("https://dai.ly/x123456")

    def test_dailymotion_can_download_invalid_url(self):
        """Geçersiz URL reddedilmeli"""
        downloader = DailymotionDownloader()
        assert not downloader.can_download("https://youtube.com/watch?v=123")
        assert not downloader.can_download("https://example.com")

    @patch('subprocess.run')
    def test_dailymotion_get_video_info_success(self, mock_run):
        """Dailymotion video bilgilerini başarıyla al"""
        video_info = {
            'title': 'Dailymotion Video',
            'duration': 180,
            'uploader': 'DM Creator',
            'thumbnail': 'https://example.com/dm_thumb.jpg',
            'view_count': 10000,
            'like_count': 500,
            'ext': 'mp4'
        }

        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps(video_info)
        )

        downloader = DailymotionDownloader()
        info = downloader.get_video_info("https://www.dailymotion.com/video/x123456")

        assert info is not None
        assert info['title'] == 'Dailymotion Video'
        assert info['view_count'] == 10000
        assert info['platform'] == 'dailymotion'

    @patch('subprocess.run')
    def test_dailymotion_get_video_info_failure(self, mock_run):
        """Dailymotion bilgi hatası ele alınmalı"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr='Error'
        )

        downloader = DailymotionDownloader()
        info = downloader.get_video_info("https://www.dailymotion.com/invalid")

        assert info is None

    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_dailymotion_download_success(self, mock_makedirs, mock_run, tmp_path):
        """Dailymotion videosunu başarıyla indir"""
        mock_run.return_value = Mock(returncode=0, stdout='', stderr='')

        downloader = DailymotionDownloader()
        options = {'format': 'best[ext=mp4]', 'save_info': False}

        result = downloader.download(
            "https://www.dailymotion.com/video/x123456",
            str(tmp_path),
            options
        )

        assert result is True

    @patch('subprocess.run')
    @patch('os.makedirs')
    def test_dailymotion_download_failure(self, mock_makedirs, mock_run):
        """Dailymotion indirme hatası ele alınmalı"""
        mock_run.return_value = Mock(
            returncode=1,
            stderr='Download failed'
        )

        downloader = DailymotionDownloader()
        result = downloader.download(
            "https://www.dailymotion.com/video/x123456",
            "/tmp/path",
            {}
        )

        assert result is False


class TestPlatformManager:
    """Platform yöneticisi testleri"""

    def test_platform_manager_initialization(self):
        """Platform yöneticisi başlatılmalı"""
        manager = PlatformManager()
        assert manager.downloaders is not None
        assert len(manager.downloaders) > 0

    def test_platform_manager_has_vimeo(self):
        """Vimeo indirici kaydedilmeli"""
        manager = PlatformManager()
        assert Platform.VIMEO in manager.downloaders

    def test_platform_manager_has_dailymotion(self):
        """Dailymotion indirici kaydedilmeli"""
        manager = PlatformManager()
        assert Platform.DAILYMOTION in manager.downloaders

    def test_platform_manager_find_vimeo_downloader(self):
        """Vimeo URL için indirici bulunmalı"""
        manager = PlatformManager()
        downloader = manager.find_downloader("https://vimeo.com/123456")

        assert downloader is not None
        assert downloader.platform == Platform.VIMEO

    def test_platform_manager_find_dailymotion_downloader(self):
        """Dailymotion URL için indirici bulunmalı"""
        manager = PlatformManager()
        downloader = manager.find_downloader("https://www.dailymotion.com/video/x123")

        assert downloader is not None
        assert downloader.platform == Platform.DAILYMOTION

    def test_platform_manager_find_unknown_downloader(self):
        """Bilinmeyen platform için None dönmeli"""
        manager = PlatformManager()
        downloader = manager.find_downloader("https://unknown.com/video")

        assert downloader is None

    def test_platform_manager_register_custom_downloader(self):
        """Özel indirici kaydedilebilmeli"""
        manager = PlatformManager()

        # Mock özel indirici
        custom_downloader = Mock(spec=PlatformDownloader)
        custom_downloader.platform = Platform.TWITCH

        manager.register_downloader(custom_downloader)

        assert Platform.TWITCH in manager.downloaders

    @patch.object(VimeoDownloader, 'get_video_info')
    def test_platform_manager_get_video_info_vimeo(self, mock_get_info):
        """Manager Vimeo video bilgisini al"""
        mock_get_info.return_value = {
            'title': 'Test',
            'duration': 120,
            'platform': 'vimeo'
        }

        manager = PlatformManager()
        info = manager.get_video_info("https://vimeo.com/123456")

        assert info is not None
        assert info['platform'] == 'vimeo'

    @patch.object(DailymotionDownloader, 'get_video_info')
    def test_platform_manager_get_video_info_dailymotion(self, mock_get_info):
        """Manager Dailymotion video bilgisini al"""
        mock_get_info.return_value = {
            'title': 'DM Video',
            'duration': 180,
            'platform': 'dailymotion'
        }

        manager = PlatformManager()
        info = manager.get_video_info("https://dai.ly/x123456")

        assert info is not None
        assert info['platform'] == 'dailymotion'

    def test_platform_manager_get_video_info_unknown(self):
        """Bilinmeyen platform için None"""
        manager = PlatformManager()
        info = manager.get_video_info("https://unknown.com/video")

        assert info is None

    @patch.object(VimeoDownloader, 'download')
    def test_platform_manager_download_vimeo(self, mock_download):
        """Manager Vimeo indirmesi"""
        mock_download.return_value = True

        manager = PlatformManager()
        result = manager.download(
            "https://vimeo.com/123456",
            "/tmp/path",
            {'format': 'best'}
        )

        assert result is True

    @patch.object(DailymotionDownloader, 'download')
    def test_platform_manager_download_dailymotion(self, mock_download):
        """Manager Dailymotion indirmesi"""
        mock_download.return_value = True

        manager = PlatformManager()
        result = manager.download(
            "https://dai.ly/x123456",
            "/tmp/path",
            {}
        )

        assert result is True

    def test_platform_manager_download_unknown(self):
        """Bilinmeyen platform indirmesi False"""
        manager = PlatformManager()
        result = manager.download(
            "https://unknown.com/video",
            "/tmp/path",
            {}
        )

        assert result is False

    def test_platform_manager_get_supported_platforms(self):
        """Desteklenen platformları listele"""
        manager = PlatformManager()
        platforms = manager.get_supported_platforms()

        assert 'vimeo' in platforms
        assert 'dailymotion' in platforms
        assert isinstance(platforms, list)

    def test_platform_manager_empty_options(self):
        """Boş seçenekler işlenebilmeli"""
        manager = PlatformManager()

        with patch.object(VimeoDownloader, 'download', return_value=True):
            result = manager.download(
                "https://vimeo.com/123456",
                "/tmp/path"
            )
            assert result is True


class TestPlatformIntegration:
    """Platform entegrasyonu testleri"""

    def test_multiple_platforms_detection(self):
        """Farklı platformlar tanınmalı"""
        manager = PlatformManager()

        urls = [
            ("https://vimeo.com/123456", Platform.VIMEO),
            ("https://www.dailymotion.com/video/x123", Platform.DAILYMOTION),
            ("https://dai.ly/x456", Platform.DAILYMOTION),
        ]

        for url, expected_platform in urls:
            downloader = manager.find_downloader(url)
            assert downloader is not None
            assert downloader.platform == expected_platform

    def test_platform_manager_sequential_downloads(self):
        """Sırayla birden fazla indirme"""
        manager = PlatformManager()

        with patch.object(VimeoDownloader, 'download', return_value=True):
            with patch.object(DailymotionDownloader, 'download', return_value=True):
                vimeo_result = manager.download("https://vimeo.com/123", "/tmp")
                dailymotion_result = manager.download("https://dai.ly/x456", "/tmp")

                assert vimeo_result is True
                assert dailymotion_result is True
