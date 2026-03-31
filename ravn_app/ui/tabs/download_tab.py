"""Download tab implementation extracted from the main window."""

import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from ravn_app.core.downloader import DownloadFormat, DownloadQuality
from ravn_app.core.i18n import t
from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode
from ravn_app.core.task_manager import TaskType
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.components.playlist_item import PlaylistItemRow
from ravn_app.ui.components.url_input import UrlInputRow
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Motion, Sizes
from ravn_app.ui.tabs._download_feedback import FeedbackMixin
from ravn_app.ui.tabs._download_playlist import PlaylistMixin
from ravn_app.ui.ui_components import Tooltip

try:
    from tkinterdnd2 import DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False


_QUALITY_MAP = {
    "En İyi": DownloadQuality.BEST,
    "En Iyi": DownloadQuality.BEST,
    "Best": DownloadQuality.BEST,
    "1080p": DownloadQuality.HIGH_1080P,
    "720p": DownloadQuality.MEDIUM_720P,
    "480p": DownloadQuality.LOW_480P,
    "Sadece Ses": DownloadQuality.AUDIO_ONLY,
    "Audio Only": DownloadQuality.AUDIO_ONLY,
    # Audio mode — bitrate seçenekleri: hepsi AUDIO_ONLY kalite spec'i kullanır
    "320k": DownloadQuality.AUDIO_ONLY,
    "192k": DownloadQuality.AUDIO_ONLY,
    "128k": DownloadQuality.AUDIO_ONLY,
}

# Bitrate label → yt-dlp --audio-quality arg
_AUDIO_BITRATE_MAP = {
    "Best": "0",
    "En İyi": "0",
    "En Iyi": "0",
    "320k": "320K",
    "192k": "192K",
    "128k": "128K",
}

_FORMAT_MAP = {
    "MP4":  DownloadFormat.MP4,
    "WebM": DownloadFormat.WEBM,
    "MKV":  DownloadFormat.MKV,
    "MP3":  DownloadFormat.MP3,
    "M4A":  DownloadFormat.M4A,
    "FLAC": DownloadFormat.FLAC,
    "OPUS": DownloadFormat.OPUS,
    "WAV":  DownloadFormat.WAV,
    "AAC":  DownloadFormat.AAC,
}

_VIDEO_FORMATS  = ["MP4", "WebM", "MKV"]
_AUDIO_FORMATS  = ["MP3", "AAC", "FLAC", "OPUS", "WAV", "M4A"]


