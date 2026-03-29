"""
UI logic tests for tab widgets without rendering.
"""

from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from ravn_app.core.converter import AudioBitrate, VideoQuality
from ravn_app.ui.converter_tab import ConverterTab
from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab
from ravn_app.ui.main_window import YouTubeDownloaderApp
from ravn_app.ui.subtitle_tab import SubtitleTab


class _FakeEntry:
    def __init__(self, value=""):
        self.value = value

    def get(self):
        return self.value

    def delete(self, _a, _b):
        self.value = ""

    def insert(self, _idx, value):
        self.value = value


class _FakeCombo:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FakeLabel:
    def __init__(self):
        self.calls = []

    def configure(self, **kwargs):
        self.calls.append(kwargs)

    def pack(self, **kwargs):
        self.calls.append({"pack": kwargs})

    def pack_forget(self):
        self.calls.append({"pack_forget": True})


class _FakeZone:
    def __init__(self):
        self.calls = []

    def configure(self, **kwargs):
        self.calls.append(kwargs)


class _FakeText:
    def __init__(self):
        self.lines = []

    def insert(self, _pos, text):
        self.lines.append(text)

    def see(self, _pos):
        return None


class _FakeEvent:
    def __init__(self, data):
        self.data = data


class _FakeVar:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _FakeSlider:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value


class _FakeConfig:
    def __init__(self):
        self.writes = []

    def set(self, key, value):
        self.writes.append((key, value))

    def get(self, key, default=None):
        defaults = {
            "theme": "nordic",
            "language": "tr",
            "notifications_enabled": True,
            "auto_update_check": True,
            "default_download_path": str(Path.home()),
            "default_format": "MP4",
            "default_quality": "1080p",
            "concurrent_downloads": 1,
            "ffmpeg_path": "ffmpeg",
            "auto_cleanup": False,
            "history_limit": 1000,
            "auto_subtitle_download": False,
            "preferred_subtitle_language": "tr",
        }
        return defaults.get(key, default)


class _FakeBadgeManager:
    def __init__(self, badge):
        self.badge = badge

    def get_platform_badge(self, _url):
        return self.badge


class _FakeButton(_FakeLabel):
    pass


class _FakeFrame:
    def __init__(self):
        self._children = []
        self.calls = []

    def pack(self, **kwargs):
        self.calls.append({"pack": kwargs})

    def pack_forget(self):
        self.calls.append({"pack_forget": True})

    def winfo_children(self):
        return list(self._children)


class TestConverterTabLogic:
    def test_get_quality_maps_labels(self):
        tab = ConverterTab.__new__(ConverterTab)
        tab.quality = _FakeCombo("Düşük")
        assert tab.get_quality() == VideoQuality.LOW

    def test_get_audio_bitrate_maps_labels(self):
        tab = ConverterTab.__new__(ConverterTab)
        tab.audio_bitrate = _FakeCombo("192k (Yüksek)")
        assert tab.get_audio_bitrate() == AudioBitrate.HIGH


class TestSubtitleTabLogic:
    def test_parse_drop_path_handles_braces(self):
        tab = SubtitleTab.__new__(SubtitleTab)
        parsed = tab._parse_drop_path(_FakeEvent("{C:\\test\\video.mp4}"))
        assert str(parsed).endswith("video.mp4")

    def test_highlight_zone_updates_colors(self):
        tab = SubtitleTab.__new__(SubtitleTab)
        zone = _FakeZone()
        hint = _FakeLabel()
        tab._highlight_zone(zone, hint, True)
        assert zone.calls
        assert hint.calls

    def test_on_video_drop_sets_selected_video(self):
        tab = SubtitleTab.__new__(SubtitleTab)
        tab._video_drop_zone = _FakeZone()
        tab._video_dnd_hint = _FakeLabel()
        tab.video_label = _FakeLabel()
        tab.log = Mock()
        tab.current_video_file = None
        tab._on_video_drop(_FakeEvent("{C:\\media\\movie.mp4}"))
        assert tab.current_video_file.endswith("movie.mp4")

    def test_on_subtitle_drop_sets_selected_subtitle(self):
        tab = SubtitleTab.__new__(SubtitleTab)
        tab._subtitle_drop_zone = _FakeZone()
        tab._subtitle_dnd_hint = _FakeLabel()
        tab.subtitle_label = _FakeLabel()
        tab.log = Mock()
        tab.current_subtitle_file = None
        tab._on_subtitle_drop(_FakeEvent("{C:\\subs\\movie.srt}"))
        assert tab.current_subtitle_file.endswith("movie.srt")


