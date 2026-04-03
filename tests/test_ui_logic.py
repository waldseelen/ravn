"""
UI logic tests for tab widgets without rendering.
"""

import queue
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

from ravn_app.core.persistence import LibraryRegistrationResult
from ravn_app.core.task_manager import TaskResult, TaskStatus
from ravn_app.core.converter import AudioBitrate, VideoQuality
from ravn_app.core.i18n import t
from ravn_app.core.runners import TorrentProgressSnapshot
from ravn_app.ui.converter_tab import ConverterTab
from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab
from ravn_app.ui.main_window import YouTubeDownloaderApp
from ravn_app.ui.components.command_palette import PaletteCommand, CommandPaletteDialog
from ravn_app.ui.components.playlist_sort_dialog import PlaylistSortDialog
from ravn_app.ui.tabs.download_tab import DownloadTab
from ravn_app.ui.tabs.download_workspace import DownloadWorkspace
from ravn_app.ui.tabs.filters_tab import FiltersTab
from ravn_app.ui.tabs.library_tab import LibraryTab
from ravn_app.ui.tabs.mixer_tab import MixerTab
from ravn_app.ui.tabs.torrent_tab import TorrentTab
from ravn_app.ui.queue_panel import QueueItemWidget
from ravn_app.ui.subtitle_tab import SubtitleTab
from ravn_app.ui.design_tokens import Colors, Icons


class _FakeEntry:
    def __init__(self, value=""):
        self.value = value
        self.focused = False
        self.config = {}

    def get(self):
        return self.value

    def delete(self, _a, _b):
        self.value = ""

    def insert(self, _idx, value):
        self.value = value

    def focus_set(self):
        self.focused = True

    def configure(self, **kwargs):
        self.config.update(kwargs)


class _FakeCombo:
    def __init__(self, value):
        self.value = value
        self.config = {}

    def get(self):
        return self.value

    def set(self, value):
        self.value = value

    def configure(self, **kwargs):
        self.config.update(kwargs)


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
            "theme": "dark",
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
            "subtitle_fallback_language": "en",
            "subtitle_include_auto_generated": True,
            "auto_embed_subtitles": False,
            "auto_id3_tagging": True,
            "auto_embed_lyrics": True,
            "auto_sort_downloads": False,
            "auto_sort_mode": "artist",
            "download_naming_preset": "standard",
            "download_filename_template": "",
            "download_postprocess": {
                "extract_audio": False,
                "audio_format": "mp3",
                "audio_bitrate": "192k",
                "convert_enabled": False,
                "convert_format": "mkv",
                "embed_subtitles": False,
            },
            "download_robustness": {
                "enable_archive": True,
                "detect_duplicates": True,
                "continue_partial": True,
                "format_fallback": True,
                "rate_limit_kbps": 0,
            },
            "download_advanced": {
                "cookies_mode": "browser",
                "cookies_browser": "firefox",
                "cookies_profile": "default-release",
                "cookies_file": "",
                "concurrent_fragments": 3,
                "fragment_retries": 12,
                "socket_timeout_seconds": 45,
            },
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
    def __init__(self, width=120, hover_color="#333333", text=""):
        self._props = {
            "width": width,
            "hover_color": hover_color,
            "border_width": 0,
            "border_color": None,
            "text": text,
            "fg_color": None,
            "text_color": None,
        }
        self.focused = False
        self.pack_config = {}

    def cget(self, name):
        return self._props.get(name)

    def configure(self, **kwargs):
        self._props.update(kwargs)

    def pack_configure(self, **kwargs):
        self.pack_config.update(kwargs)

    def focus_set(self):
        self.focused = True


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


class _FakeToast:
    def __init__(self):
        self.successes = []
        self.warnings = []

    def show_success(self, message):
        self.successes.append(message)

    def show_warning(self, message):
        self.warnings.append(message)


class _FakeShortcutTab:
    def __init__(self, viewable=False):
        self.viewable = viewable
        self.calls = []

    def winfo_viewable(self):
        return self.viewable

    def _on_ctrl_enter(self, event=None):
        self.calls.append(("enter", event))

    def _on_escape(self, event=None):
        self.calls.append(("escape", event))

    def _on_ctrl_l(self, event=None):
        self.calls.append(("clear", event))
        return "break"


class _FakeFrame:
    def __init__(self):
        self._children = []
        self.calls = []
        self._manager = ""
        self.config = {}
        self.pack_config = {}
        self.raised = False

    def pack(self, **kwargs):
        self._manager = "pack"
        self.calls.append({"pack": kwargs})

    def grid(self, **kwargs):
        self._manager = "grid"
        self.calls.append({"grid": kwargs})

    def tkraise(self):
        self.raised = True
        self.calls.append({"tkraise": True})

    def pack_forget(self):
        self._manager = ""
        self.calls.append({"pack_forget": True})

    def pack_configure(self, **kwargs):
        self.pack_config.update(kwargs)

    def grid_rowconfigure(self, *_args, **_kwargs):
        return None

    def grid_columnconfigure(self, *_args, **_kwargs):
        return None

    def configure(self, **kwargs):
        self.config.update(kwargs)

    def winfo_children(self):
        return list(self._children)

    def winfo_manager(self):
        return self._manager


