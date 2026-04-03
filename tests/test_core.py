"""
RAVN Birim Testleri
pytest ile çalışır: pytest tests/
"""

import pytest
import sys
import os
from pathlib import Path
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

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP3,
            quality=DownloadQuality.AUDIO_ONLY,
            embed_metadata=True,
        )

        call_kwargs = self.downloader._runner.download.call_args.kwargs
        extra_args = call_kwargs["extra_args"]
        assert "--add-metadata" in extra_args
        assert "--embed-thumbnail" in extra_args
        assert "--convert-thumbnails" in extra_args

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

    def test_download_video_uses_subtitle_fallback_and_embed_args(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Clip",
            "subtitles": {},
            "automatic_captions": {"en": [{"ext": "vtt"}]},
        }
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp4"]},
        )

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            auto_subtitle_download=True,
            preferred_subtitle_language="tr",
            subtitle_fallback_language="en",
            subtitle_include_auto_generated=True,
            auto_embed_subtitles=True,
        )

        extra_args = self.downloader._runner.download.call_args.kwargs["extra_args"]
        assert "--write-subs" in extra_args
        assert "--write-auto-subs" in extra_args
        assert "--embed-subs" in extra_args
        sub_lang_index = extra_args.index("--sub-langs") + 1
        assert extra_args[sub_lang_index] == "en"

    def test_download_audio_skips_subtitle_embed_even_when_enabled(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Track",
            "subtitles": {"tr": [{"ext": "vtt"}]},
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
            auto_subtitle_download=True,
            preferred_subtitle_language="tr",
            auto_embed_subtitles=True,
        )

        extra_args = self.downloader._runner.download.call_args.kwargs["extra_args"]
        assert "--write-subs" in extra_args
        assert "--embed-subs" not in extra_args

    def test_download_clean_naming_preset_renames_output(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Live / Final",
            "uploader": "AC/DC",
            "upload_date": "20240131",
        }
        self.downloader._runner.compute_size_by_quality.return_value = {
            "resolution_by_quality": {"En İyi": "1920x1080"}
        }

        source_file = tmp_path / "Live Final.mp4"
        source_file.write_bytes(b"video")
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(source_file)]},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            naming_preset="clean",
        )

        renamed_path = Path(result.output_files[0])
        assert renamed_path.exists()
        assert renamed_path.name == "ACDC - Live Final.mp4"
        assert not source_file.exists()

    def test_download_custom_template_uses_resolution_and_folder_structure(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Clip",
            "uploader": "Studio/Channel",
        }
        self.downloader._runner.compute_size_by_quality.return_value = {
            "resolution_by_quality": {"1080p": "1920x1080"}
        }

        source_file = tmp_path / "Clip.mp4"
        source_file.write_bytes(b"video")
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(source_file)]},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.HIGH_1080P,
            filename_template="{uploader}/{resolution} - {title}",
        )

        renamed_path = Path(result.output_files[0])
        assert renamed_path.exists()
        assert renamed_path.parent.name == "StudioChannel"
        assert renamed_path.name == "1920x1080 - Clip.mp4"

    def test_download_enriches_metadata_with_normalized_title_and_tags(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {
            "title": "Song Name (Official Video)",
            "uploader": "Artist Name - Topic",
            "playlist_title": "Album 2026",
            "extractor_key": "YouTube",
            "upload_date": "20260403",
            "webpage_url": "https://example.com/watch?v=1",
        }

        source_file = tmp_path / "Song Name.mp4"
        source_file.write_bytes(b"video")
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(source_file)]},
        )

        result = self.downloader.download(
            url="https://www.youtube.com/watch?v=1",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            auto_subtitle_download=True,
        )

        assert result.title == "Song Name"
        assert result.metadata["normalized"]["uploader"] == "Artist Name"
        assert "youtube" in result.metadata["library_tags"]
        assert "creator-artist-name" in result.metadata["library_tags"]
        assert result.metadata["acquisition"]["upload_date"] == "20260403"

    def test_download_passes_archive_resume_and_rate_limit_args(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip", "duration": 10}
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp4"]},
        )

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            robustness_profile={
                "enable_archive": True,
                "detect_duplicates": True,
                "continue_partial": True,
                "format_fallback": True,
                "rate_limit_kbps": 512,
            },
        )

        extra_args = self.downloader._runner.download.call_args.kwargs["extra_args"]
        assert "--download-archive" in extra_args
        assert "--continue" in extra_args
        assert "--part" in extra_args
        assert "--limit-rate" in extra_args
        assert "512K" in extra_args

    def test_download_passes_advanced_auth_and_fragment_args(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip", "duration": 10}
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp4"]},
        )

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            advanced_profile={
                "cookies_mode": "browser",
                "cookies_browser": "firefox",
                "cookies_profile": "default-release",
                "concurrent_fragments": 4,
                "fragment_retries": 8,
                "socket_timeout_seconds": 55,
            },
        )

        extra_args = self.downloader._runner.download.call_args.kwargs["extra_args"]
        assert "--cookies-from-browser" in extra_args
        assert "firefox:default-release" in extra_args
        assert "--concurrent-fragments" in extra_args
        assert "4" in extra_args
        assert "--fragment-retries" in extra_args
        assert "8" in extra_args
        assert "--socket-timeout" in extra_args
        assert "55" in extra_args

    def test_download_uses_cookie_file_auth_when_configured(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip", "duration": 10}
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": ["out.mp4"]},
        )

        self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            advanced_profile={
                "cookies_mode": "file",
                "cookies_file": "C:/secure/cookies.txt",
            },
        )

        extra_args = self.downloader._runner.download.call_args.kwargs["extra_args"]
        assert "--cookies" in extra_args
        assert "C:/secure/cookies.txt" in extra_args
        assert "--cookies-from-browser" not in extra_args

    def test_download_retries_with_fallback_format_when_primary_fails(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip"}
        source_file = tmp_path / "Clip.mp4"
        source_file.write_bytes(b"video")
        self.downloader._runner.download.side_effect = [
            RunnerResult(success=False, return_code=1, error_message="No downloadable formats available"),
            RunnerResult(success=True, return_code=0, metadata={"downloaded_files": [str(source_file)]}),
        ]

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.HIGH_1080P,
            robustness_profile={"format_fallback": True},
        )

        assert result.success is True
        assert result.metadata["robustness"]["format_fallback_used"] is True
        assert self.downloader._runner.download.call_count == 2
        second_call = self.downloader._runner.download.call_args_list[1].kwargs
        assert second_call["format_spec"] == DownloadFormat.MP4.format_spec

    def test_download_archive_skip_marks_duplicate_metadata(self):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip", "uploader": "Uploader"}
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [], "archive_skipped": True},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir="C:/downloads",
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            robustness_profile={"detect_duplicates": True, "enable_archive": True},
        )

        assert result.success is True
        assert result.output_files == []
        assert result.metadata["robustness"]["archive_skipped"] is True

    def test_download_filters_supporting_artifacts_out_of_primary_outputs(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip"}

        video_file = tmp_path / "Clip.mp4"
        subtitle_file = tmp_path / "Clip.en.vtt"
        video_file.write_bytes(b"video")
        subtitle_file.write_text("WEBVTT", encoding="utf-8")
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(video_file), str(subtitle_file)]},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            auto_subtitle_download=True,
        )

        assert result.output_files == [str(video_file)]
        assert result.metadata["supporting_files"] == [str(subtitle_file)]

    def test_download_postprocess_extract_audio_pipeline_returns_final_audio(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip"}

        video_file = tmp_path / "Clip.mp4"
        audio_file = tmp_path / "Clip.mp3"
        video_file.write_bytes(b"video")

        helpers = Mock()

        def _extract_audio(**_kwargs):
            audio_file.write_bytes(b"audio")
            return RunnerResult(success=True, return_code=0, metadata={"output_file": str(audio_file)})

        helpers.extract_audio.side_effect = _extract_audio
        self.downloader._media_helpers_factory = lambda: helpers
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(video_file)]},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            postprocess_profile={
                "extract_audio": True,
                "audio_format": "mp3",
                "audio_bitrate": "192k",
            },
        )

        assert result.success is True
        assert result.output_files == [str(audio_file)]
        assert result.metadata["postprocess"]["executed_steps"] == ["extract_audio"]

    def test_download_postprocess_embeds_matching_subtitle_sidecar(self, tmp_path):
        self.downloader._runner = Mock()
        self.downloader._runner.extract_info.return_value = {"title": "Clip"}

        video_file = tmp_path / "Clip.mp4"
        subtitle_file = tmp_path / "Clip.en.vtt"
        subtitled_file = tmp_path / "Clip.subtitled.mp4"
        video_file.write_bytes(b"video")
        subtitle_file.write_text("WEBVTT", encoding="utf-8")

        embedder = Mock()

        def _embed_soft(**_kwargs):
            subtitled_file.write_bytes(b"subbed")
            return True

        embedder.embed_soft.side_effect = _embed_soft
        self.downloader._subtitle_embedder_factory = lambda: embedder
        self.downloader._runner.download.return_value = RunnerResult(
            success=True,
            return_code=0,
            metadata={"downloaded_files": [str(video_file), str(subtitle_file)]},
        )

        result = self.downloader.download(
            url="https://example.com/v",
            output_dir=str(tmp_path),
            format_type=DownloadFormat.MP4,
            quality=DownloadQuality.BEST,
            postprocess_profile={"embed_subtitles": True},
            auto_subtitle_download=True,
            preferred_subtitle_language="en",
        )

        assert result.success is True
        assert result.output_files == [str(subtitled_file)]
        assert "embed_subtitles" in result.metadata["postprocess"]["executed_steps"]


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