class DownloadTab(FeedbackMixin, PlaylistMixin, ctk.CTkFrame):
    """Download tab with playlist and batch flow support."""

    def __init__(
        self,
        parent,
        downloader,
        config_manager,
        platform_manager,
        task_queue,
        animation_manager,
        toast_manager_getter: Callable[[], Any],
        queue_paused_getter: Callable[[], bool],
        show_queue_tab_callback: Callable[[], None],
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.downloader = downloader
        self.config_manager = config_manager
        self.platform_manager = platform_manager
        self.task_queue = task_queue
        self.animation_manager = animation_manager

        self.toast_manager_getter = toast_manager_getter
        self.queue_paused_getter = queue_paused_getter
        self.show_queue_tab_callback = show_queue_tab_callback

        # Video column playlist state
        self._video_playlist_entries: List[Dict[str, Any]] = []
        self._video_playlist_selection_vars: List[ctk.BooleanVar] = []
        self._video_playlist_source_url = ""
        self._video_playlist_detail_rows: List[Tuple[Any, Dict[str, Any]]] = []
        self._video_is_playlist_fetching = False
        
        # Music column playlist state
        self._music_playlist_entries: List[Dict[str, Any]] = []
        self._music_playlist_selection_vars: List[ctk.BooleanVar] = []
        self._music_playlist_source_url = ""
        self._music_playlist_detail_rows: List[Tuple[Any, Dict[str, Any]]] = []
        self._music_is_playlist_fetching = False
        
        # Active column pointers (will be set by _activate_video_side/_activate_music_side)
        self.playlist_entries: List[Dict[str, Any]] = []
        self.playlist_selection_vars: List[ctk.BooleanVar] = []
        self.playlist_source_url = ""
        self.playlist_detail_rows: List[Tuple[Any, Dict[str, Any]]] = []
        self.is_playlist_fetching = False
        self.is_info_fetching = False
        self.batch_mode_var = ctk.BooleanVar(value=False)

        self._spinner_animation_id: Optional[str] = None
        self._processing_after_id: Optional[str] = None
        self._processing_tick = 0
        self._processing_spinner_index = 0
        self._processing_text_base = ""
        self._download_progress_value = 0.0
        self._last_video_info: Optional[Dict[str, Any]] = None
        self._player_btn = None
        self._playlist_sort_dialog_enabled = True

        aria2c_path = self.config_manager.get("aria2c_path", "aria2c")
        self.torrent_downloader = TorrentDownloader(aria2c_path)
        self.setup_ui()

    def setup_ui(self):
        """Build tab widgets."""
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=10)

        title = ctk.CTkLabel(
            header_frame,
            text=f"{Icons.DOWNLOAD} {t('download.title')}",
            font=Fonts.H1,
        )
        title.pack(anchor="w", side="left")

        platform_frame = ctk.CTkFrame(self, fg_color="transparent")
        platform_frame.pack(fill="x", padx=15, pady=10)

        ctk.CTkLabel(platform_frame, text=t("download.platformLabel"), font=Fonts.LABEL).pack(side="left", padx=5)

        platforms = self.platform_manager.get_supported_platforms()
        platform_menu = ctk.CTkOptionMenu(
            platform_frame,
            values=platforms,
            command=self._on_platform_selected,
        )
        platform_menu.pack(side="left", padx=5)

        self.selected_platform_label = ctk.CTkLabel(
            platform_frame,
            text="URL",
            corner_radius=Sizes.CORNER_MD,
            fg_color=Colors.BTN_SECONDARY,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            width=120,
        )
        self.selected_platform_label.pack(side="left", padx=8)

        url_frame = ctk.CTkFrame(self, fg_color="transparent")
        url_frame.pack(fill="x", padx=15, pady=10)
        self._url_row_frame = url_frame

        ctk.CTkLabel(url_frame, text=f"{Icons.LINK_INPUT} {t('download.urlLabel')}", font=Fonts.LABEL).pack(side="left", padx=5)

        batch_toggle = ctk.CTkCheckBox(
            url_frame,
            text=t("download.batchMode"),
            variable=self.batch_mode_var,
            command=self._toggle_batch_mode,
            font=Fonts.SMALL,
        )
        batch_toggle.pack(side="left", padx=10)

        self.url_input_row = UrlInputRow(url_frame)
        self.url_input_row.pack(side="left", fill="x", expand=True)
        self.url_entry = self.url_input_row.url_entry
        self.url_validation_icon = self.url_input_row.validation_icon
        self.size_estimate_label = self.url_input_row.size_estimate_label
        self.url_validation_icon.configure(text_color=Colors.TEXT_MUTED)
        self.size_estimate_label.configure(text_color=Colors.TEXT_MUTED)

        self.url_entry.bind("<KeyRelease>", self._on_url_changed)
        self.url_entry.bind(
            "<FocusIn>",
            lambda _e: self.animation_manager.animate_focus_ring(
                self.url_entry,
                focused=True,
                duration=Motion.MICRO,
                idle_color=Colors.BORDER,
                focus_color=Colors.FOCUS_RING,
            ),
        )
        self.url_entry.bind("<FocusOut>", self._on_url_focus_out)
        self.url_entry.configure(cursor=Cursors.TEXT)

        if _HAS_DND:
            try:
                self.url_entry.drop_target_register(DND_FILES)
                self.url_entry.dnd_bind("<<Drop>>", self._on_torrent_file_drop)
            except Exception:
                pass

        # Torrent mod seçici (sadece magnet/torrent URL'de görünür)
        self.torrent_mode_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(
            self.torrent_mode_frame,
            text=t("download.torrentModeLabel"),
            font=Fonts.LABEL,
        ).pack(side="left", padx=5)
        self.torrent_mode_selector = ctk.CTkSegmentedButton(
            self.torrent_mode_frame,
            values=[t("download.torrentModeFull"), t("download.torrentModeSequential"), t("download.torrentModeStream")],
        )
        self.torrent_mode_selector.set(t("download.torrentModeFull"))
        self.torrent_mode_selector.pack(side="left", padx=5)
        # Başlangıçta gizli — standard URL'de görünmez
        # torrent_mode_frame pack edilmez; _on_url_changed gösterir/gizler

        self.batch_url_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(
            self.batch_url_frame,
            text=t("download.batchHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=5, pady=2)

        self.batch_url_text = ctk.CTkTextbox(
            self.batch_url_frame,
            height=120,
            font=Fonts.MONO,
            wrap="none",
        )
        self.batch_url_text.pack(fill="x", padx=5)

        self.info_label = ctk.CTkLabel(
            self,
            text=self._build_default_info_text(platforms),
            text_color=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify="left",
        )
        self.info_label.pack(fill="x", padx=15, pady=(6, 4))

        # ── Two-column layout: Video | Music ─────────────────────────────
        self._columns_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._columns_frame.pack(fill="x", padx=15, pady=(0, 10))
        self._columns_frame.grid_columnconfigure(0, weight=1)
        self._columns_frame.grid_columnconfigure(1, weight=1)

        # ── Video column ──────────────────────────────────────────────────
        video_col = ctk.CTkFrame(
            self._columns_frame,
            fg_color=Colors.BG_SURFACE,
            corner_radius=8,
        )
        video_col.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        ctk.CTkLabel(
            video_col,
            text=f"▶  {t('download.modeVideo')}",
            font=Fonts.H2,
        ).pack(anchor="w", padx=12, pady=(10, 6))

        vq_frame = ctk.CTkFrame(video_col, fg_color="transparent")
        vq_frame.pack(fill="x", padx=8, pady=2)
        self.quality_label = ctk.CTkLabel(
            vq_frame,
            text=f"{Icons.QUALITY_SELECT} {t('download.qualityLabel')}",
            font=Fonts.LABEL,
        )
        self.quality_label.pack(side="left", padx=4)
        self.quality_menu = ctk.CTkOptionMenu(
            vq_frame,
            values=[t("download.qualityBest"), "1080p", "720p", "480p"],
            command=lambda _v: self._on_quality_changed(),
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.quality_menu.pack(side="left", padx=4, fill="x", expand=True)

        vf_frame = ctk.CTkFrame(video_col, fg_color="transparent")
        vf_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(
            vf_frame,
            text=f"{Icons.FORMAT_SELECT} {t('download.formatLabel')}",
            font=Fonts.LABEL,
        ).pack(side="left", padx=4)
        self.format_menu = ctk.CTkOptionMenu(
            vf_frame,
            values=_VIDEO_FORMATS,
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.format_menu.pack(side="left", padx=4, fill="x", expand=True)

        Tooltip(self.quality_menu, t("download.qualityTooltip"))
        Tooltip(self.format_menu, t("download.formatTooltip"))

        self._video_fetch_btn = ctk.CTkButton(
            video_col,
            text=f"{Icons.SEARCH} {t('download.fetchData')}",
            command=self._fetch_video_data,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            cursor=Cursors.POINTER,
        )
        self._video_fetch_btn.pack(padx=8, pady=(8, 4), fill="x")

        # Video playlist panel
        self._video_playlist_widgets = self._create_playlist_panel(video_col, self._download_video)
        self._video_playlist_widgets['frame'].pack(padx=8, pady=(4, 4), fill="both", expand=True)

        self._video_download_btn = ctk.CTkButton(
            video_col,
            text=f"{Icons.DOWNLOAD_BTN} {t('download.videoDownloadBtn')}",
            command=self._download_video,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            cursor=Cursors.POINTER,
        )
        self._video_download_btn.pack(padx=8, pady=(4, 4), fill="x")

        self._video_progress = ctk.CTkProgressBar(video_col)
        self._video_progress.configure(
            progress_color=Colors.ACCENT,
            fg_color=Colors.PROGRESS_BG,
        )
        self._video_progress.set(0)
        self._video_progress.pack(padx=8, pady=2, fill="x")
        self._video_progress.pack_forget()

        self._video_status_label = ctk.CTkLabel(
            video_col,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY,
        )
        self._video_status_label.pack(padx=8, pady=(2, 6))

        self._video_error_panel = ErrorPanel(
            video_col,
            animation_manager=self.animation_manager,
            on_retry=self._retry_last_action,
        )

        # ── Music column ──────────────────────────────────────────────────
        music_col = ctk.CTkFrame(
            self._columns_frame,
            fg_color=Colors.BG_SURFACE,
            corner_radius=8,
        )
        music_col.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        ctk.CTkLabel(
            music_col,
            text=f"♪  {t('download.modeAudio')}",
            font=Fonts.H2,
        ).pack(anchor="w", padx=12, pady=(10, 6))

        mf_frame = ctk.CTkFrame(music_col, fg_color="transparent")
        mf_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(
            mf_frame,
            text=f"{Icons.FORMAT_SELECT} {t('download.formatLabel')}",
            font=Fonts.LABEL,
        ).pack(side="left", padx=4)
        self.music_format_menu = ctk.CTkOptionMenu(
            mf_frame,
            values=_AUDIO_FORMATS,
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.music_format_menu.set("MP3")
        self.music_format_menu.pack(side="left", padx=4, fill="x", expand=True)

        mb_frame = ctk.CTkFrame(music_col, fg_color="transparent")
        mb_frame.pack(fill="x", padx=8, pady=2)
        ctk.CTkLabel(
            mb_frame,
            text=f"{Icons.QUALITY_SELECT} {t('download.bitrateLabel')}",
            font=Fonts.LABEL,
        ).pack(side="left", padx=4)
        self.music_bitrate_menu = ctk.CTkOptionMenu(
            mb_frame,
            values=[t("download.qualityBest"), "320k", "192k", "128k"],
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.music_bitrate_menu.pack(side="left", padx=4, fill="x", expand=True)

        self._music_fetch_btn = ctk.CTkButton(
            music_col,
            text=f"{Icons.SEARCH} {t('download.fetchData')}",
            command=self._fetch_music_data,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            cursor=Cursors.POINTER,
        )
        self._music_fetch_btn.pack(padx=8, pady=(8, 4), fill="x")

        # Music playlist panel
        self._music_playlist_widgets = self._create_playlist_panel(music_col, self._download_music)
        self._music_playlist_widgets['frame'].pack(padx=8, pady=(4, 4), fill="both", expand=True)

        self._music_download_btn = ctk.CTkButton(
            music_col,
            text=f"♪ {t('download.musicDownloadBtn')}",
            command=self._download_music,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            cursor=Cursors.POINTER,
        )
        self._music_download_btn.pack(padx=8, pady=(4, 4), fill="x")

        self._music_progress = ctk.CTkProgressBar(music_col)
        self._music_progress.configure(
            progress_color=Colors.ACCENT,
            fg_color=Colors.PROGRESS_BG,
        )
        self._music_progress.set(0)
        self._music_progress.pack(padx=8, pady=2, fill="x")
        self._music_progress.pack_forget()

        self._music_status_label = ctk.CTkLabel(
            music_col,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY,
        )
        self._music_status_label.pack(padx=8, pady=(2, 6))

        self._music_error_panel = ErrorPanel(
            music_col,
            animation_manager=self.animation_manager,
            on_retry=self._retry_last_action,
        )

        # Initialize active-side pointers to video (default)
        self._active_btn_restore_text = f"{Icons.DOWNLOAD_BTN} {t('download.videoDownloadBtn')}"
        self._activate_video_side()

        # Shared button bindings and tooltips
        for button in (self._video_fetch_btn, self._video_download_btn, 
                      self._music_fetch_btn, self._music_download_btn):
            button.bind("<ButtonPress-1>", lambda _e, btn=button: self._apply_button_press_state(btn))
            button.bind("<ButtonRelease-1>", lambda _e, btn=button: self._apply_button_release_state(btn))
            button.bind("<Enter>", lambda _e, btn=button: self._apply_button_hover_state(btn, is_hover=True))
            button.bind("<Leave>", lambda _e, btn=button: self._apply_button_hover_state(btn, is_hover=False))

        Tooltip(self._video_fetch_btn, t("download.fetchData"))
        Tooltip(self._video_download_btn, t("download.videoDownloadBtn"))
        Tooltip(self._music_fetch_btn, t("download.fetchData"))
        Tooltip(self._music_download_btn, t("download.musicDownloadBtn"))

        self.error_frame = self.error_panel

    def _activate_video_side(self) -> None:
        """Point shared mixin attributes to the video column widgets and sync state."""
        # Save current state back to appropriate column if any
        if hasattr(self, '_save_active_playlist_state'):
            self._save_active_playlist_state()

        if hasattr(self, '_video_download_btn'):
            self.download_btn = self._video_download_btn
        if hasattr(self, '_video_progress'):
            self.download_progress = self._video_progress
        if hasattr(self, '_video_status_label'):
            self.download_status_label = self._video_status_label
        if hasattr(self, '_video_error_panel'):
            self.error_panel = self._video_error_panel
            self.error_frame = self.error_panel
        self._active_btn_restore_text = f"{Icons.DOWNLOAD_BTN} {t('download.videoDownloadBtn')}"

        # Point playlist widgets to video column
        if hasattr(self, '_video_playlist_widgets'):
            self.playlist_frame = self._video_playlist_widgets['frame']
            self.playlist_list_frame = self._video_playlist_widgets['list_frame']
            self.playlist_summary_label = self._video_playlist_widgets['summary_label']
            self.playlist_select_all_btn = self._video_playlist_widgets['select_all_btn']
            self.playlist_clear_btn = self._video_playlist_widgets['clear_btn']
            self.playlist_approve_btn = self._video_playlist_widgets['approve_btn']

        # Load video column state
        self._active_column = 'video'
        if hasattr(self, '_video_playlist_entries'):
            self.playlist_entries = self._video_playlist_entries
        if hasattr(self, '_video_playlist_selection_vars'):
            self.playlist_selection_vars = self._video_playlist_selection_vars
        if hasattr(self, '_video_playlist_source_url'):
            self.playlist_source_url = self._video_playlist_source_url
        if hasattr(self, '_video_playlist_detail_rows'):
            self.playlist_detail_rows = self._video_playlist_detail_rows
        if hasattr(self, '_video_is_playlist_fetching'):
            self.is_playlist_fetching = self._video_is_playlist_fetching

    def _activate_music_side(self) -> None:
        """Point shared mixin attributes to the music column widgets and sync state."""
        # Save current state back to appropriate column if any
        if hasattr(self, '_save_active_playlist_state'):
            self._save_active_playlist_state()

        if hasattr(self, '_music_download_btn'):
            self.download_btn = self._music_download_btn
        if hasattr(self, '_music_progress'):
            self.download_progress = self._music_progress
        if hasattr(self, '_music_status_label'):
            self.download_status_label = self._music_status_label
        if hasattr(self, '_music_error_panel'):
            self.error_panel = self._music_error_panel
            self.error_frame = self.error_panel
        self._active_btn_restore_text = f"♪ {t('download.musicDownloadBtn')}"
        
        # Point playlist widgets to music column
        self.playlist_frame = self._music_playlist_widgets['frame']
        self.playlist_list_frame = self._music_playlist_widgets['list_frame']
        self.playlist_summary_label = self._music_playlist_widgets['summary_label']
        self.playlist_select_all_btn = self._music_playlist_widgets['select_all_btn']
        self.playlist_clear_btn = self._music_playlist_widgets['clear_btn']
        self.playlist_approve_btn = self._music_playlist_widgets['approve_btn']
        
        # Load music column state
        self._active_column = 'music'
        self.playlist_entries = self._music_playlist_entries
        self.playlist_selection_vars = self._music_playlist_selection_vars
        self.playlist_source_url = self._music_playlist_source_url
        self.playlist_detail_rows = self._music_playlist_detail_rows
        self.is_playlist_fetching = self._music_is_playlist_fetching
    
    def _save_active_playlist_state(self) -> None:
        """Save current playlist state back to the appropriate column."""
        if not hasattr(self, '_active_column'):
            self._active_column = 'video'  # Default
            return
            
        if self._active_column == 'video':
            self._video_playlist_entries = self.playlist_entries
            self._video_playlist_selection_vars = self.playlist_selection_vars
            self._video_playlist_source_url = self.playlist_source_url
            self._video_playlist_detail_rows = self.playlist_detail_rows
            self._video_is_playlist_fetching = self.is_playlist_fetching
        elif self._active_column == 'music':
            self._music_playlist_entries = self.playlist_entries
            self._music_playlist_selection_vars = self.playlist_selection_vars
            self._music_playlist_source_url = self.playlist_source_url
            self._music_playlist_detail_rows = self.playlist_detail_rows
            self._music_is_playlist_fetching = self.is_playlist_fetching

    def _download_music(self) -> None:
        """Start a music download from the music column."""
        if self.queue_paused_getter():
            self._activate_music_side()
            self._show_download_error(t("download.queuePaused"), "")
            return

        url = self.url_entry.get().strip()
        if not url:
            self._activate_music_side()
            self._show_download_error(t("download.urlRequired"), "")
            return

        self._activate_music_side()

        format_type = _FORMAT_MAP.get(self.music_format_menu.get(), DownloadFormat.MP3)
        bitrate_str = self.music_bitrate_menu.get()
        audio_bitrate = _AUDIO_BITRATE_MAP.get(bitrate_str, "0")
        quality = DownloadQuality.AUDIO_ONLY

        default_path = self.config_manager.get(
            "default_download_path",
            str(Path.home() / "Downloads" / "RAVN"),
        )
        output_dir = str(Path(default_path))
        self._start_single_download(url, output_dir, format_type, quality, audio_bitrate)

    # _on_mode_changed kept for backward compat with any external callers
    def _on_mode_changed(self, value: str) -> None:
        pass

    def _is_audio_mode(self) -> bool:
        return False

    def _on_ctrl_enter(self, event=None):
        """Handle Ctrl+Enter - trigger primary download action."""
        if not self.winfo_viewable():
            return
        self._download_video()

    def _on_escape(self, event=None):
        """Handle Escape - cancel fetching if in progress."""
        if not self.winfo_viewable():
            return
        # Download tab uses task queue; Escape clears any fetch spinners
        if self.is_playlist_fetching or self.is_info_fetching:
            self._stop_processing_feedback()
            self.is_playlist_fetching = False
            self.is_info_fetching = False

    def _on_ctrl_l(self, event=None):
        """Handle Ctrl+L - clear URL input."""
        if not self.winfo_viewable():
            return
        if self.batch_mode_var.get():
            self.batch_url_text.delete("1.0", "end")
        else:
            self.url_entry.delete(0, "end")
        return "break"

    def _build_default_info_text(self, platforms: List[str]) -> str:
        return (
            f"{t('download.defaultInfoFlow')}\n"
            + f"{t('download.supportedPlatforms')}: "
            + ", ".join(platforms)
        )

    def _on_platform_selected(self, platform: str):
        self.selected_platform_label.configure(
            text=platform.upper(),
            fg_color=Colors.BTN_SECONDARY,
        )

    def _toggle_batch_mode(self):
        if self.batch_mode_var.get():
            self.url_input_row.pack_forget()
            self.batch_url_frame.pack(fill="x", padx=15, pady=(0, 10), before=self.info_label)
            self._set_button_loading_state(self.fetch_data_btn, is_loading=True)
            self.info_label.configure(
                text=t("download.batchModeInfo")
            )
            return

        self.batch_url_frame.pack_forget()
        self.url_input_row.pack(side="left", fill="x", expand=True)
        self._set_button_loading_state(self.fetch_data_btn, is_loading=False)
        self.info_label.configure(
            text=self._build_default_info_text(self.platform_manager.get_supported_platforms())
        )

    def _on_url_changed(self, _event=None):
        url = self.url_entry.get().strip()
        self._set_url_validation_state("", Colors.TEXT_MUTED)
        badge = self.platform_manager.get_platform_badge(url)
        self.selected_platform_label.configure(
            text=f"{badge['icon']} {badge['label']}",
            fg_color=badge["color"],
        )

        playlist_entries = self.__dict__.get("playlist_entries", [])
        playlist_source_url = self.__dict__.get("playlist_source_url", "")
        if playlist_entries and playlist_source_url and playlist_source_url != url:
            self._clear_playlist_selection()

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            if self._looks_like_playlist_url(url):
                fetch_data_btn.configure(text=f"{Icons.SEARCH} {t('download.fetchPlaylistData')}")
            else:
                fetch_data_btn.configure(text=f"{Icons.SEARCH} {t('download.fetchVideoData')}")

        # Torrent mod seçiciyi göster/gizle
        protocol = self._detect_url_protocol(self.url_entry.get().strip())
        torrent_mode_frame = getattr(self, "torrent_mode_frame", None)
        if torrent_mode_frame is not None:
            if protocol in ("magnet", "torrent_file"):
                pack_kwargs = {"fill": "x", "padx": 15, "pady": (0, 5)}
                url_row_frame = getattr(self, "_url_row_frame", None)
                if url_row_frame is not None:
                    pack_kwargs["after"] = url_row_frame
                torrent_mode_frame.pack(**pack_kwargs)
            else:
                torrent_mode_frame.pack_forget()

    def _on_url_focus_out(self, _event=None):
        self.animation_manager.animate_focus_ring(
            self.url_entry,
            focused=False,
            duration=Motion.MICRO,
            idle_color=Colors.BORDER,
            focus_color=Colors.FOCUS_RING,
        )
        # Context-menu paste gibi key event üretmeyen durumlarda görünürlüğü senkronize et.
        self._on_url_changed()
        url = self.url_entry.get().strip()
        if not url:
            self._set_url_validation_state("", Colors.TEXT_MUTED)
            return
        protocol = self._detect_url_protocol(url)
        if protocol in ("magnet", "torrent_file") or self._validate_url(url):
            self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)
        else:
            self._set_url_validation_state(Icons.ERROR_INDICATOR, Colors.ERROR)

    @staticmethod
    def _detect_url_protocol(url: str) -> str:
        """Return 'magnet', 'torrent_file', or 'standard'."""
        normalized = (url or "").strip()
        if normalized.lower().startswith("magnet:?xt=urn:"):
            return "magnet"
        if normalized.lower().endswith(".torrent"):
            return "torrent_file"
        return "standard"

    @staticmethod
    def _validate_url(url: str) -> bool:
        if not url:
            return False
        lowered = url.lower()
        if not (lowered.startswith("http://") or lowered.startswith("https://")):
            return False
        known_domains = [
            "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
            "twitch.tv", "soundcloud.com", "facebook.com", "twitter.com",
            "tiktok.com", "instagram.com", "bilibili.com", "nicovideo.jp",
        ]
        return any(domain in lowered for domain in known_domains)

    @staticmethod
    def _looks_like_playlist_url(url: str) -> bool:
        lowered = url.lower()
        return (
            "list=" in lowered
            or "/playlist" in lowered
            or "/sets/" in lowered
            or "/collection/" in lowered
        )

    @staticmethod
    def _format_duration(seconds: Any) -> str:
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            return ""
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:d}:{sec:02d}"

    def _get_selected_quality_label(self) -> str:
        try:
            return str(self.quality_menu.get() or t("download.qualityBest"))
        except Exception:
            return t("download.qualityBest")

    @staticmethod
    def _format_size_from_mb(size_mb: float) -> str:
        if size_mb >= 1024:
            return f"{size_mb / 1024:.1f} GB"
        return f"{size_mb:.1f} MB"

    def _on_quality_changed(self):
        if not self.playlist_entries:
            self._update_size_estimate()
            return

        quality_label = self._get_selected_quality_label()
        for item_widget, entry in self.playlist_detail_rows:
            item_widget.set_detail_text(self._build_playlist_detail_text(entry, quality_label))

        self._update_playlist_summary()
        self._update_size_estimate()

    def _set_url_validation_state(self, icon_text: str, color):
        url_validation_icon = self.__dict__.get("url_validation_icon")
        resolved_color = color
        if isinstance(color, tuple):
            resolved_color = color[0] if ctk.get_appearance_mode().lower() == "light" else color[1]
        if url_validation_icon is not None:
            url_validation_icon.configure(text=icon_text, text_color=resolved_color)

    def _apply_button_hover_state(self, button, is_hover: bool):
        if button is None:
            return
        try:
            if not hasattr(button, "_ravn_hover_color"):
                button._ravn_hover_color = button.cget("hover_color")
            hover_color = Colors.HOVER_BEIGE if is_hover else button._ravn_hover_color
            button.configure(hover_color=hover_color)
        except Exception:
            return

    def _retry_last_action(self):
        if self.is_playlist_fetching or self.is_info_fetching:
            return

        if self.playlist_entries and self.playlist_source_url == self.url_entry.get().strip():
            self._download_video()
            return

        self._fetch_download_data()

    def _start_video_info_fetch(self, url: str):
        if self.is_info_fetching or self.is_playlist_fetching:
            return

        self.is_info_fetching = True
        self.error_panel.hide_error()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback(t("download.videoInfoLoading"))

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.fetchData')}...")
            self._set_button_loading_state(fetch_data_btn, is_loading=True)

        def run_info_fetch():
            info = self.downloader.extract_video_info(url)
            self.after(0, self._on_video_info_fetch_complete, info)

        threading.Thread(target=run_info_fetch, daemon=True).start()

    def _on_video_info_fetch_complete(self, info: Optional[Dict[str, Any]]):
        self.is_info_fetching = False
        self._stop_processing_feedback()
        self._hide_progress()

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            self._set_button_loading_state(fetch_data_btn, is_loading=False)
            fetch_data_btn.configure(text=f"{Icons.REFRESH} {t('download.refreshVideoData')}")

        if not info:
            self.download_status_label.configure(text="")
            self._show_download_error(
                t("download.videoInfoFailed"),
                "Video info not found",
            )
            return

        title = str(info.get("title") or t("common.unknown"))
        uploader = str(info.get("uploader") or t("common.unknown"))
        duration = self._format_duration(info.get("duration"))
        details = f"{title} • {uploader}"
        if duration:
            details = f"{details} • {duration}"
        self.download_status_label.configure(text=t("download.readyStatus", details=details))
        self._last_video_info = info
        self._update_size_estimate()
        self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)

    def _fetch_video_data(self):
        """Fetch playlist/video info from the video column."""
        self._activate_video_side()
        self._fetch_download_data()

    def _fetch_music_data(self):
        """Fetch playlist/video info from the music column."""
        self._activate_music_side()
        self._fetch_download_data()

    def _fetch_download_data(self):
        url = self.url_entry.get().strip()
        if not url:
            self._show_download_error(t("download.urlRequired"), "")
            return

        if self._looks_like_playlist_url(url):
            if not self.is_playlist_fetching:
                self._start_playlist_fetch(url)
            return

        if not self.is_info_fetching:
            self._start_video_info_fetch(url)

    def _start_single_download(
        self,
        url: str,
        output_dir: str,
        format_type: DownloadFormat,
        quality: DownloadQuality,
        audio_bitrate: Optional[str] = None,
    ):
        self.error_panel.hide_error()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback(t("download.downloadLoading"))
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.downloadLoading')}...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        embed_metadata = bool(self.config_manager.get("auto_id3_tagging", self.config_manager.get("embed_metadata", True)))
        embed_lyrics = bool(self.config_manager.get("auto_embed_lyrics", True))
        auto_sort_enabled = bool(self.config_manager.get("auto_sort_downloads", self.config_manager.get("auto_sort_by_channel", False)))
        auto_sort_mode = str(self.config_manager.get("auto_sort_mode", "artist") or "artist").lower()

        def run_download():
            try:
                result = self.downloader.download(
                    url=url,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    progress_callback=self._on_download_progress,
                    embed_metadata=embed_metadata,
                    embed_lyrics=embed_lyrics,
                    auto_sort_enabled=auto_sort_enabled,
                    auto_sort_mode=auto_sort_mode,
                    audio_bitrate=audio_bitrate,
                )
                if result.success:
                    self.after(0, self._on_download_success, result)
                else:
                    self.after(0, self._on_download_failure, result.error_message)
            except Exception as exc:
                self.after(0, self._on_download_failure, str(exc))

        threading.Thread(target=run_download, daemon=True).start()

    def _download_video(self):
        self._activate_video_side()
        if self.queue_paused_getter():
            self._show_download_error(t("download.queuePaused"), "")
            return

        batch_mode = False
        try:
            batch_mode = bool(self.batch_mode_var.get())
        except Exception:
            batch_mode = False

        if batch_mode:
            self._download_batch()
            return

        url = self.url_entry.get().strip()
        if not url:
            self._show_download_error(t("download.urlRequired"), "")
            return

        quality_str = self.quality_menu.get()
        quality = _QUALITY_MAP.get(quality_str, DownloadQuality.BEST)
        format_type = _FORMAT_MAP.get(self.format_menu.get(), DownloadFormat.MP4)
        audio_bitrate = None

        default_path = self.config_manager.get(
            "default_download_path",
            str(Path.home() / "Downloads" / "RAVN"),
        )
        output_dir = str(Path(default_path))

        if self._looks_like_playlist_url(url):
            if self.is_playlist_fetching:
                return

            if self.playlist_source_url != url or not self.playlist_entries:
                self._show_download_error(t("download.playlistFetchFirst"), "")
                return

            selected_entries = self._get_selected_playlist_entries()
            if not selected_entries:
                self._show_download_error(t("download.playlistSelectAtLeastOne"), "")
                return

            self._start_playlist_download(selected_entries, output_dir, format_type, quality)
            return

        protocol = self._detect_url_protocol(url)
        if protocol in ("magnet", "torrent_file"):
            self._start_torrent_download(url, output_dir)
            return

        self._start_single_download(url, output_dir, format_type, quality, audio_bitrate)

    def _start_torrent_download(self, source: str, output_dir: str):
        """Start a torrent/magnet download via TorrentDownloader."""
        if not self.torrent_downloader.is_available():
            toast = self.toast_manager_getter()
            if toast:
                toast.show(t("download.torrentMissing"), level="warning")
            return

        _mode_map = {
            t("download.torrentModeFull"): TorrentDownloadMode.FULL,
            t("download.torrentModeSequential"): TorrentDownloadMode.SEQUENTIAL,
            t("download.torrentModeStream"): TorrentDownloadMode.STREAM,
        }
        selected_mode = getattr(self, "torrent_mode_selector", None)
        mode = _mode_map.get(
            selected_mode.get() if selected_mode else t("download.torrentModeFull"),
            TorrentDownloadMode.FULL,
        )

        self._start_processing_feedback(t("download.torrentLoading"))
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.downloadLoading')}...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        def run_torrent():
            try:
                def progress_cb(percent: int, msg: str):
                    self.after(0, self._on_download_progress, percent, msg)

                result = self.torrent_downloader.download(
                    source=source,
                    output_dir=output_dir,
                    mode=mode,
                    progress_callback=progress_cb,
                )
                if result.success:
                    self.after(0, self._on_torrent_success, result, output_dir)
                else:
                    self.after(0, self._on_download_failure, result.error_message)
            except Exception as exc:
                self.after(0, self._on_download_failure, str(exc))

        threading.Thread(target=run_torrent, daemon=True).start()

    def _on_download_success_simple(self, output_dir: str):
        """Handle torrent download success (legacy, kept for compatibility)."""
        self._stop_processing_feedback()
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=self._active_btn_restore_text)
        toast = self.toast_manager_getter()
        if toast:
            toast.show(t("download.torrentDownloaded", outputDir=output_dir), level="success")

    def _on_torrent_success(self, result, output_dir: str):
        """Handle torrent download success with optional stream URL."""
        self._stop_processing_feedback()
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=self._active_btn_restore_text)

        toast = self.toast_manager_getter()
        if toast:
            toast.show(t("download.torrentDownloaded", outputDir=output_dir), level="success")

        if result.stream_url:
            self._show_open_player_button(result.stream_url)

    def _show_open_player_button(self, url: str):
        """Show an 'Open in Player' button for stream URL."""
        if not hasattr(self, "_player_btn") or self._player_btn is None:
            self._player_btn = ctk.CTkButton(
                self,
                text=f"{Icons.PLAY if hasattr(Icons, 'PLAY') else '▶'} {t('download.openInPlayer')}",
                command=lambda: self._open_with_player(url),
                font=Fonts.LABEL,
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_HOVER,
            )
        else:
            self._player_btn.configure(command=lambda: self._open_with_player(url))
        self._player_btn.pack(padx=15, pady=5, anchor="w")

    def _open_with_player(self, url: str):
        """Open URL or file path with the system default player."""
        import os
        import subprocess
        try:
            if os.name == "nt":
                os.startfile(url)
            else:
                subprocess.Popen(["xdg-open", url])
        except Exception:
            pass

    def _on_torrent_file_drop(self, event):
        """Handle a .torrent file dropped onto the URL entry."""
        try:
            raw = event.data.strip()
            if raw.startswith("{") and raw.endswith("}"):
                raw = raw[1:-1]
            file_path = raw.strip()
            if not file_path.lower().endswith(".torrent"):
                toast = self.toast_manager_getter()
                if toast:
                    toast.show(t("download.torrentFileOnly"), level="warning")
                return
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, file_path)
            self._on_url_changed()
        except Exception:
            pass

    def _download_batch(self):
        batch_text = self.batch_url_text.get("1.0", "end").strip()
        if not batch_text:
            self._show_download_error(t("download.urlRequired"), "")
            return

        urls = [line.strip() for line in batch_text.split("\n") if line.strip()]
        if not urls:
            self._show_download_error(t("download.invalidUrls"), "")
            return

        if len(urls) > 50:
            self._show_download_error(t("download.tooManyUrls"), "")
            urls = urls[:50]

        quality = _QUALITY_MAP.get(self.quality_menu.get(), DownloadQuality.BEST)
        format_type = _FORMAT_MAP.get(self.format_menu.get(), DownloadFormat.MP4)
        embed_metadata = bool(self.config_manager.get("auto_id3_tagging", self.config_manager.get("embed_metadata", True)))
        embed_lyrics = bool(self.config_manager.get("auto_embed_lyrics", True))
        auto_sort_enabled = bool(self.config_manager.get("auto_sort_downloads", self.config_manager.get("auto_sort_by_channel", False)))
        auto_sort_mode = str(self.config_manager.get("auto_sort_mode", "artist") or "artist").lower()

        default_path = self.config_manager.get(
            "default_download_path",
            str(Path.home() / "Downloads" / "RAVN"),
        )
        output_dir = str(Path(default_path))

        self.download_status_label.configure(text=t("download.queuedAddProgress", count=len(urls)))
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.queuedAddLoading')}")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        for index, url in enumerate(urls, start=1):
            task_name = t("download.batchTaskName", index=index, total=len(urls))
            self.task_queue.add_task(
                task_type=TaskType.DOWNLOAD,
                name=task_name,
                execute_fn=lambda u=url: self.downloader.download(
                    url=u,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    embed_metadata=embed_metadata,
                    embed_lyrics=embed_lyrics,
                    auto_sort_enabled=auto_sort_enabled,
                    auto_sort_mode=auto_sort_mode,
                ),
            )

        self.download_status_label.configure(
            text=t("download.queuedAddStatus", count=len(urls))
        )
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
        self.show_queue_tab_callback()

    def _update_size_estimate(self):
        if not self._last_video_info:
            self.size_estimate_label.configure(text="")
            return

        quality_label = self._get_selected_quality_label()
        size_by_quality = self._last_video_info.get("size_by_quality_mb") or {}
        size_mb = float(size_by_quality.get(quality_label, 0) or 0)
        if size_mb <= 0:
            size_mb = float(size_by_quality.get(t("download.qualityBest"), 0) or 0)
        if size_mb <= 0:
            size_mb = float(size_by_quality.get("En Iyi", 0) or 0)
        if size_mb <= 0:
            size_mb = float(size_by_quality.get("En İyi", 0) or 0)
        if size_mb <= 0:
            size_mb = float(size_by_quality.get("Best", 0) or 0)
        if size_mb <= 0:
            filesize = self._last_video_info.get("filesize") or self._last_video_info.get("filesize_approx") or 0
            size_mb = float(filesize) / (1024 * 1024) if filesize else 0

        if size_mb > 0:
            self.size_estimate_label.configure(
                text=f"~{self._format_size_from_mb(size_mb)}",
                text_color=Colors.TEXT_MUTED,
            )
            return

        self.size_estimate_label.configure(text="")

    def set_status_text(self, text: str):
        """Public bridge for main window level status updates."""
        self.download_status_label.configure(text=text)

    def _create_playlist_panel(self, parent, download_command):
        """Create a playlist panel for a column.
        
        Args:
            parent: Parent frame (video_col or music_col)
            download_command: Command for approve button (_download_video or _download_music)
            
        Returns:
            Dictionary with playlist widgets: {
                'frame', 'summary_label', 'list_frame', 
                'select_all_btn', 'clear_btn', 'approve_btn'
            }
        """
        playlist_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_CARD, corner_radius=6)
        
        ctk.CTkLabel(
            playlist_frame,
            text=f"{Icons.QUEUE} {t('download.playlistTitle')}",
            font=Fonts.LABEL_BOLD,
        ).pack(anchor="w", padx=8, pady=(8, 4))
        
        summary_label = ctk.CTkLabel(
            playlist_frame,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        )
        summary_label.pack(anchor="w", padx=8, pady=(0, 4))
        
        controls_row = ctk.CTkFrame(playlist_frame, fg_color="transparent")
        controls_row.pack(fill="x", padx=8, pady=(0, 4))
        
        select_all_btn = ctk.CTkButton(
            controls_row,
            text=f"{Icons.CHECK} {t('download.playlistSelectAll')}",
            width=100,
            height=28,
            command=self._select_all_playlist_items,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL,
        )
        select_all_btn.pack(side="left")
        
        clear_btn = ctk.CTkButton(
            controls_row,
            text=f"{Icons.CLEAR_BTN} {t('download.playlistClear')}",
            width=100,
            height=28,
            command=self._clear_all_playlist_items,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL,
        )
        clear_btn.pack(side="left", padx=(6, 0))
        
        approve_btn = ctk.CTkButton(
            controls_row,
            text=f"{Icons.DOWNLOAD_BTN} {t('download.playlistApprove')}",
            width=150,
            height=28,
            command=download_command,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
        )
        approve_btn.pack(side="right", padx=(6, 0))
        
        list_frame = ctk.CTkScrollableFrame(
            playlist_frame,
            height=300,
            fg_color=Colors.BG_SURFACE,
        )
        list_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        
        # Start hidden
        playlist_frame.pack_forget()
        
        return {
            'frame': playlist_frame,
            'summary_label': summary_label,
            'list_frame': list_frame,
            'select_all_btn': select_all_btn,
            'clear_btn': clear_btn,
            'approve_btn': approve_btn,
        }