class _FakeFocusable:
    def __init__(self):
        self.focused = False

    def focus_set(self):
        self.focused = True


class _FakeTree:
    def __init__(self):
        self.items = {}
        self.selection_value = []
        self.focus_value = None

    def insert(self, parent, _index, iid, text="", values=()):
        self.items[iid] = {
            "parent": parent,
            "text": text,
            "values": tuple(values),
            "detached": False,
        }
        return iid

    def item(self, iid, **kwargs):
        if kwargs:
            self.items[iid].update(kwargs)
        return self.items[iid]

    def parent(self, iid):
        return self.items.get(iid, {}).get("parent", "")

    def selection(self):
        return tuple(self.selection_value)

    def selection_set(self, iid):
        if isinstance(iid, (tuple, list)):
            self.selection_value = list(iid)
        else:
            self.selection_value = [iid]

    def selection_remove(self, _items):
        self.selection_value = []

    def focus(self, iid):
        self.focus_value = iid

    def detach(self, iid):
        if iid in self.items:
            self.items[iid]["detached"] = True

    def move(self, iid, parent, _index):
        if iid in self.items:
            self.items[iid]["parent"] = parent
            self.items[iid]["detached"] = False

    def get_children(self, parent=""):
        return [
            iid
            for iid, item in self.items.items()
            if item.get("parent", "") == parent and not item.get("detached", False)
        ]


class TestConverterTabLogic:
    def test_get_quality_maps_labels(self):
        tab = ConverterTab.__new__(ConverterTab)
        tab.quality = _FakeCombo("Düşük")
        assert tab.get_quality() == VideoQuality.LOW

    def test_get_audio_bitrate_maps_labels(self):
        tab = ConverterTab.__new__(ConverterTab)
        tab.audio_bitrate = _FakeCombo("192k (Yüksek)")
        assert tab.get_audio_bitrate() == AudioBitrate.HIGH

    def test_conversion_success_triggers_library_auto_add(self):
        tab = ConverterTab.__new__(ConverterTab)
        tab._spinner_animation_id = None
        tab.animation_manager = SimpleNamespace(animate_button_enabled=lambda *_args, **_kwargs: None)
        tab.convert_btn = _FakeButton()
        tab.stop_btn = _FakeButton()
        tab.status_label = _FakeLabel()
        tab.progress_var = SimpleNamespace(set=lambda _value: None)
        tab.db_manager = Mock()
        tab.notify_callback = Mock()
        tab.auto_add_to_library_callback = Mock()

        settings = SimpleNamespace(
            input_file="C:/media/input.mp4",
            output_file="C:/media/output.mkv",
            video_codec=SimpleNamespace(name="H265"),
            audio_codec=SimpleNamespace(name="AAC"),
            audio_only=False,
            video_only=False,
        )

        import ravn_app.ui.converter_tab as module

        original_loading_state = module.set_button_loading_state
        original_showinfo = module.messagebox.showinfo
        try:
            module.set_button_loading_state = lambda *_args, **_kwargs: None
            module.messagebox.showinfo = lambda *_args, **_kwargs: None
            tab._on_conversion_success(settings, duration=2.5)
        finally:
            module.set_button_loading_state = original_loading_state
            module.messagebox.showinfo = original_showinfo

        tab.auto_add_to_library_callback.assert_called_once_with(
            "C:/media/output.mkv",
            source_type="conversion",
            metadata={
                "input_file": "C:/media/input.mp4",
                "video_codec": "h265",
                "audio_codec": "aac",
                "audio_only": False,
                "video_only": False,
            },
        )


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

    def test_quality_normalization_handles_legacy_labels(self):
        assert SettingsTab._normalize_quality_for_storage("Best") == "best"
        assert SettingsTab._normalize_quality_for_storage("En Iyi") == "best"
        assert SettingsTab._normalize_quality_for_storage("En İyi") == "best"

    def test_save_settings_writes_expected_keys(self):
        tab = SettingsTab.__new__(SettingsTab)
        tab.config = _FakeConfig()
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
        tab.subtitle_fallback_combo = _FakeCombo("none")
        tab.subtitle_auto_generated_var = _FakeVar(True)
        tab.auto_embed_subtitles_var = _FakeVar(True)
        tab.auto_id3_var = _FakeVar(True)
        tab.auto_lyrics_var = _FakeVar(True)
        tab.auto_sort_var = _FakeVar(True)
        tab.auto_sort_mode_combo = _FakeCombo("Sanatçı")
        tab.naming_preset_combo = _FakeCombo("clean")
        tab.filename_template_entry = _FakeEntry("{uploader}/{title}")
        tab.postprocess_extract_audio_var = _FakeVar(True)
        tab.postprocess_audio_format_combo = _FakeCombo("MP3")
        tab.postprocess_audio_bitrate_combo = _FakeCombo("320k")
        tab.postprocess_convert_var = _FakeVar(True)
        tab.postprocess_convert_format_combo = _FakeCombo("MKV")
        tab.postprocess_embed_subtitles_var = _FakeVar(True)
        tab.download_archive_var = _FakeVar(True)
        tab.download_duplicate_var = _FakeVar(True)
        tab.download_continue_partial_var = _FakeVar(True)
        tab.download_format_fallback_var = _FakeVar(True)
        tab.download_rate_limit_entry = _FakeEntry("512")
        tab.download_cookie_mode_combo = _FakeCombo(t("settings.downloadAdvancedCookiesBrowser"))
        tab.download_cookie_browser_combo = _FakeCombo("firefox")
        tab.download_cookie_profile_entry = _FakeEntry("default-release")
        tab.download_cookie_file_entry = _FakeEntry("")
        tab.download_concurrent_fragments_entry = _FakeEntry("4")
        tab.download_fragment_retries_entry = _FakeEntry("9")
        tab.download_socket_timeout_entry = _FakeEntry("60")
        tab.close_behavior_combo = _FakeCombo("Sistem Çekmecesine Küçült")

        import ravn_app.ui.history_settings_tab as module

        original_showinfo = module.messagebox.showinfo
        try:
            module.messagebox.showinfo = lambda *_args, **_kwargs: None
            tab.save_settings()
        finally:
            module.messagebox.showinfo = original_showinfo

        keys = {key for key, _ in tab.config.writes}
        assert "theme" not in keys
        assert "language" not in keys
        assert "default_download_path" in keys
        assert "history_limit" in keys
        assert "auto_id3_tagging" in keys
        assert "subtitle_fallback_language" in keys
        assert "subtitle_include_auto_generated" in keys
        assert "auto_embed_subtitles" in keys
        assert "auto_embed_lyrics" in keys
        assert "auto_sort_downloads" in keys
        assert "auto_sort_mode" in keys
        assert "download_naming_preset" in keys
        assert "download_filename_template" in keys
        assert "download_postprocess" in keys
        assert "download_robustness" in keys
        assert "download_advanced" in keys


