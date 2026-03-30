"""
UI logic tests for tab widgets without rendering.
"""

from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock

from ravn_app.core.task_manager import TaskStatus
from ravn_app.core.converter import AudioBitrate, VideoQuality
from ravn_app.ui.converter_tab import ConverterTab
from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab
from ravn_app.ui.main_window import YouTubeDownloaderApp
from ravn_app.ui.tabs.download_tab import DownloadTab
from ravn_app.ui.queue_panel import QueueItemWidget
from ravn_app.ui.subtitle_tab import SubtitleTab
from ravn_app.ui.design_tokens import Colors, Icons


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
            "auto_id3_tagging": True,
            "auto_embed_lyrics": True,
            "auto_sort_downloads": False,
            "auto_sort_mode": "artist",
        }
        return defaults.get(key, default)


class _FakeBadgeManager:
    def __init__(self, badge):
        self.badge = badge

    def get_platform_badge(self, _url):
        return self.badge


class _FakeButton(_FakeLabel):
    pass


class _FakeActionButton:
    def __init__(self, width=120, hover_color="#333333"):
        self._props = {
            "width": width,
            "hover_color": hover_color,
            "border_width": 0,
            "border_color": None,
        }

    def cget(self, name):
        return self._props.get(name)

    def configure(self, **kwargs):
        self._props.update(kwargs)


class _FakeProgressBar:
    def __init__(self):
        self.values = []
        self.calls = []

    def set(self, value):
        self.values.append(value)

    def configure(self, **kwargs):
        self.calls.append(kwargs)

    def pack(self, **kwargs):
        self.calls.append({"pack": kwargs})

    def pack_forget(self):
        self.calls.append({"pack_forget": True})


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
        tab.auto_id3_var = _FakeVar(True)
        tab.auto_lyrics_var = _FakeVar(True)
        tab.auto_sort_var = _FakeVar(True)
        tab.auto_sort_mode_combo = _FakeCombo("Sanatçı")
        tab.close_behavior_combo = _FakeCombo("Sistem Çekmecesine Küçült")

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
        assert "auto_id3_tagging" in keys
        assert "auto_embed_lyrics" in keys
        assert "auto_sort_downloads" in keys
        assert "auto_sort_mode" in keys


