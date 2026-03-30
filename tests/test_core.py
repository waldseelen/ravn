"""
RAVN Birim Testleri
pytest ile çalışır: pytest tests/
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Proje dizinini path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ravn_app.core.downloader import DownloadFormat, DownloadQuality, YouTubeDownloader
from ravn_app.core.runners import RunnerResult
from ravn_app.utils.file_utils import sanitize_filename, format_bytes
from ravn_app.utils.system_utils import find_executable, get_platform


class TestYouTubeDownloader:
    """YouTubeDownloader sınıfı testleri"""
    
    def setup_method(self):
        """Her test öncesi çalışır"""
        self.downloader = YouTubeDownloader()
    
    def test_downloader_creation(self):
        """Downloader nesnesi oluşturulabilir mi"""
        assert self.downloader is not None
        assert self.downloader.download_queue is not None
    
    def test_format_options(self):
        """Format seçenekleri mevcut mi"""
        formats = self.downloader.get_video_format_options()
        assert "MP4 (Video)" in formats
        assert "MP3 (Ses)" in formats
        # New API includes more formats: MP4, WebM, MKV, MP3, M4A
        assert len(formats) >= 2
    
    def test_quality_options(self):
        """Kalite seçenekleri mevcut mi"""
        qualities = self.downloader.get_quality_options()
        assert "En İyi" in qualities
        assert "1080p" in qualities
        assert "720p" in qualities
        assert "480p" in qualities
        # New API may include more quality options
        assert len(qualities) >= 4
    
    def test_sanitize_filename(self):
        """Dosya adı temizleme çalışıyor mu"""
        filename = 'My "Video" (2025) | Full HD.mp4'
        cleaned = YouTubeDownloader.sanitize_filename(filename)
        assert '"' not in cleaned
        assert '|' not in cleaned
        assert '(' in cleaned  # Parantez temizlenmiyor

    @patch("ravn_app.core.downloader.YtDlpRunner.extract_playlist_entries")
    def test_extract_playlist_entries(self, mock_extract):
        """Playlist entry extraction proxies runner output"""
        mock_extract.return_value = [
            {"title": "A", "url": "https://example.com/a"},
            {"title": "B", "url": "https://example.com/b"},
        ]
        entries = self.downloader.extract_playlist_entries("https://example.com/playlist")
        assert len(entries) == 2
        assert entries[0]["title"] == "A"

    def test_download_audio_includes_metadata_embedding_args(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Track",
            "uploader": "Artist",
            "description": "lyrics text",
            "thumbnail": "https://example.com/thumb.jpg",
        }
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp3"]},
        )
        self.downloader._apply_audio_metadata = Mock()

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP3,
            quality=DownloadQuality.AUDIO_ONLY,
        )

        call_kwargs = self.downloader._runner.download.call_args.kwargs
        extra_args = call_kwargs["extra_args"]
        assert "--embed-metadata" in extra_args
        assert "--embed-thumbnail" in extra_args
        assert "--parse-metadata" in extra_args

    def test_download_audio_triggers_audio_metadata_postprocessing(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Track",
            "uploader": "Artist",
            "description": "lyrics text",
            "thumbnail": "https://example.com/thumb.jpg",
        }
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp3"]},
        )
        self.downloader._apply_audio_metadata = Mock()

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP3,
            quality=DownloadQuality.AUDIO_ONLY,
        )

        self.downloader._apply_audio_metadata.assert_called_once()

    def test_download_auto_sort_uses_artist_subfolder(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Track",
            "artist": "AC/DC",
            "uploader": "Uploader Name",
            "description": "lyrics",
            "thumbnail": "",
        }
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp3"]},
        )
        self.downloader._apply_audio_metadata = Mock()

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP3,
            quality=DownloadQuality.AUDIO_ONLY,
            auto_sort_enabled=True,
            auto_sort_mode="artist",
        )

        call_kwargs = self.downloader._runner.download.call_args.kwargs
        assert call_kwargs["output_dir"].endswith("ACDC")


class TestFileUtils:
    """Dosya işlemleri testleri"""
    
    def test_sanitize_filename_removes_invalid_chars(self):
        """Geçersiz karakterler temizleniyor mu"""
        test_cases = [
            ('file*name.txt', 'filename.txt'),
            ('file?test.mp4', 'filetest.mp4'),
            ('file:name.doc', 'filename.doc'),
            ('file"name".docx', 'filename.docx'),
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected
    
    def test_format_bytes_conversion(self):
        """Byte dönüştürmesi doğru mu"""
        assert "(1.00 Bytes)" in format_bytes(1)
        assert "KB" in format_bytes(1024)
        assert "MB" in format_bytes(1024 * 1024)
        assert "GB" in format_bytes(1024 * 1024 * 1024)
    
    def test_format_bytes_invalid_input(self):
        """Geçersiz giriş ele alınıyor mu"""
        assert format_bytes("invalid") == ""
        assert format_bytes(None) == ""


class TestSystemUtils:
    """Sistem işlemleri testleri"""
    
    def test_platform_detection(self):
        """Platform algılama çalışıyor mu"""
        platform = get_platform()
        assert platform in ["windows", "darwin", "linux"]
    
    def test_find_executable(self):
        """Executable bulma çalışıyor mu"""
        # python her zaman bulunabilir
        result = find_executable("python")
        assert result is not None or find_executable("python3") is not None


class TestIntegration:
    """Entegrasyon testleri"""
    
    def test_downloader_workflow(self):
        """Temel indirme akışı doğru mu"""
        downloader = YouTubeDownloader()
        
        # Format seçeneklerini al
        formats = downloader.get_video_format_options()
        assert "MP4 (Video)" in formats
        
        # Kalite seçeneklerini al
        qualities = downloader.get_quality_options()
        assert len(qualities) > 0
        
        # İndirme kuyruğu boş olmalı
        assert downloader.download_queue.empty()


@pytest.mark.skip(reason="YouTube API ihtiyacı")
class TestLiveDownload:
    """Canlı indirme testleri (internet gerekli)"""
    
    def test_extract_video_info(self):
        """Video bilgilerini çekebiliyor mu"""
        downloader = YouTubeDownloader()
        # Bu test gerçek bir video URL'si gerektirir
        # Örnek: https://www.youtube.com/watch?v=dQw4w9WgXcQ
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