class TestPlaylistSortDialogLogic:
    def test_format_bytes_outputs_expected_units(self):
        assert PlaylistSortDialog._format_bytes(0) == "0 B"
        assert PlaylistSortDialog._format_bytes(1024) == "1.0 KB"
        assert PlaylistSortDialog._format_bytes(1024 * 1024) == "1.0 MB"

    def test_parse_duration_filter_supports_seconds_and_mmss(self):
        assert PlaylistSortDialog._parse_duration_filter("90") == 90.0
        assert PlaylistSortDialog._parse_duration_filter("02:30") == 150.0
        assert PlaylistSortDialog._parse_duration_filter("01:02:03") == 3723.0
        assert PlaylistSortDialog._parse_duration_filter("bad") is None

    def test_filter_rows_supports_title_duration_and_popularity(self):
        dialog = PlaylistSortDialog.__new__(PlaylistSortDialog)
        dialog._all_rows = [
            {"index": 0, "title_sort": "alpha", "duration": 60.0, "view_count": 10},
            {"index": 1, "title_sort": "beta clip", "duration": 180.0, "view_count": 500},
            {"index": 2, "title_sort": "beta live", "duration": 240.0, "view_count": 200},
        ]

        rows = dialog._filter_rows(
            title_query="beta",
            min_duration=120.0,
            max_duration=220.0,
            popularity_mode="top50",
        )

        assert [row["index"] for row in rows] == [1]

    def test_apply_range_selection_marks_requested_indexes(self):
        dialog = PlaylistSortDialog.__new__(PlaylistSortDialog)
        dialog._all_rows = [
            {"index": 0, "position": 1, "selected": True},
            {"index": 1, "position": 2, "selected": True},
            {"index": 2, "position": 3, "selected": True},
            {"index": 3, "position": 4, "selected": True},
        ]
        dialog.range_start_entry = _FakeEntry("2")
        dialog.range_end_entry = _FakeEntry("3")
        dialog._refresh_tree = Mock()

        dialog._apply_range_selection()

        assert [row["selected"] for row in dialog._all_rows] == [False, True, True, False]
        dialog._refresh_tree.assert_called_once()


