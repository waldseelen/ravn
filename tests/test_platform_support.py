"""
Platform support tests.
"""

from unittest.mock import Mock, patch

from ravn_app.core.platform_support import (
    DailymotionDownloader,
    GenericYtDlpDownloader,
    InstagramDownloader,
    Platform,
    PlatformManager,
    TikTokDownloader,
    TwitchDownloader,
    TwitterXDownloader,
    VimeoDownloader,
    YouTubeDownloader,
)


class TestPlatformSpecificDetection:
    def test_tiktok_can_download(self):
        downloader = TikTokDownloader()
        assert downloader.can_download("https://www.tiktok.com/@demo/video/123")
        assert downloader.can_download("https://vm.tiktok.com/abcdef/")
        assert not downloader.can_download("https://example.com/video")

    def test_instagram_can_download_reel_and_post(self):
        downloader = InstagramDownloader()
        assert downloader.can_download("https://www.instagram.com/reel/ABC/")
        assert downloader.can_download("https://www.instagram.com/p/XYZ/")
        assert not downloader.can_download("https://www.instagram.com/stories/test/")

    def test_twitch_can_download_vod_and_clip(self):
        downloader = TwitchDownloader()
        assert downloader.can_download("https://www.twitch.tv/videos/123456789")
        assert downloader.can_download("https://clips.twitch.tv/FancyClipName")
        assert not downloader.can_download("https://www.twitch.tv/somechannel")

    def test_twitter_x_can_download(self):
        downloader = TwitterXDownloader()
        assert downloader.can_download("https://x.com/user/status/123")
        assert downloader.can_download("https://twitter.com/user/status/123")
        assert not downloader.can_download("https://example.com/x")

    def test_generic_fallback(self):
        downloader = GenericYtDlpDownloader()
        assert downloader.can_download("https://random.example/video")
        assert not downloader.can_download("ftp://example.com/video")


class TestPlatformManager:
    def test_default_platforms_registered(self):
        manager = PlatformManager()
        platforms = manager.get_supported_platforms()
        assert "youtube" in platforms
        assert "vimeo" in platforms
        assert "dailymotion" in platforms
        assert "tiktok" in platforms
        assert "instagram" in platforms
        assert "twitch" in platforms
        assert "twitter" in platforms
        assert "generic" in platforms

    def test_detection_prioritizes_specific_before_generic(self):
        manager = PlatformManager()
        assert manager.detect_platform("https://vimeo.com/123") == Platform.VIMEO
        assert manager.detect_platform("https://www.tiktok.com/@x/video/1") == Platform.TIKTOK
        assert manager.detect_platform("https://unknown.example/video") == Platform.GENERIC

    def test_get_platform_badge_known(self):
        manager = PlatformManager()
        badge = manager.get_platform_badge("https://www.instagram.com/reel/abc/")
        assert badge["platform"] == "instagram"
        assert badge["icon"] == "IG"
        assert "label" in badge
        assert "color" in badge

    def test_get_platform_badge_unknown(self):
        manager = PlatformManager()
        badge = manager.get_platform_badge("not-a-valid-url")
        assert badge["platform"] == "unknown"
        assert badge["icon"] == "?"

    @patch("ravn_app.core.platform_support.YtDlpRunner.download")
    def test_download_with_options(self, mock_download, tmp_path):
        mock_download.return_value = Mock(success=True, error_message="", metadata={})
        manager = PlatformManager()
        success = manager.download(
            "https://vimeo.com/123",
            str(tmp_path),
            {"format": "best", "save_info": True, "subtitles": True, "retries": 1},
        )
        assert success is True
        assert mock_download.call_count == 1

    @patch("ravn_app.core.platform_support.YtDlpRunner.extract_info")
    def test_get_video_info_maps_fields(self, mock_extract):
        mock_extract.return_value = {
            "title": "Demo",
            "duration": 12,
            "uploader": "Uploader",
            "thumbnail": "https://image",
            "view_count": 5,
            "like_count": 1,
            "formats": [{"id": "1"}, {"id": "2"}],
            "ext": "mp4",
            "extractor": "youtube",
        }
        manager = PlatformManager()
        info = manager.get_video_info("https://youtube.com/watch?v=1")
        assert info is not None
        assert info["title"] == "Demo"
        assert info["formats"] == 2
        assert info["platform"] == "youtube"