class TestMainWindowLogic:
    def test_detect_url_protocol_handles_uppercase_magnet(self):
        assert DownloadTab._detect_url_protocol("MAGNET:?xt=urn:btih:abc123") == "magnet"

    def test_on_url_changed_applies_platform_badge(self):
        app = DownloadTab.__new__(DownloadTab)
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

    def test_on_url_changed_places_torrent_mode_after_url_row(self):
        app = DownloadTab.__new__(DownloadTab)
        app.url_entry = _FakeEntry("magnet:?xt=urn:btih:abc123")
        app.selected_platform_label = _FakeLabel()
        app.platform_manager = _FakeBadgeManager(
            {"icon": "?", "label": "Unknown", "color": "#666", "platform": "unknown"}
        )
        app.torrent_mode_frame = _FakeFrame()
        app._url_row_frame = object()

        app._on_url_changed()

        pack_calls = [c["pack"] for c in app.torrent_mode_frame.calls if "pack" in c]
        assert pack_calls
        assert pack_calls[-1].get("after") is app._url_row_frame

    def test_apply_progress_update_uses_smoothing(self):
        app = DownloadTab.__new__(DownloadTab)
        app.download_progress = _FakeProgressBar()
        app.download_status_label = _FakeLabel()
        app.animation_manager = SimpleNamespace(
            smooth_progress=lambda current, target, max_step=0.08: min(target, current + max_step)
        )
        app._download_progress_value = 0.0

        app._apply_progress_update(100, "İndiriliyor")

        assert app._download_progress_value < 1.0
        assert app.download_progress.values[-1] == app._download_progress_value
        assert app.download_status_label.calls[-1]["text"] == "İndiriliyor"

    def test_start_processing_feedback_starts_spinner_and_message_loop(self):
        app = DownloadTab.__new__(DownloadTab)
        app.download_status_label = _FakeLabel()
        app.animation_manager = SimpleNamespace(
            stop_animation=lambda _animation_id: None,
            format_processing_text=lambda base, tick: f"{base}{'.' * ((tick % 3) + 1)}",
        )
        app._spinner_animation_id = None
        app._processing_after_id = None

        scheduled = {}

        def fake_after(delay, callback, *args):
            scheduled["delay"] = delay
            scheduled["callback"] = callback
            scheduled["args"] = args
            return "after-1"

        app.after = fake_after

        app._start_processing_feedback("Downloading")

        assert app._processing_after_id == "after-1"
        assert "Downloading" in app.download_status_label.calls[-1]["text"]

    def test_button_press_release_restores_original_width(self):
        app = DownloadTab.__new__(DownloadTab)
        button = _FakeActionButton(width=160)

        for _ in range(3):
            app._apply_button_press_state(button)
            app._apply_button_release_state(button)

        assert button.cget("width") == 160

    def test_del_closes_db_manager_safely(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        fake_db = Mock()
        app.__dict__["db_manager"] = fake_db
        app.__del__()
        fake_db.close.assert_called_once()

    def test_looks_like_playlist_url(self):
        assert DownloadTab._looks_like_playlist_url("https://www.youtube.com/playlist?list=PL1")
        assert not DownloadTab._looks_like_playlist_url("https://www.youtube.com/watch?v=abc")

    def test_get_selected_playlist_entries(self):
        app = DownloadTab.__new__(DownloadTab)
        app.playlist_entries = [{"url": "a"}, {"url": "b"}]
        app.playlist_selection_vars = [_FakeVar(True), _FakeVar(False)]
        selected = app._get_selected_playlist_entries()
        assert selected == [{"url": "a"}]

    def test_on_playlist_fetch_complete_sets_ui(self):
        app = DownloadTab.__new__(DownloadTab)
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

        import ravn_app.ui.tabs.download_tab as module
        from ravn_app.ui import design_tokens

        original_checkbox = module.ctk.CTkCheckBox
        original_boolvar = module.ctk.BooleanVar
        original_frame = module.ctk.CTkFrame
        original_label = module.ctk.CTkLabel
        original_playlist_item = module.PlaylistItemRow
        original_fonts = design_tokens.Fonts
        original_module_fonts = module.Fonts
        try:
            # Mock Fonts to avoid Tkinter root window requirement
            mock_fonts = Mock()
            mock_fonts.LABEL_BOLD = Mock()
            mock_fonts.SMALL = Mock()
            design_tokens.Fonts = mock_fonts
            module.Fonts = mock_fonts

            module.ctk.BooleanVar = lambda value=True: _FakeVar(value)
            module.ctk.CTkCheckBox = lambda *_args, **_kwargs: _FakeLabel()
            module.ctk.CTkFrame = lambda *_args, **_kwargs: _FakeFrame()
            module.ctk.CTkLabel = lambda *_args, **_kwargs: _FakeLabel()

            class _FakePlaylistItem(_FakeFrame):
                def __init__(self, *_args, **_kwargs):
                    super().__init__()

                def set_detail_text(self, _detail_text):
                    return None

            module.PlaylistItemRow = _FakePlaylistItem

            entries = [
                {"title": "Video 1", "url": "https://example.com/1", "duration": 61,
                 "filesize_mb": 25.5, "resolution": "1920x1080", "format_note": "1080p"},
                {"title": "Video 2", "url": "https://example.com/2", "duration": 30,
                 "filesize_mb": 15.2, "resolution": "1280x720", "format_note": "720p"},
            ]
            app._on_playlist_fetch_complete("https://example.com/list", entries)
        finally:
            module.ctk.CTkCheckBox = original_checkbox
            module.ctk.BooleanVar = original_boolvar
            module.ctk.CTkFrame = original_frame
            module.ctk.CTkLabel = original_label
            module.PlaylistItemRow = original_playlist_item
            design_tokens.Fonts = original_fonts
            module.Fonts = original_module_fonts

        assert app.playlist_source_url == "https://example.com/list"
        assert len(app.playlist_entries) == 2
        assert len(app.playlist_selection_vars) == 2

    def test_download_video_fetches_playlist_before_download(self):
        app = DownloadTab.__new__(DownloadTab)
        app.queue_paused_getter = lambda: False
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
        app = DownloadTab.__new__(DownloadTab)
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
        app = DownloadTab.__new__(DownloadTab)
        app.url_entry = _FakeEntry("https://www.youtube.com/watch?v=abc")
        app.is_playlist_fetching = False
        app.is_info_fetching = False
        app._show_download_error = Mock()
        app._start_playlist_fetch = Mock()
        app._start_video_info_fetch = Mock()

        app._fetch_download_data()

        app._start_video_info_fetch.assert_called_once()
        app._start_playlist_fetch.assert_not_called()

    def test_start_playlist_fetch_returns_when_info_fetching(self):
        app = DownloadTab.__new__(DownloadTab)
        app.is_playlist_fetching = False
        app.is_info_fetching = True
        app.error_panel = SimpleNamespace(hide_error=Mock())

        app._start_playlist_fetch("https://www.youtube.com/playlist?list=PL1")

        app.error_panel.hide_error.assert_not_called()

    def test_start_video_info_fetch_returns_when_playlist_fetching(self):
        app = DownloadTab.__new__(DownloadTab)
        app.is_playlist_fetching = True
        app.is_info_fetching = False
        app.error_panel = SimpleNamespace(hide_error=Mock())

        app._start_video_info_fetch("https://www.youtube.com/watch?v=abc")

        app.error_panel.hide_error.assert_not_called()

    def test_start_processing_feedback_cancels_previous_timer(self):
        app = DownloadTab.__new__(DownloadTab)
        app.download_status_label = _FakeLabel()
        app.animation_manager = SimpleNamespace(
            stop_animation=lambda _animation_id: None,
            format_processing_text=lambda base, tick: f"{base}{'.' * ((tick % 3) + 1)}",
        )
        app._spinner_animation_id = None
        app._processing_after_id = "after-prev"
        app.after_cancel = Mock()

        def fake_after(_delay, _callback, *_args):
            return "after-new"

        app.after = fake_after

        app._start_processing_feedback("Downloading")

        app.after_cancel.assert_called_once_with("after-prev")
        assert app._processing_after_id == "after-new"

    def test_update_playlist_summary_uses_selected_quality_size(self):
        app = DownloadTab.__new__(DownloadTab)
        app.playlist_summary_label = _FakeLabel()
        app.quality_menu = _FakeCombo("1080p")
        app.playlist_selection_vars = [_FakeVar(True), _FakeVar(True)]
        app.playlist_entries = [
            {
                "filesize_mb": 100,
                "size_by_quality_mb": {"1080p": 950.0, "720p": 300.0},
            },
            {
                "filesize_mb": 120,
                "size_by_quality_mb": {"1080p": 900.0, "720p": 320.0},
            },
        ]

        app._update_playlist_summary()

        latest = app.playlist_summary_label.calls[-1]
        assert latest["text"].startswith(f"{Icons.QUEUED_STATUS} 2/2")
        assert "1.8 GB" in latest["text"]

    def test_playlist_metrics_fallback_prefers_best_over_stale_entry(self):
        app = DownloadTab.__new__(DownloadTab)
        entry = {
            "filesize_mb": 12.0,
            "resolution": "640x360",
            "format_note": "360p",
            "size_by_quality_mb": {"En İyi": 96.0},
            "resolution_by_quality": {"En İyi": "1920x1080"},
            "format_note_by_quality": {"En İyi": "1080p"},
        }

        metrics = app._get_playlist_entry_quality_metrics(entry, "720p")

        assert metrics["size_mb"] == 96.0
        assert metrics["resolution"] == "1920x1080"
        assert metrics["format_note"] == "1080p"

    def test_update_playlist_summary_uses_best_fallback_when_quality_missing(self):
        app = DownloadTab.__new__(DownloadTab)
        app.playlist_summary_label = _FakeLabel()
        app.quality_menu = _FakeCombo("720p")
        app.playlist_selection_vars = [_FakeVar(True), _FakeVar(True)]
        app.playlist_entries = [
            {
                "filesize_mb": 8.0,
                "size_by_quality_mb": {"En İyi": 120.0},
                "resolution_by_quality": {"En İyi": "1920x1080"},
            },
            {
                "filesize_mb": 9.0,
                "size_by_quality_mb": {"En İyi": 80.0},
                "resolution_by_quality": {"En İyi": "1920x1080"},
            },
        ]

        app._update_playlist_summary()

        latest = app.playlist_summary_label.calls[-1]
        assert "200.0 MB" in latest["text"]

    def test_on_playlist_fetch_complete_opens_sort_dialog_when_enabled(self):
        app = DownloadTab.__new__(DownloadTab)
        app._hide_progress = Mock()
        app._stop_processing_feedback = Mock()
        app._set_button_loading_state = Mock()
        app._set_url_validation_state = Mock()
        app._open_playlist_sort_dialog = Mock()
        app._render_inline_playlist_entries = Mock()
        app.download_btn = _FakeButton()
        app.download_status_label = _FakeLabel()
        app.playlist_frame = _FakeFrame()
        app.playlist_list_frame = _FakeFrame()
        app.playlist_summary_label = _FakeLabel()
        app.playlist_selection_vars = []
        app.playlist_entries = []
        app.playlist_source_url = ""
        app.is_playlist_fetching = True
        app._playlist_sort_dialog_enabled = True
        app.quality_menu = _FakeCombo("720p")
        app.fetch_data_btn = _FakeButton()

        import ravn_app.ui.tabs._download_playlist as playlist_module

        original_boolvar = playlist_module.ctk.BooleanVar
        try:
            playlist_module.ctk.BooleanVar = lambda value=True: _FakeVar(value)
            entries = [{"title": "Video 1", "url": "https://example.com/1", "duration": 61}]
            app._on_playlist_fetch_complete("https://example.com/list", entries)
        finally:
            playlist_module.ctk.BooleanVar = original_boolvar

        app._open_playlist_sort_dialog.assert_called_once()
        app._render_inline_playlist_entries.assert_not_called()

    def test_on_playlist_fetch_complete_renders_selected_quality_details(self):
        app = DownloadTab.__new__(DownloadTab)
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
        app.quality_menu = _FakeCombo("720p")
        app._update_playlist_summary = Mock()

        import ravn_app.ui.tabs.download_tab as module
        from ravn_app.ui import design_tokens

        captured_label_texts = []

        class _CaptureLabel(_FakeLabel):
            def __init__(self, *_args, **kwargs):
                super().__init__()
                text = kwargs.get("text")
                if isinstance(text, str):
                    captured_label_texts.append(text)

        original_checkbox = module.ctk.CTkCheckBox
        original_boolvar = module.ctk.BooleanVar
        original_frame = module.ctk.CTkFrame
        original_label = module.ctk.CTkLabel
        original_playlist_item = module.PlaylistItemRow
        original_fonts = design_tokens.Fonts
        original_module_fonts = module.Fonts
        try:
            mock_fonts = Mock()
            mock_fonts.LABEL_BOLD = Mock()
            mock_fonts.SMALL = Mock()
            design_tokens.Fonts = mock_fonts
            module.Fonts = mock_fonts

            module.ctk.BooleanVar = lambda value=True: _FakeVar(value)
            module.ctk.CTkCheckBox = lambda *_args, **_kwargs: _FakeLabel()
            module.ctk.CTkFrame = lambda *_args, **_kwargs: _FakeFrame()
            module.ctk.CTkLabel = _CaptureLabel

            class _FakePlaylistItem(_FakeFrame):
                def __init__(self, *_args, **kwargs):
                    super().__init__()
                    detail_text = kwargs.get("detail_text")
                    if isinstance(detail_text, str):
                        captured_label_texts.append(detail_text)

                def set_detail_text(self, detail_text):
                    if isinstance(detail_text, str):
                        captured_label_texts.append(detail_text)

            module.PlaylistItemRow = _FakePlaylistItem

            entries = [
                {
                    "title": "Video 1",
                    "url": "https://example.com/1",
                    "duration": 61,
                    "filesize_mb": 120.0,
                    "resolution": "1920x1080",
                    "format_note": "1080p",
                    "size_by_quality_mb": {"1080p": 120.0, "720p": 65.4},
                    "resolution_by_quality": {"1080p": "1920x1080", "720p": "1280x720"},
                    "format_note_by_quality": {"1080p": "1080p", "720p": "720p"},
                }
            ]

            app._on_playlist_fetch_complete("https://example.com/list", entries)
        finally:
            module.ctk.CTkCheckBox = original_checkbox
            module.ctk.BooleanVar = original_boolvar
            module.ctk.CTkFrame = original_frame
            module.ctk.CTkLabel = original_label
            module.PlaylistItemRow = original_playlist_item
            design_tokens.Fonts = original_fonts
            module.Fonts = original_module_fonts

        assert any("1280x720" in text for text in captured_label_texts)
        assert any("65.4 MB" in text for text in captured_label_texts)


class TestQueuePanelLogic:
    def test_status_badge_uses_expected_colors(self):
        widget = QueueItemWidget.__new__(QueueItemWidget)

        assert widget._get_status_color(TaskStatus.QUEUED) == Colors.STATUS_QUEUED
        assert widget._get_status_color(TaskStatus.RUNNING) == Colors.STATUS_RUNNING
        assert widget._get_status_color(TaskStatus.COMPLETED) == Colors.STATUS_DONE

    def test_running_spinner_rotates_icon_frames(self):
        widget = QueueItemWidget.__new__(QueueItemWidget)
        widget.task = SimpleNamespace(status=TaskStatus.RUNNING)
        widget.status_label = _FakeLabel()
        widget._spinner_index = 0

        def fake_after(delay, _callback):
            widget._scheduled_delay = delay
            return "after-1"

        widget.after = fake_after

        widget._animate_running_spinner()

        assert widget.status_label.calls[-1]["text"] == widget._SPINNER_FRAMES[0]
        assert widget.status_label.calls[-1]["text_color"] == Colors.STATUS_RUNNING
        assert widget._scheduled_delay == 90

    def test_animate_entrance_delegates_to_animation_manager(self):
        widget = QueueItemWidget.__new__(QueueItemWidget)
        widget.animation_manager = SimpleNamespace(animate_queue_entrance=Mock())

        widget.animate_entrance()

        widget.animation_manager.animate_queue_entrance.assert_called_once()