class TestTorrentTabLogic:
    def test_resolve_play_target_prefers_primary_file(self):
        row = {
            "primary_file": "C:/media/movie.mkv",
            "stream_url": "http://127.0.0.1:8080/movie.mkv",
            "play_target": None,
        }
        assert TorrentTab._resolve_play_target(row) == "C:/media/movie.mkv"

    def test_format_progress_status_includes_eta_and_size(self):
        tab = TorrentTab.__new__(TorrentTab)
        progress = TorrentProgressSnapshot(
            percent=33,
            speed_text="4MiB/s",
            eta_text="2m",
            downloaded_text="1.0 GB",
            total_text="3.0 GB",
        )
        assert tab._format_progress_status(progress) == "33% • 4MiB/s • ETA 2m • 1.0 GB / 3.0 GB"

    def test_selected_session_id_returns_parent_for_child_rows(self):
        tab = TorrentTab.__new__(TorrentTab)
        tab._downloads_tree = _FakeTree()
        tab._download_rows = {"torrent-1": {}}
        tab._downloads_tree.insert("", "end", iid="torrent-1", text="Torrent")
        tab._downloads_tree.insert("torrent-1", "end", iid="torrent-1::file::1", text="movie.mkv")
        tab._downloads_tree.selection_set("torrent-1::file::1")

        assert tab._get_selected_session_id() == "torrent-1"

    def test_enqueue_download_updates_queue_position_labels(self):
        tab = TorrentTab.__new__(TorrentTab)
        tab._downloads_tree = _FakeTree()
        tab._download_queue = __import__("collections").deque()
        tab._session_order = ["torrent-1", "torrent-2"]
        tab._active_filter_key = "all"
        tab._download_rows = {
            "torrent-1": {"name": "A", "mode": "Full", "status": "", "progress": "0%", "downloaded": "0 B", "total_size": "—", "remaining": "—", "speed": "—", "eta": "—", "peers": "—", "seeders": "—", "queue_state": "pending"},
            "torrent-2": {"name": "B", "mode": "Full", "status": "", "progress": "0%", "downloaded": "0 B", "total_size": "—", "remaining": "—", "speed": "—", "eta": "—", "peers": "—", "seeders": "—", "queue_state": "pending"},
        }
        tab._downloads_tree.insert("", "end", iid="torrent-1", text="A", values=TorrentTab._build_row_values(tab._download_rows["torrent-1"]))
        tab._downloads_tree.insert("", "end", iid="torrent-2", text="B", values=TorrentTab._build_row_values(tab._download_rows["torrent-2"]))

        tab._enqueue_download("torrent-1")
        tab._enqueue_download("torrent-2")

        assert list(tab._download_queue) == ["torrent-1", "torrent-2"]
        assert "#1" in tab._download_rows["torrent-1"]["status"]
        assert "#2" in tab._download_rows["torrent-2"]["status"]

    def test_apply_session_filter_hides_non_matching_rows(self):
        tab = TorrentTab.__new__(TorrentTab)
        tab._downloads_tree = _FakeTree()
        tab._download_rows = {
            "torrent-1": {"name": "Queued", "mode": "Full", "status": "", "progress": "0%", "downloaded": "0 B", "total_size": "—", "remaining": "—", "speed": "—", "eta": "—", "peers": "—", "seeders": "—", "queue_state": "queued"},
            "torrent-2": {"name": "Paused", "mode": "Full", "status": "", "progress": "0%", "downloaded": "0 B", "total_size": "—", "remaining": "—", "speed": "—", "eta": "—", "peers": "—", "seeders": "—", "queue_state": "paused"},
        }
        tab._file_rows = {}
        tab._session_order = ["torrent-1", "torrent-2"]
        tab._active_filter_key = "queued"
        tab._downloads_tree.insert("", "end", iid="torrent-1", text="Queued", values=TorrentTab._build_row_values(tab._download_rows["torrent-1"]))
        tab._downloads_tree.insert("", "end", iid="torrent-2", text="Paused", values=TorrentTab._build_row_values(tab._download_rows["torrent-2"]))

        tab._apply_session_filter()

        assert tab._downloads_tree.get_children("") == ["torrent-1"]

    def test_selected_open_target_prefers_child_file_path(self):
        tab = TorrentTab.__new__(TorrentTab)
        tab._downloads_tree = _FakeTree()
        tab._download_rows = {
            "torrent-1": {
                "primary_file": "C:/media/movie.mkv",
                "stream_url": None,
                "play_target": None,
            }
        }
        tab._file_rows = {"torrent-1::file::1": {"parent_id": "torrent-1", "file_path": "C:/media/extra.srt"}}
        tab._downloads_tree.insert("", "end", iid="torrent-1", text="Torrent")
        tab._downloads_tree.insert("torrent-1", "end", iid="torrent-1::file::1", text="extra.srt")
        tab._downloads_tree.selection_set("torrent-1::file::1")

        assert tab._selected_open_target() == "C:/media/extra.srt"