class TestSettingsAndHistoryLogic:
    def test_history_format_size(self):
        assert HistoryTab.format_size(1024) == "1.0 KB"

    def test_save_settings_writes_expected_keys(self):
        tab = SettingsTab.__new__(SettingsTab)
        tab.config = _FakeConfig()
        tab.theme_combo = _FakeCombo("Nordic")
        tab.language_combo = _FakeCombo("Türkçe")
        tab.notifications_var = _FakeVar(True)
        tab.auto_update_var = _FakeVar(False)
        tab.download_dir_entry = _FakeEntry("C:\\Downloads")
        tab.default_format_combo = _FakeCombo("MP4")
        tab.default_quality_combo = _FakeCombo("1080p")
        tab.concurrent_slider = _FakeSlider(2)
        tab.ffmpeg_entry = _FakeEntry("ffmpeg")
        tab.auto_cleanup_var = _FakeVar(False)
        tab.history_limit_entry = _FakeEntry("500")
        tab.auto_subtitle_var = _FakeVar(True)
        tab.subtitle_lang_combo = _FakeCombo("en")

        import ravn_app.ui.history_settings_tab as module

        original_showinfo = module.messagebox.showinfo
        try:
            module.messagebox.showinfo = lambda *_args, **_kwargs: None
            tab.save_settings()
        finally:
            module.messagebox.showinfo = original_showinfo

        keys = {key for key, _ in tab.config.writes}
        assert "theme" in keys
        assert "language" in keys
        assert "default_download_path" in keys
        assert "history_limit" in keys


class TestMainWindowLogic:
    def test_on_url_changed_applies_platform_badge(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.url_entry = _FakeEntry("https://x.com/test/status/1")
        app.selected_platform_label = _FakeLabel()
        app.platform_manager = _FakeBadgeManager(
            {"icon": "X", "label": "Twitter/X", "color": "#60a5fa", "platform": "twitter"}
        )
        app._on_url_changed()
        assert app.selected_platform_label.calls
        latest = app.selected_platform_label.calls[-1]
        assert latest["text"] == "X Twitter/X"

        del app

    def test_del_closes_db_manager_safely(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        fake_db = Mock()
        app.__dict__["db_manager"] = fake_db
        app.__del__()
        fake_db.close.assert_called_once()

    def test_looks_like_playlist_url(self):
        assert YouTubeDownloaderApp._looks_like_playlist_url("https://www.youtube.com/playlist?list=PL1")
        assert not YouTubeDownloaderApp._looks_like_playlist_url("https://www.youtube.com/watch?v=abc")

    def test_get_selected_playlist_entries(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.playlist_entries = [{"url": "a"}, {"url": "b"}]
        app.playlist_selection_vars = [_FakeVar(True), _FakeVar(False)]
        selected = app._get_selected_playlist_entries()
        assert selected == [{"url": "a"}]

    def test_on_playlist_fetch_complete_sets_ui(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._hide_progress = Mock()
        app.download_btn = _FakeButton()
        app.download_status_label = _FakeLabel()
        app.playlist_frame = _FakeFrame()
        app.playlist_list_frame = _FakeFrame()
        app.playlist_summary_label = _FakeLabel()
        app.playlist_selection_vars = []
        app.playlist_entries = []
        app.playlist_source_url = ""
        app.is_playlist_fetching = True
        app._update_playlist_summary = Mock()

        import ravn_app.ui.main_window as module

        original_checkbox = module.ctk.CTkCheckBox
        original_boolvar = module.ctk.BooleanVar
        try:
            module.ctk.BooleanVar = lambda value=True: _FakeVar(value)
            module.ctk.CTkCheckBox = lambda *_args, **_kwargs: _FakeLabel()
            entries = [
                {"title": "Video 1", "url": "https://example.com/1", "duration": 61},
                {"title": "Video 2", "url": "https://example.com/2", "duration": 30},
            ]
            app._on_playlist_fetch_complete("https://example.com/list", entries)
        finally:
            module.ctk.CTkCheckBox = original_checkbox
            module.ctk.BooleanVar = original_boolvar

        assert app.playlist_source_url == "https://example.com/list"
        assert len(app.playlist_entries) == 2
        assert len(app.playlist_selection_vars) == 2

    def test_download_video_fetches_playlist_before_download(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.queue_paused = False
        app.url_entry = _FakeEntry("https://www.youtube.com/playlist?list=PL1")
        app.quality_menu = _FakeCombo("En İyi")
        app.format_menu = _FakeCombo("MP4")
        app.config_manager = _FakeConfig()
        app.playlist_source_url = ""
        app.playlist_entries = []
        app.is_playlist_fetching = False
        app._show_download_error = Mock()
        app._start_playlist_fetch = Mock()
        app._start_playlist_download = Mock()
        app._start_single_download = Mock()
        app._get_selected_playlist_entries = Mock(return_value=[])

        app._download_video()

        app._show_download_error.assert_called_once()
        app._start_playlist_fetch.assert_not_called()
        app._start_single_download.assert_not_called()

    def test_fetch_download_data_starts_playlist_fetch(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.url_entry = _FakeEntry("https://www.youtube.com/playlist?list=PL1")
        app.is_playlist_fetching = False
        app.is_info_fetching = False
        app._show_download_error = Mock()
        app._start_playlist_fetch = Mock()
        app._start_video_info_fetch = Mock()

        app._fetch_download_data()

        app._start_playlist_fetch.assert_called_once()
        app._start_video_info_fetch.assert_not_called()

    def test_fetch_download_data_starts_video_info_fetch(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.url_entry = _FakeEntry("https://www.youtube.com/watch?v=abc")
        app.is_playlist_fetching = False
        app.is_info_fetching = False
        app._show_download_error = Mock()
        app._start_playlist_fetch = Mock()
        app._start_video_info_fetch = Mock()

        app._fetch_download_data()

        app._start_video_info_fetch.assert_called_once()
        app._start_playlist_fetch.assert_not_called()

