"""Unit tests for the pure media-URL helpers extracted from the download tab."""

import pytest

from ravn_app.core import media_url_utils as u


class TestDetectUrlProtocol:
    @pytest.mark.parametrize("url,expected", [
        ("magnet:?xt=urn:btih:abc", "magnet"),
        ("  MAGNET:?xt=urn:btih:abc  ", "magnet"),
        ("https://example.com/file.torrent", "torrent_file"),
        ("https://example.com/FILE.TORRENT", "torrent_file"),
        ("https://youtube.com/watch?v=x", "standard"),
        ("", "standard"),
        (None, "standard"),
    ])
    def test_detects(self, url, expected):
        assert u.detect_url_protocol(url) == expected


class TestIsSupportedVideoUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=x",
        "http://youtu.be/x",
        "https://vimeo.com/123",
        "https://www.tiktok.com/@a/video/1",
    ])
    def test_supported(self, url):
        assert u.is_supported_video_url(url) is True

    @pytest.mark.parametrize("url", [
        "",
        "ftp://youtube.com/x",           # wrong scheme
        "https://example.com/x",         # unknown domain
        "youtube.com/x",                 # missing scheme
        "magnet:?xt=urn:btih:abc",
    ])
    def test_unsupported(self, url):
        assert u.is_supported_video_url(url) is False


class TestLooksLikePlaylistUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/watch?v=x&list=PL123",
        "https://soundcloud.com/user/sets/my-set",
        "https://example.com/collection/abc",
    ])
    def test_playlist(self, url):
        assert u.looks_like_playlist_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=x",
        "https://vimeo.com/123",
        "",
    ])
    def test_single(self, url):
        assert u.looks_like_playlist_url(url) is False


class TestFormatDuration:
    @pytest.mark.parametrize("seconds,expected", [
        (0, ""),
        (-5, ""),
        ("nan", ""),
        (None, ""),
        (45, "0:45"),
        (90, "1:30"),
        (3661, "1:01:01"),
        (8752, "2:25:52"),
    ])
    def test_formats(self, seconds, expected):
        assert u.format_duration(seconds) == expected


class TestFormatSizeFromMb:
    @pytest.mark.parametrize("mb,expected", [
        (0, "0.0 MB"),
        (512, "512.0 MB"),
        (1023.9, "1023.9 MB"),
        (1024, "1.0 GB"),
        (2622.8, "2.6 GB"),
    ])
    def test_formats(self, mb, expected):
        assert u.format_size_from_mb(mb) == expected