class TestPhase7TabLogic:
    def test_mixer_input_requirements(self):
        assert MixerTab._input_requirement("audio", "trim") == ("exact", 1)
        assert MixerTab._input_requirement("audio", "concat") == ("min", 2)
        assert MixerTab._input_requirement("video", "overlay") == ("exact", 2)

    def test_library_parse_tags_deduplicates(self):
        assert LibraryTab._parse_tags(" Work, tutorial,work , demo ") == ["work", "tutorial", "demo"]

    def test_filters_summary_omits_empty_values(self):
        summary = FiltersTab._summarize_active_filters(
            {
                "brightness": 0,
                "contrast": 1.2,
                "grayscale": True,
                "lut_file": "",
            }
        )
        assert summary == ["contrast=1.2", "grayscale"]

    def test_download_behavior_settings_apply_selected_profile(self):
        tab = DownloadTab.__new__(DownloadTab)
        tab.config_manager = _FakeConfig()
        tab.download_profile_menu = _FakeCombo(t("download.profileMusic"))

        settings = tab._get_download_behavior_settings()

        assert settings["naming_preset"] == "clean"
        assert settings["embed_metadata"] is True
        assert settings["auto_sort_enabled"] is True
        assert settings["audio_bitrate"] == "320K"
        assert settings["robustness_profile"]["enable_archive"] is True
        assert settings["advanced_profile"]["cookies_mode"] == "browser"
        assert settings["advanced_profile"]["concurrent_fragments"] == 3

    def test_settings_advanced_cookie_mode_updates_widget_state(self):
        tab = SettingsTab.__new__(SettingsTab)
        tab.download_cookie_mode_combo = _FakeCombo(t("settings.downloadAdvancedCookiesBrowser"))
        tab.download_cookie_browser_combo = _FakeCombo("chrome")
        tab.download_cookie_profile_entry = _FakeEntry("Default")
        tab.download_cookie_file_entry = _FakeEntry("")

        tab._update_download_advanced_controls_state()

        assert tab.download_cookie_browser_combo.config["state"] == "normal"
        assert tab.download_cookie_profile_entry.config["state"] == "normal"
        assert tab.download_cookie_file_entry.config["state"] == "disabled"

        tab.download_cookie_mode_combo.set(t("settings.downloadAdvancedCookiesFile"))
        tab._update_download_advanced_controls_state()

        assert tab.download_cookie_browser_combo.config["state"] == "disabled"
        assert tab.download_cookie_file_entry.config["state"] == "normal"

    def test_download_register_outputs_uses_library_callback(self):
        tab = DownloadTab.__new__(DownloadTab)
        captured = []
        tab.auto_add_to_library_callback = lambda paths, **kwargs: captured.append((paths, kwargs))

        tab._register_download_outputs(
            SimpleNamespace(
                output_files=["C:/media/output.mp4", ""],
                url="https://example.com/watch?v=1",
                title="Example Output",
                metadata={"library_tags": ["downloaded", "youtube"]},
            )
        )

        assert captured == [
            (
                ["C:/media/output.mp4"],
                {
                    "source_type": "download",
                    "title": "Example Output",
                    "tags": ["downloaded", "youtube"],
                    "metadata": {
                        "library_tags": ["downloaded", "youtube"],
                        "source_url": "https://example.com/watch?v=1",
                    },
                },
            )
        ]

    def test_download_success_duplicate_skip_shows_warning_without_registering_outputs(self):
        tab = DownloadTab.__new__(DownloadTab)
        toast = _FakeToast()
        tab._stop_processing_feedback = Mock()
        tab.download_progress = _FakeProgressBar()
        tab.download_status_label = _FakeLabel()
        tab.animation_manager = SimpleNamespace(animate_success_flash=Mock())
        tab._animate_download_completion_pulse = Mock()
        tab._register_download_outputs = Mock()
        tab.toast_manager_getter = lambda: toast
        tab._set_button_loading_state = Mock()
        tab.download_btn = _FakeActionButton(text="Download")
        tab._active_btn_restore_text = "Download"
        tab.after = lambda *_args, **_kwargs: "after-1"

        tab._on_download_success(
            SimpleNamespace(
                output_files=[],
                metadata={"robustness": {"archive_skipped": True}},
            )
        )

        assert tab.download_progress.values[-1] == 1.0
        assert tab.download_status_label.calls[-1]["text"] == t("download.downloadSkippedDuplicate")
        tab._register_download_outputs.assert_not_called()
        assert toast.warnings == [t("download.downloadSkippedDuplicate")]
        assert toast.successes == []

    def test_download_success_registers_outputs_and_shows_success_toast(self):
        tab = DownloadTab.__new__(DownloadTab)
        toast = _FakeToast()
        tab._stop_processing_feedback = Mock()
        tab.download_progress = _FakeProgressBar()
        tab.download_status_label = _FakeLabel()
        tab.animation_manager = SimpleNamespace(animate_success_flash=Mock())
        tab._animate_download_completion_pulse = Mock()
        tab._register_download_outputs = Mock()
        tab.toast_manager_getter = lambda: toast
        tab._set_button_loading_state = Mock()
        tab.download_btn = _FakeActionButton(text="Download")
        tab._active_btn_restore_text = "Download"
        tab.bell = Mock()
        tab.after = lambda *_args, **_kwargs: "after-1"

        import ravn_app.ui.tabs._download_feedback as feedback_module
        original_notify = feedback_module.NotificationManager.show_download_complete
        try:
            feedback_module.NotificationManager.show_download_complete = lambda *_args, **_kwargs: None
            tab._on_download_success(
                SimpleNamespace(
                    output_files=["C:/media/output.mp4"],
                    metadata={"robustness": {"archive_skipped": False}},
                )
            )
        finally:
            feedback_module.NotificationManager.show_download_complete = original_notify

        tab._register_download_outputs.assert_called_once()
        assert toast.successes
        assert tab.download_btn.cget("text") == "Download"

    def test_mixer_task_complete_triggers_library_auto_add(self):
        tab = MixerTab.__new__(MixerTab)
        tab._active_task_id = "mix-1"
        tab._active_task_context = {
            "operation": "mix",
            "mode": "audio",
            "inputs": ["a.mp3", "b.mp3"],
            "output_path": "C:/media/mix.mp3",
        }
        tab._set_running = Mock()
        tab.progress_bar = _FakeProgressBar()
        tab.status_label = _FakeLabel()
        tab.operation_combo = _FakeCombo("Mix")
        tab._append_log = Mock()
        tab._persist_task_record = Mock()
        tab.auto_add_to_library_callback = Mock()
        tab.toast_manager_getter = lambda: None
        tab._reset_active_task = Mock()

        task = SimpleNamespace(
            id="mix-1",
            result=TaskResult(success=True, output_path="C:/media/mix.mp3", metadata={"track_count": 2}),
        )

        tab._on_task_complete(task)

        tab.auto_add_to_library_callback.assert_called_once_with(
            "C:/media/mix.mp3",
            source_type="mixer",
            metadata={
                "track_count": 2,
                "operation": "mix",
                "mode": "audio",
                "input_paths": ["a.mp3", "b.mp3"],
            },
        )

    def test_filters_task_complete_triggers_library_auto_add(self):
        tab = FiltersTab.__new__(FiltersTab)
        tab._active_task_id = "filter-1"
        tab._active_task_context = {
            "input_file": "C:/media/input.mp4",
            "output_path": "C:/media/filtered.mp4",
        }
        tab._set_running = Mock()
        tab.progress_bar = _FakeProgressBar()
        tab.status_label = _FakeLabel()
        tab._append_log = Mock()
        tab._persist_task_record = Mock()
        tab.auto_add_to_library_callback = Mock()
        tab.toast_manager_getter = lambda: None
        tab._reset_active_task = Mock()

        task = SimpleNamespace(
            id="filter-1",
            result=TaskResult(success=True, output_path="C:/media/filtered.mp4", metadata={"filters": ["eq=brightness=0.1"]}),
        )

        tab._on_task_complete(task)

        tab.auto_add_to_library_callback.assert_called_once_with(
            "C:/media/filtered.mp4",
            source_type="filters",
            metadata={
                "filters": ["eq=brightness=0.1"],
                "input_file": "C:/media/input.mp4",
            },
        )


class TestMainWindowLogic:
    def test_detect_url_protocol_handles_uppercase_magnet(self):
        assert DownloadTab._detect_url_protocol("MAGNET:?xt=urn:btih:abc123") == "magnet"

    def test_detect_url_protocol_handles_magnet_with_dn_before_xt(self):
        assert DownloadTab._detect_url_protocol("magnet:?dn=Example&xt=urn:btih:abc123") == "magnet"

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

    def test_shortcuts_delegate_to_phase7_tabs(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.download_tab = _FakeShortcutTab(viewable=False)
        app.converter_tab = _FakeShortcutTab(viewable=False)
        app.subtitle_tab = _FakeShortcutTab(viewable=False)
        app.mixer_tab = _FakeShortcutTab(viewable=False)
        app.filters_tab = _FakeShortcutTab(viewable=True)
        app.library_tab = _FakeShortcutTab(viewable=False)

        app._on_ctrl_enter()
        result = app._on_ctrl_l()

        assert app.filters_tab.calls[0][0] == "enter"
        assert app.filters_tab.calls[1][0] == "clear"
        assert result == "break"

    def test_register_outputs_with_library_schedules_refresh(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.media_library_auto_adder = Mock()
        app.media_library_auto_adder.register_outputs.return_value = [
            LibraryRegistrationResult(
                file_path="C:/media/output.mp4",
                source_type="conversion",
                media_id=1,
                added=True,
            )
        ]
        refresh = Mock()
        home_refresh = Mock()
        app.library_tab = SimpleNamespace(refresh_dashboard=refresh)
        app.home_workspace = SimpleNamespace(refresh_dashboard=home_refresh)
        app.__dict__["_ui_callback_queue"] = queue.Queue()

        results = app._register_outputs_with_library(
            "C:/media/output.mp4",
            source_type="conversion",
            metadata={"input_file": "C:/media/input.mov"},
        )

        assert results[0].added is True
        app.media_library_auto_adder.register_outputs.assert_called_once_with(
            "C:/media/output.mp4",
            source_type="conversion",
            title=None,
            tags=None,
            metadata={"input_file": "C:/media/input.mov"},
        )
        app._process_ui_callbacks()
        refresh.assert_called_once()
        home_refresh.assert_called_once()

    def test_show_download_view_selects_mode(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        download_workspace = _FakeFrame()
        download_workspace.select_mode = Mock()
        app._workspace_frames = {"download": download_workspace}
        app.download_workspace = download_workspace
        app._sidebar_buttons = {}
        app._workspace_meta = lambda: {"download": ("Download", "Downloader")}
        app.workspace_title_label = _FakeLabel()
        app.workspace_subtitle_label = _FakeLabel()
        app._update_navigation_state = Mock()
        app._refresh_header_actions = Mock()
        app.home_workspace = None
        app._current_view_key = None

        app.show_download_view("torrent")

        download_workspace.select_mode.assert_called_once_with("torrent")
        assert app._last_primary_view_key == "download"
        assert app._current_view_key == "download"

    def test_download_workspace_select_mode_updates_segment_for_programmatic_switch(self):
        workspace = DownloadWorkspace.__new__(DownloadWorkspace)
        workspace._MODE_KEYS = ("url", "playlist", "batch", "torrent")
        workspace._segment_value_to_key = {
            "URL": "url",
            "Playlist": "playlist",
            "Batch": "batch",
            "Torrent": "torrent",
        }
        workspace.mode_selector = _FakeCombo("URL")
        workspace.download_tab = _FakeFrame()
        workspace.torrent_tab = _FakeFrame()
        workspace._sync_standard_mode = Mock()

        workspace.select_mode("torrent")

        assert workspace.mode_selector.get() == "Torrent"
        assert workspace.torrent_tab.winfo_manager() == "pack"
        workspace._sync_standard_mode.assert_not_called()

    def test_open_and_close_drawer_updates_state(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        queue_drawer = _FakeFrame()
        app._drawer_frames = {"queue": queue_drawer}
        app.drawer_shell = _FakeFrame()
        app.drawer_title_label = _FakeLabel()
        app.drawer_subtitle_label = _FakeLabel()
        app.drawer_close_button = _FakeActionButton()
        app._drawer_meta = lambda: {"queue": ("Queue panel", "Live tasks")}
        app._refresh_header_actions = Mock()
        app._active_drawer_key = None
        app.after = lambda _delay, callback: callback()
        app.focus_get = lambda: None

        app._open_drawer("queue")
        assert app._active_drawer_key == "queue"
        assert queue_drawer.calls[0]["pack"]["fill"] == "both"
        assert app.drawer_shell.winfo_manager() == "pack"

        app._close_drawer()
        assert app._active_drawer_key is None
        assert app.drawer_shell.winfo_manager() == ""

    def test_escape_closes_active_drawer_before_tab_handler(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._active_drawer_key = "queue"
        app._close_drawer = Mock()

        result = app._on_escape()

        app._close_drawer.assert_called_once()
        assert result == "break"

    def test_quick_paste_url_populates_download_input(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.show_download_view = Mock()
        app.clipboard_get = Mock(return_value="https://example.com/video")
        entry = _FakeEntry()
        app.download_tab = SimpleNamespace(url_entry=entry, _on_url_changed=Mock())

        app._quick_paste_url()

        app.show_download_view.assert_called_once_with("url")
        assert entry.get() == "https://example.com/video"
        assert entry.focused is True
        app.download_tab._on_url_changed.assert_called_once()

    @patch("ravn_app.ui.main_window.CommandPaletteDialog")
    def test_open_command_palette_creates_dialog(self, mock_dialog):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._build_command_palette_commands = Mock(return_value=[])
        app.__dict__["_command_palette"] = None

        app.open_command_palette()

        mock_dialog.assert_called_once()
        assert app.__dict__["_command_palette"] is mock_dialog.return_value

    def test_command_palette_filters_commands(self):
        commands = [
            PaletteCommand("open-home", "Open Home", "Dashboard", action=lambda: None, keywords=("home",)),
            PaletteCommand("open-queue", "Open Queue", "Tasks", action=lambda: None, keywords=("queue",)),
        ]

        filtered = CommandPaletteDialog.filter_commands(commands, "queue")

        assert len(filtered) == 1
        assert filtered[0].key == "open-queue"

    def test_build_command_palette_commands_exposes_expected_actions(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.show_workspace = Mock()
        app.show_download_view = Mock()
        app.show_studio_view = Mock()
        app.show_library_view = Mock()
        app.show_queue_view = Mock()
        app.show_settings_view = Mock()
        app._quick_paste_url = Mock()
        app._quick_convert_file = Mock()

        commands = app._build_command_palette_commands()
        command_keys = {command.key for command in commands}

        assert "open-home" in command_keys
        assert "open-download" in command_keys
        assert "open-queue" in command_keys
        assert "open-settings" in command_keys
        assert "paste-url" in command_keys

    def test_apply_responsive_shell_state_updates_compact_labels(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.sidebar = _FakeFrame()
        app.header = _FakeFrame()
        app.stage_frame = _FakeFrame()
        footer_frame = _FakeFrame()
        app.footer_status_label = SimpleNamespace(master=footer_frame)
        app.drawer_shell = _FakeFrame()
        app.quick_actions_label = _FakeLabel()
        app.command_palette_button = _FakeActionButton(text="Command Palette")
        app._quick_action_buttons = {
            "paste": _FakeActionButton(text="Paste URL"),
            "torrent": _FakeActionButton(text="Add Torrent"),
            "convert": _FakeActionButton(text="Convert File"),
            "library": _FakeActionButton(text="Open Library"),
        }

        app._apply_responsive_shell_state(1200)

        assert app.sidebar.config["width"] == 210
        assert app.drawer_shell.config["width"] == 340
        assert app.command_palette_button.cget("text")
        assert "Paste" in app._quick_action_buttons["paste"].cget("text") or "Yapistir" in app._quick_action_buttons["paste"].cget("text")

    def test_show_settings_view_switches_to_settings_workspace(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._show_view = Mock()

        app.show_settings_view()

        app._show_view.assert_called_once_with("settings")

    def test_toggle_theme_persists_and_applies_without_rebuild(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.config_manager = _FakeConfig()
        app._refresh_sidebar_utility_controls = Mock()
        app._refresh_header_actions = Mock()

        import ravn_app.ui.main_window as module

        with patch.object(module.ThemeManager, "apply_theme") as apply_theme, patch.object(module.Tooltip, "dismiss_all"):
            app._toggle_theme()

        assert ("theme", "light") in app.config_manager.writes
        apply_theme.assert_called_once_with("light")
        app._refresh_sidebar_utility_controls.assert_called_once()
        app._refresh_header_actions.assert_called_once()

    def test_toggle_language_persists_and_refreshes_shell(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.config_manager = _FakeConfig()
        app.refresh_i18n = Mock()

        fake_i18n = Mock()
        import ravn_app.ui.main_window as module

        with patch.object(module, "get_i18n", return_value=fake_i18n):
            app._toggle_language()

        assert ("language", "en") in app.config_manager.writes
        fake_i18n.set_language.assert_called_once_with("en", persist=False)
        app.refresh_i18n.assert_called_once()

    def test_refresh_i18n_syncs_runtime_language_without_shell_rebuild(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app.config_manager = SimpleNamespace(get=lambda key, default=None: "en" if key == "language" else default)
        app.__dict__["_command_palette"] = None
        app.__dict__["_sidebar_button_labels"] = {}
        app.__dict__["_current_view_key"] = None
        app.__dict__["_last_primary_view_key"] = "home"
        app.__dict__["_active_drawer_key"] = None
        app.home_workspace = None
        app.download_workspace = None
        app.studio_workspace = None
        app.library_workspace = None
        app.settings_tab = None
        app.queue_tab = None
        app._resync_workspace_tab_references = Mock()
        app._update_navigation_state = Mock()
        app._refresh_sidebar_utility_controls = Mock()
        app._apply_responsive_shell_state = Mock()
        app._refresh_header_actions = Mock()
        app._workspace_meta = lambda: {"home": ("Home", "Subtitle")}
        app.winfo_width = lambda: 1400
        app.workspace_title_label = _FakeLabel()
        app.workspace_subtitle_label = _FakeLabel()

        fake_i18n = Mock()
        import ravn_app.ui.main_window as module

        with patch.object(module, "get_i18n", return_value=fake_i18n), patch.object(module.Tooltip, "dismiss_all"):
            app.refresh_i18n()

        fake_i18n.set_language.assert_called_once_with("en", persist=False)
        app._resync_workspace_tab_references.assert_called_once()
        app._apply_responsive_shell_state.assert_called_once_with(1400)
        assert app.i18n is fake_i18n

    def test_update_navigation_state_uses_non_color_active_marker(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._current_view_key = "download"
        app._sidebar_button_labels = {"home": "Home", "download": "Download"}
        app._sidebar_buttons = {
            "home": _FakeActionButton(text="Home"),
            "download": _FakeActionButton(text="Download"),
        }

        import ravn_app.ui.main_window as module
        original_fonts = module.Fonts
        try:
            module.Fonts = SimpleNamespace(LABEL="label", LABEL_BOLD="label_bold")
            app._update_navigation_state()
        finally:
            module.Fonts = original_fonts

        assert app._sidebar_buttons["download"].cget("text").startswith("› ")
        assert app._sidebar_buttons["home"].cget("text") == "Home"

    def test_close_drawer_restores_focus_target(self):
        app = YouTubeDownloaderApp.__new__(YouTubeDownloaderApp)
        app._active_drawer_key = "queue"
        app._drawer_frames = {"queue": _FakeFrame()}
        app.drawer_shell = _FakeFrame()
        app.drawer_shell.pack()
        focus_target = _FakeFocusable()
        app._drawer_return_focus = focus_target
        app._refresh_header_actions = Mock()

        app._close_drawer()

        assert focus_target.focused is True
        assert app._active_drawer_key is None

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
        app.batch_mode_var = _FakeVar(False)
        app.mode_selector = _FakeCombo("Video")
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

        app._execute_download()

        app._show_download_error.assert_called_once()
        app._start_playlist_fetch.assert_not_called()
        app._start_single_download.assert_not_called()

    def test_toggle_batch_mode_handles_missing_shared_fetch_button(self):
        app = DownloadTab.__new__(DownloadTab)
        app.batch_mode_var = _FakeVar(True)
        app.url_input_row = _FakeLabel()
        app.batch_url_frame = _FakeLabel()
        app.info_label = _FakeLabel()
        app.platform_manager = _FakeBadgeManager({"icon": "?", "label": "Unknown", "color": "#666", "platform": "unknown"})
        app._video_fetch_btn = _FakeButton()
        app._music_fetch_btn = _FakeButton()
        app._set_button_loading_state = Mock()

        app._toggle_batch_mode()

        assert any("pack_forget" in call for call in app.url_input_row.calls)
        assert app._set_button_loading_state.call_count == 2

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

