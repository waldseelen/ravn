"""
Ana uygulama penceresi - CustomTkinter arayüzü (Sekmeli)
"""

import threading
import customtkinter as ctk
from customtkinter import filedialog
from PIL import Image
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ravn_app.ui.converter_tab import ConverterTab
from ravn_app.ui.subtitle_tab import SubtitleTab
from ravn_app.ui.history_settings_tab import HistoryTab, SettingsTab
from ravn_app.ui.queue_panel import QueuePanel
from ravn_app.ui.ui_components import ToastManager, Tooltip
from ravn_app.core.database import DatabaseManager, ConfigManager
from ravn_app.core.platform_support import PlatformManager
from ravn_app.core.downloader import YouTubeDownloader, DownloadFormat, DownloadQuality
from ravn_app.core.task_manager import TaskType, get_task_queue
from ravn_app.core.error_handler import YtDlpErrorParser, format_error_for_user
from ravn_app.core.animation_manager import get_animation_manager
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Motion, Spacing, Sizes
from ravn_app.ui.design_tokens import Icons
from ravn_app.ui.advanced_features import NotificationManager, SystemTrayIntegration


# Map UI dropdown labels to enum values
_QUALITY_MAP = {
    "En İyi": DownloadQuality.BEST,
    "1080p": DownloadQuality.HIGH_1080P,
    "720p": DownloadQuality.MEDIUM_720P,
    "480p": DownloadQuality.LOW_480P,
    "Sadece Ses": DownloadQuality.AUDIO_ONLY,
}

_FORMAT_MAP = {
    "MP4": DownloadFormat.MP4,
    "WebM": DownloadFormat.WEBM,
    "MKV": DownloadFormat.MKV,
    "MP3": DownloadFormat.MP3,
    "M4A": DownloadFormat.M4A,
}


class YouTubeDownloaderApp(ctk.CTk):
    """Ana uygulama penceresi - Sekmeli arayüz"""

    def __init__(self):
        super().__init__()

        # Tema ve pencere ayarları
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("RAVN - Media Manager")
        self.geometry("1400x900")  # Daha geniş ve yüksek pencere
        self.minsize(1200, 800)  # Minimum boyut da artırıldı

        # Database ve Config yönetimi (Faz 4) - uses OS-specific paths
        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.platform_manager = PlatformManager()  # Platform desteği

        # Downloader ve task manager
        self.downloader = YouTubeDownloader()
        self.task_queue = get_task_queue()
        self.queue_paused = False
        self.playlist_entries: List[Dict[str, Any]] = []
        self.playlist_selection_vars: List[ctk.BooleanVar] = []
        self.playlist_source_url = ""
        self.playlist_detail_rows: List[Tuple[Any, Dict[str, Any]]] = []
        self.is_playlist_fetching = False
        self.is_info_fetching = False
        self.batch_mode_var = ctk.BooleanVar(value=False)  # Batch download mode
        self.animation_manager = get_animation_manager()
        self._spinner_animation_id: Optional[str] = None
        self._processing_after_id: Optional[str] = None
        self._processing_tick = 0
        self._processing_spinner_index = 0
        self._processing_text_base = ""
        self._download_progress_value = 0.0

        # Toast notification manager (POL-20, POL-21)
        self.toast_manager: Optional[ToastManager] = None

        # Tema yönetimi
        self.current_theme = self.config_manager.get('theme', 'nordic')
        self.tray = None
        self._setup_ui()
        # Initialize toast manager after UI setup
        self.toast_manager = ToastManager(self)
        self._setup_tray_integration()
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def __del__(self):
        """Uygulama kapanırken veritabanını kapat"""
        db_manager = self.__dict__.get("db_manager")
        if db_manager:
            db_manager.close()

    def _setup_ui(self):
        """UI bileşenlerini kur"""
        # Üst başlık
        header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        header_frame.pack(fill="x", padx=0, pady=0)

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(pady=(12, 10))

        title = ctk.CTkLabel(
            header_inner,
            text="RAVN  —  Media Manager",
            font=Fonts.TITLE
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            header_inner,
            text="Media downloader & converter",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        subtitle.pack()

        # Sekmeli arayüz
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview.configure(
            segmented_button_fg_color=Colors.BG_SURFACE,
            segmented_button_selected_color=Colors.ACCENT,
            segmented_button_selected_hover_color=Colors.ACCENT_HOVER,
            segmented_button_unselected_color=Colors.BG_CARD,
            segmented_button_unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
        )

        # Sekme: İndir (Faz 1)
        download_tab = self.tabview.add(f"{Icons.DOWNLOAD}  İndir")
        self._setup_download_tab(download_tab)

        # Sekme: Dönüştür (Faz 2)
        converter_tab = self.tabview.add(f"{Icons.CONVERT}  Dönüştür")
        self._setup_converter_tab(converter_tab)

        # Sekme: Altyazı (Faz 3)
        subtitle_tab = self.tabview.add(f"{Icons.SUBTITLE}  Altyazı")
        self._setup_subtitle_tab(subtitle_tab)

        # Sekme: Kuyruk (Faz 4 - YENİ)
        queue_tab = self.tabview.add(f"{Icons.QUEUE}  Kuyruk")
        self._setup_queue_tab(queue_tab)

        # Sekme: Geçmiş (Faz 4)
        history_tab = self.tabview.add(f"{Icons.HISTORY}  Geçmiş")
        self._setup_history_tab(history_tab)

        # Sekme: Ayarlar (Faz 4 & 5)
        settings_tab = self.tabview.add(f"{Icons.SETTINGS}  Ayarlar")
        self._setup_settings_tab_full(settings_tab)
        self._setup_tab_switch_transition()

        # Alt durum çubuğu
        footer_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        footer_frame.pack(fill="x", padx=0, pady=0)

        status = ctk.CTkLabel(
            footer_frame,
            text="RAVN v1.0.0  •  Hazır",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        status.pack(pady=5)

    def _setup_download_tab(self, tab):
        """İndirme sekmesini kur - Platform desteğiyle"""
        # Başlık
        header_frame = ctk.CTkFrame(tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=10)

        title = ctk.CTkLabel(
            header_frame,
            text=f"{Icons.DOWNLOAD} Video İndir",
            font=Fonts.H1
        )
        title.pack(anchor="w")

        # Platform seçimi
        platform_frame = ctk.CTkFrame(tab, fg_color="transparent")
        platform_frame.pack(fill="x", padx=15, pady=10)

        platform_label = ctk.CTkLabel(
            platform_frame,
            text="Platform:",
            font=Fonts.LABEL
        )
        platform_label.pack(side="left", padx=5)

        platforms = self.platform_manager.get_supported_platforms()
        platform_menu = ctk.CTkOptionMenu(
            platform_frame,
            values=platforms,
            command=lambda x: self._on_platform_selected(x)
        )
        platform_menu.pack(side="left", padx=5)
        self.selected_platform_label = ctk.CTkLabel(
            platform_frame,
            text="",
            corner_radius=Sizes.CORNER_MD,
            fg_color=Colors.BTN_SECONDARY,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            width=120
        )
        self.selected_platform_label.pack(side="left", padx=8)
        self.selected_platform_label.configure(text="URL")

        # URL giriş alanı (tek veya çoklu)
        url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        url_frame.pack(fill="x", padx=15, pady=10)

        url_label = ctk.CTkLabel(
            url_frame,
            text=f"{Icons.LINK_INPUT} URL:",
            font=Fonts.LABEL
        )
        url_label.pack(side="left", padx=5)

        # Batch mode toggle (use existing variable or create if not exists)
        if not hasattr(self, 'batch_mode_var'):
            self.batch_mode_var = ctk.BooleanVar(value=False)

        batch_toggle = ctk.CTkCheckBox(
            url_frame,
            text="Toplu İndirme",
            variable=self.batch_mode_var,
            command=self._toggle_batch_mode,
            font=Fonts.SMALL
        )
        batch_toggle.pack(side="left", padx=10)

        # Single URL entry (default)
        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="Video URL'sini gir...",
            width=400,
            corner_radius=Sizes.CORNER_SM,  # POL-22
        )
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.url_entry.bind("<KeyRelease>", self._on_url_changed)
        self.url_entry.bind("<FocusIn>", lambda _e: self.animation_manager.animate_focus_ring(
            self.url_entry,
            focused=True,
            duration=Motion.MICRO,
            idle_color=Colors.BORDER,
            focus_color=Colors.FOCUS_RING,
        ))
        self.url_entry.bind("<FocusOut>", self._on_url_focus_out)
        # POL-27: Text cursor for input
        self.url_entry.configure(cursor=Cursors.TEXT)

        self.url_validation_icon = ctk.CTkLabel(
            url_frame,
            text="",
            width=26,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
        )
        self.url_validation_icon.pack(side="left", padx=(2, 4))

        # Batch URL text area (hidden by default)
        self.batch_url_frame = ctk.CTkFrame(tab, fg_color="transparent")
        batch_info = ctk.CTkLabel(
            self.batch_url_frame,
            text="Her satıra bir URL yazın (maks. 50)",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        batch_info.pack(anchor="w", padx=5, pady=2)

        self.batch_url_text = ctk.CTkTextbox(
            self.batch_url_frame,
            height=120,
            font=Fonts.MONO,
            wrap="none"
        )
        self.batch_url_text.pack(fill="x", padx=5)
        # Initially hidden

        # Kalite ve format seçenekleri
        options_frame = ctk.CTkFrame(tab, fg_color="transparent")
        options_frame.pack(fill="x", padx=15, pady=5)

        quality_label = ctk.CTkLabel(
            options_frame,
            text=f"{Icons.QUALITY_SELECT} Kalite:",
            font=Fonts.LABEL
        )
        quality_label.pack(side="left", padx=5)

        self.quality_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["En İyi", "1080p", "720p", "480p", "Sadece Ses"],
            command=lambda _value: self._on_quality_changed(),
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.quality_menu.pack(side="left", padx=5)

        format_label = ctk.CTkLabel(
            options_frame,
            text=f"{Icons.FORMAT_SELECT} Format:",
            font=Fonts.LABEL
        )
        format_label.pack(side="left", padx=15)

        self.format_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["MP4", "WebM", "MKV", "MP3", "M4A"],
            fg_color=Colors.BG_INPUT,
            button_color=Colors.ACCENT,
            button_hover_color=Colors.ACCENT_HOVER,
            dropdown_fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            dropdown_text_color=Colors.TEXT_PRIMARY,
        )
        self.format_menu.pack(side="left", padx=5)

        # Bilgi etiketi
        self.info_label = ctk.CTkLabel(
            tab,
            text=(
                "Akış: URL gir  →  Verileri Getir  →  (playlist ise seçim yap)  →  İndir\n"
                + "Desteklenen platformlar: "
                + ", ".join(platforms)
            ),
            text_color=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            justify="left"
        )
        self.info_label.pack(fill="x", padx=15, pady=(6, 10))

        # Playlist seçim alanı (yalnızca playlist linklerinde görünür)
        self.playlist_frame = ctk.CTkFrame(tab, fg_color=Colors.BG_SURFACE)

        playlist_title = ctk.CTkLabel(
            self.playlist_frame,
            text=f"{Icons.QUEUE} Playlist içeriği",
            font=Fonts.LABEL_BOLD
        )
        playlist_title.pack(anchor="w", padx=10, pady=(10, 4))

        self.playlist_summary_label = ctk.CTkLabel(
            self.playlist_frame,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self.playlist_summary_label.pack(anchor="w", padx=10, pady=(0, 6))

        controls_row = ctk.CTkFrame(self.playlist_frame, fg_color="transparent")
        controls_row.pack(fill="x", padx=10, pady=(0, 6))

        self.playlist_select_all_btn = ctk.CTkButton(
            controls_row,
            text=f"{Icons.CHECK} Tümünü Seç",
            width=120,
            height=30,
            command=self._select_all_playlist_items,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL
        )
        self.playlist_select_all_btn.pack(side="left")

        self.playlist_clear_btn = ctk.CTkButton(
            controls_row,
            text=f"{Icons.CLEAR_BTN} Seçimi Temizle",
            width=120,
            height=30,
            command=self._clear_all_playlist_items,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL
        )
        self.playlist_clear_btn.pack(side="left", padx=(8, 0))

        self.playlist_list_frame = ctk.CTkScrollableFrame(
            self.playlist_frame,
            height=500,
            fg_color=Colors.BG_CARD
        )
        self.playlist_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.playlist_frame.pack_forget()

        # Veri çekme butonu (playlist/video metadata için)
        self.fetch_data_btn = ctk.CTkButton(
            tab,
            text=f"{Icons.SEARCH} Verileri Getir",
            command=self._fetch_download_data,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER
        )
        self.fetch_data_btn.pack(padx=15, pady=(0, 8), fill="x")

        # İndir butonu
        self.download_btn = ctk.CTkButton(
            tab,
            text=f"{Icons.DOWNLOAD_BTN} İndir",
            command=self._download_video,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER
        )
        self.download_btn.pack(padx=15, pady=(0, 10), fill="x")

        # İlerleme çubuğu
        self.download_progress = ctk.CTkProgressBar(tab)
        self.download_progress.configure(
            progress_color=Colors.PROGRESS_FILL,
            fg_color=Colors.PROGRESS_BG,
        )
        self.download_progress.set(0)
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self.download_progress.pack_forget()  # Başlangıçta gizli

        # Durum etiketi
        self.download_status_label = ctk.CTkLabel(
            tab,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY
        )
        self.download_status_label.pack(pady=5)

        for button in (self.fetch_data_btn, self.download_btn):
            button.bind("<ButtonPress-1>", lambda _e, btn=button: self._apply_button_press_state(btn))
            button.bind("<ButtonRelease-1>", lambda _e, btn=button: self._apply_button_release_state(btn))
            button.bind("<Enter>", lambda _e, btn=button: self._apply_button_hover_state(btn, is_hover=True))
            button.bind("<Leave>", lambda _e, btn=button: self._apply_button_hover_state(btn, is_hover=False))
            # POL-27: Cursor feedback
            button.configure(cursor=Cursors.POINTER)

        # POL-34: Tooltips for main action buttons
        Tooltip(self.fetch_data_btn, "URL'den video/playlist bilgilerini çek")
        Tooltip(self.download_btn, "Seçilen videoyu/playlist'i indir")

        # Hata çerçevesi
        self.error_frame = ctk.CTkFrame(
            tab,
            fg_color=Colors.ERROR_BG,
            border_width=1,
            border_color=Colors.BORDER,
        )
        # Başlangıçta gizli; hata oluştuğunda pack edilecek

        error_top_row = ctk.CTkFrame(self.error_frame, fg_color="transparent")
        error_top_row.pack(fill="x", padx=10, pady=5)

        self.error_message_label = ctk.CTkLabel(
            error_top_row,
            text="",
            text_color=Colors.ERROR,
            font=Fonts.LABEL,
            wraplength=700,
            justify="left"
        )
        self.error_message_label.pack(side="left", fill="x", expand=True)

        self.toggle_details_btn = ctk.CTkButton(
            error_top_row,
            text=f"{Icons.INFO} Teknik Detaylar",
            command=self._toggle_error_details,
            width=130,
            height=28,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL
        )
        self.toggle_details_btn.pack(side="right", padx=5)

        self.retry_btn = ctk.CTkButton(
            error_top_row,
            text=f"{Icons.RETRY} Tekrar Dene",
            command=self._retry_last_action,
            width=120,
            height=28,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL,
        )
        self.retry_btn.pack(side="right", padx=5)

        self.raw_error_textbox = ctk.CTkTextbox(
            self.error_frame,
            height=100,
            font=Fonts.MONO,
            text_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.BG_PRIMARY
        )
        # Başlangıçta gizli
        self._raw_error_visible = False

    def _on_platform_selected(self, platform: str):
        """Platform seçildiğinde çağrılır"""
        self.selected_platform_label.configure(
            text=platform.upper(),
            fg_color=Colors.BTN_SECONDARY
        )

    def _toggle_batch_mode(self):
        """Toggle between single and batch URL input"""
        if self.batch_mode_var.get():
            # Switch to batch mode
            self.url_entry.pack_forget()
            self.batch_url_frame.pack(fill="x", padx=15, pady=(0, 10), before=self.info_label)
            self._set_button_loading_state(self.fetch_data_btn, is_loading=True)
            self.info_label.configure(
                text="Toplu indirme modunda her satıra bir URL yazın. Verileri Getir butonu devre dışı."
            )
        else:
            # Switch to single mode
            self.batch_url_frame.pack_forget()
            self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
            self._set_button_loading_state(self.fetch_data_btn, is_loading=False)
            platforms = self.platform_manager.get_supported_platforms()
            self.info_label.configure(
                text=(
                    "Akış: URL gir  →  Verileri Getir  →  (playlist ise seçim yap)  →  İndir\n"
                    + "Desteklenen platformlar: "
                    + ", ".join(platforms)
                )
            )

    def _on_url_changed(self, _event=None):
        """URL değiştiğinde platform badge bilgisini güncelle."""
        url = self.url_entry.get().strip()
        self._set_url_validation_state("", Colors.TEXT_MUTED)
        badge = self.platform_manager.get_platform_badge(url)
        self.selected_platform_label.configure(
            text=f"{badge['icon']} {badge['label']}",
            fg_color=badge["color"]
        )
        playlist_entries = self.__dict__.get("playlist_entries", [])
        playlist_source = self.__dict__.get("playlist_source_url", "")
        if playlist_entries and playlist_source and playlist_source != url:
            self._clear_playlist_selection()

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            if self._looks_like_playlist_url(url):
                fetch_data_btn.configure(text=f"{Icons.SEARCH} Playlist Verilerini Getir")
            else:
                fetch_data_btn.configure(text=f"{Icons.SEARCH} Video Bilgilerini Getir")

    def _on_url_focus_out(self, _event=None):
        """POL-17: Validate URL on blur."""
        # Animate focus ring off
        self.animation_manager.animate_focus_ring(
            self.url_entry,
            focused=False,
            duration=Motion.MICRO,
            idle_color=Colors.BORDER,
            focus_color=Colors.FOCUS_RING,
        )
        # Validate URL
        url = self.url_entry.get().strip()
        if not url:
            self._set_url_validation_state("", Colors.TEXT_MUTED)
            return

        # Check if URL looks valid
        if self._validate_url(url):
            self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)
        else:
            self._set_url_validation_state(Icons.ERROR_INDICATOR, Colors.ERROR)

    @staticmethod
    def _validate_url(url: str) -> bool:
        """POL-17: Basic URL validation."""
        if not url:
            return False
        # Check for basic URL structure
        url_lower = url.lower()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            return False
        # Check for known video platforms
        known_domains = [
            "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
            "twitch.tv", "soundcloud.com", "facebook.com", "twitter.com",
            "tiktok.com", "instagram.com", "bilibili.com", "nicovideo.jp",
        ]
        return any(domain in url_lower for domain in known_domains)

    @staticmethod
    def _looks_like_playlist_url(url: str) -> bool:
        """URL'nin playlist linki olma olasılığını kontrol et."""
        lowered = url.lower()
        return (
            "list=" in lowered
            or "/playlist" in lowered
            or "/sets/" in lowered
            or "/collection/" in lowered
        )

    @staticmethod
    def _format_duration(seconds: Any) -> str:
        """Saniyeyi okunabilir süre metnine çevir."""
        if not isinstance(seconds, (int, float)) or seconds <= 0:
            return ""
        seconds = int(seconds)
        minutes, sec = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:d}:{minutes:02d}:{sec:02d}"
        return f"{minutes:d}:{sec:02d}"

    def _get_selected_quality_label(self) -> str:
        """Read selected quality label safely for both UI and tests."""
        quality_menu = self.__dict__.get("quality_menu")
        if quality_menu is None:
            return "En İyi"
        try:
            return str(quality_menu.get() or "En İyi")
        except Exception:
            return "En İyi"

    @staticmethod
    def _format_size_from_mb(size_mb: float) -> str:
        """Format MB values as MB/GB text."""
        if size_mb >= 1024:
            return f"{size_mb / 1024:.1f} GB"
        return f"{size_mb:.1f} MB"

    def _get_playlist_entry_quality_metrics(self, entry: Dict[str, Any], quality_label: str) -> Dict[str, Any]:
        """Resolve entry size/resolution details for selected quality."""
        size_by_quality = entry.get("size_by_quality_mb") or {}
        resolution_by_quality = entry.get("resolution_by_quality") or {}
        format_note_by_quality = entry.get("format_note_by_quality") or {}

        size_mb = size_by_quality.get(quality_label, entry.get("filesize_mb", 0) or 0)
        resolution = resolution_by_quality.get(quality_label, entry.get("resolution", "Unknown") or "Unknown")
        format_note = format_note_by_quality.get(quality_label, entry.get("format_note", "") or "")

        return {
            "size_mb": float(size_mb or 0),
            "resolution": str(resolution),
            "format_note": str(format_note),
        }

    def _build_playlist_detail_text(self, entry: Dict[str, Any], quality_label: str) -> str:
        """Build compact detail row text for playlist items."""
        duration = self._format_duration(entry.get("duration"))
        metrics = self._get_playlist_entry_quality_metrics(entry, quality_label)
        size_mb = metrics["size_mb"]
        resolution = metrics["resolution"]
        format_note = metrics["format_note"]

        details_parts: List[str] = []
        if duration:
            details_parts.append(f"{Icons.HISTORY} {duration}")
        if resolution and resolution != "Unknown":
            details_parts.append(f"{Icons.QUALITY_SELECT} {resolution}")
        if size_mb > 0:
            details_parts.append(f"{Icons.INFO} {self._format_size_from_mb(size_mb)}")
        if format_note:
            details_parts.append(f"{Icons.FORMAT_SELECT} {format_note}")

        return " • ".join(details_parts)

    def _on_quality_changed(self):
        """Refresh playlist details and summary when quality selection changes."""
        if not self.playlist_entries:
            return

        quality_label = self._get_selected_quality_label()
        for detail_label, entry in self.playlist_detail_rows:
            detail_label.configure(text=self._build_playlist_detail_text(entry, quality_label))

        self._update_playlist_summary()

    def _set_url_validation_state(self, icon_text: str, color: str):
        """Safely set URL validation icon when widget exists."""
        url_validation_icon = self.__dict__.get("url_validation_icon")
        if url_validation_icon is not None:
            url_validation_icon.configure(text=icon_text, text_color=color)

    def _setup_tab_switch_transition(self):
        """Apply subtle crossfade effect when switching tabs."""
        segmented = getattr(self.tabview, "_segmented_button", None)
        if segmented is None:
            return

        original_command = getattr(segmented, "_command", None)
        if original_command is None:
            return

        def wrapped_command(tab_name: str):
            original_command(tab_name)
            tab_dict = getattr(self.tabview, "_tab_dict", {})
            selected_tab = tab_dict.get(tab_name)
            if selected_tab is None:
                return

            self.animation_manager.animate_color_transition(
                selected_tab,
                "fg_color",
                Colors.BG_PRIMARY,
                Colors.BG_SURFACE,
                duration=Motion.MICRO,
            )
            self.after(
                Motion.MICRO,
                lambda: self.animation_manager.animate_color_transition(
                    selected_tab,
                    "fg_color",
                    Colors.BG_SURFACE,
                    "transparent",
                    duration=Motion.MICRO,
                ),
            )

        segmented.configure(command=wrapped_command)

    def _apply_button_press_state(self, button):
        """Apply subtle press state with scale and glow feedback."""
        if button is None:
            return
        try:
            if not hasattr(button, "_ravn_base_width"):
                button._ravn_base_width = int(button.cget("width"))
            if button._ravn_base_width > 40:
                button.configure(width=max(40, int(button._ravn_base_width * 0.95)))
            button.configure(border_width=1, border_color=Colors.ACCENT_LIGHT)
        except Exception:
            return

    def _apply_button_release_state(self, button):
        """Restore button to default dimensions and border."""
        if button is None:
            return
        try:
            base_width = int(getattr(button, "_ravn_base_width", button.cget("width")))
            button.configure(width=base_width, border_width=0)
        except Exception:
            return

    def _apply_button_hover_state(self, button, is_hover: bool):
        """Apply subtle beige hover state for action buttons."""
        if button is None:
            return
        try:
            if not hasattr(button, "_ravn_hover_color"):
                button._ravn_hover_color = button.cget("hover_color")
            hover_color = Colors.HOVER_BEIGE if is_hover else button._ravn_hover_color
            button.configure(hover_color=hover_color)
        except Exception:
            return

    def _set_button_loading_state(self, button, is_loading: bool):
        """Animate disabled/enabled transition for buttons."""
        if button is None:
            return
        try:
            if is_loading:
                button.configure(state="disabled")
                self.animation_manager.animate_button_disabled(
                    button,
                    duration=Motion.MICRO,
                    target_opacity=0.5,
                )
            else:
                button.configure(state="normal")
                self.animation_manager.animate_button_enabled(
                    button,
                    duration=Motion.MICRO,
                    target_color=Colors.TEXT_PRIMARY,
                )
        except Exception:
            return

    def _start_processing_feedback(self, base_text: str = "Processing"):
        """Start animated spinner and processing ellipsis loop."""
        status_label = self.__dict__.get("download_status_label")
        if status_label is None:
            return

        self._processing_text_base = base_text
        self._processing_tick = 0
        self._processing_spinner_index = 0
        self._download_progress_value = 0.0

        spinner_id = self.__dict__.get("_spinner_animation_id")
        if spinner_id:
            self.animation_manager.stop_animation(spinner_id)
            self._spinner_animation_id = None

        self._update_processing_feedback()

    def _update_processing_feedback(self):
        """Advance animated processing text loop."""
        status_label = self.__dict__.get("download_status_label")
        if status_label is None:
            return

        spinner_frames = ("◐", "◓", "◑", "◒")
        spinner = spinner_frames[self._processing_spinner_index % len(spinner_frames)]

        text = self.animation_manager.format_processing_text(
            self._processing_text_base,
            self._processing_tick,
        )
        status_label.configure(
            text=f"{spinner} {text}",
            text_color=Colors.STATUS_RUNNING,
        )
        self._processing_tick += 1
        self._processing_spinner_index += 1
        self._processing_after_id = self.after(125, self._update_processing_feedback)

    def _stop_processing_feedback(self):
        """Stop spinner and processing text updates."""
        processing_after_id = self.__dict__.get("_processing_after_id")
        if processing_after_id is not None:
            try:
                self.after_cancel(processing_after_id)
            except Exception:
                pass
            self._processing_after_id = None

        spinner_id = self.__dict__.get("_spinner_animation_id")
        if spinner_id:
            self.animation_manager.stop_animation(spinner_id)
            self._spinner_animation_id = None

    def _animate_error_details_height(self, target_height: int, on_done=None):
        """Animate technical details area expansion/collapse."""
        textbox = self.__dict__.get("raw_error_textbox")
        if textbox is None:
            if on_done:
                on_done()
            return

        current_height = int(textbox.cget("height") or 0)
        target_height = max(0, int(target_height))

        if current_height == target_height:
            if on_done:
                on_done()
            return

        direction = 1 if target_height > current_height else -1
        step = 10

        def tick():
            nonlocal current_height
            current_height += step * direction
            reached = current_height >= target_height if direction > 0 else current_height <= target_height
            if reached:
                current_height = target_height
            textbox.configure(height=current_height)
            if not reached:
                self.after(16, tick)
            elif on_done:
                on_done()

        tick()

    def _retry_last_action(self):
        """Retry the most likely failing action from the error box."""
        if self.is_playlist_fetching or self.is_info_fetching:
            return

        if self.playlist_entries and self.playlist_source_url == self.url_entry.get().strip():
            self._download_video()
            return

        self._fetch_download_data()

    def _clear_playlist_selection(self):
        """Playlist seçimiyle ilgili UI ve state bilgisini temizle."""
        self.playlist_entries = []
        self.playlist_selection_vars = []
        self.playlist_detail_rows = []
        self.playlist_source_url = ""
        self.is_playlist_fetching = False
        self.is_info_fetching = False

        playlist_list_frame = self.__dict__.get("playlist_list_frame")
        if playlist_list_frame is not None:
            for child in playlist_list_frame.winfo_children():
                child.destroy()

        playlist_frame = self.__dict__.get("playlist_frame")
        if playlist_frame is not None:
            playlist_frame.pack_forget()

        download_btn = self.__dict__.get("download_btn")
        if download_btn is not None:
            download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} İndir", state="normal")

    def _update_playlist_summary(self):
        """Playlist özet bilgilerini güncelle (seçili sayı + toplam boyut)."""
        playlist_summary_label = self.__dict__.get("playlist_summary_label")
        if playlist_summary_label is None:
            return

        if not self.playlist_entries or not self.playlist_selection_vars:
            return

        selected_count = sum(1 for var in self.playlist_selection_vars if var.get())
        total_count = len(self.playlist_entries)
        quality_label = self._get_selected_quality_label()

        # Seçili videoların toplam boyutunu hesapla
        total_size_mb = 0
        for i, var in enumerate(self.playlist_selection_vars):
            if var.get() and i < len(self.playlist_entries):
                entry_metrics = self._get_playlist_entry_quality_metrics(
                    self.playlist_entries[i], quality_label
                )
                total_size_mb += entry_metrics["size_mb"]

        # Boyut formatla
        size_text = self._format_size_from_mb(total_size_mb)

        # Özet metni oluştur
        summary = f"{Icons.QUEUED_STATUS} {selected_count}/{total_count} video seçili"
        if total_size_mb > 0:
            summary += f" • {Icons.INFO} ~{size_text} ({quality_label})"

        playlist_summary_label.configure(text=summary)

    def _select_all_playlist_items(self):
        """Playlist listesindeki tüm öğeleri seç."""
        for var in self.playlist_selection_vars:
            var.set(True)
        self._update_playlist_summary()

    def _clear_all_playlist_items(self):
        """Playlist listesindeki seçimleri temizle."""
        for var in self.playlist_selection_vars:
            var.set(False)
        self._update_playlist_summary()

    def _get_selected_playlist_entries(self) -> List[Dict[str, Any]]:
        """Seçilen playlist öğelerini döndür."""
        selected: List[Dict[str, Any]] = []
        for entry, variable in zip(self.playlist_entries, self.playlist_selection_vars):
            if variable.get():
                selected.append(entry)
        return selected

    def _start_playlist_fetch(self, url: str):
        """Playlist içeriğini çek ve kullanıcı seçimi için göster."""
        self.is_playlist_fetching = True
        self.error_frame.pack_forget()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        selected_quality = self._get_selected_quality_label()
        self._start_processing_feedback(f"Playlist bilgisi alınıyor ({selected_quality})")
        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.RUNNING_STATUS} Veriler Getiriliyor...")
            self._set_button_loading_state(fetch_data_btn, is_loading=True)
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} Liste Alınıyor...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        def run_playlist_fetch():
            entries = self.downloader.extract_playlist_entries(url, quality_label=selected_quality)
            self.after(0, self._on_playlist_fetch_complete, url, entries)

        threading.Thread(target=run_playlist_fetch, daemon=True).start()

    def _on_playlist_fetch_complete(self, url: str, entries: List[Dict[str, Any]]):
        """Playlist fetch tamamlandığında UI'ı güncelle."""
        self.is_playlist_fetching = False
        self._stop_processing_feedback()
        self._hide_progress()
        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            self._set_button_loading_state(fetch_data_btn, is_loading=False)

        if not entries:
            self._set_button_loading_state(self.download_btn, is_loading=False)
            self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} İndir")
            self.download_status_label.configure(text="")
            if fetch_data_btn is not None:
                fetch_data_btn.configure(text=f"{Icons.SEARCH} Playlist Verilerini Getir")
            self._show_download_error(
                "Playlist içeriği alınamadı. URL'yi kontrol edip tekrar deneyin.",
                "Playlist entries not found",
            )
            return

        self.playlist_entries = entries
        self.playlist_source_url = url
        self.playlist_selection_vars = []
        self.playlist_detail_rows = []
        quality_label = self._get_selected_quality_label()

        for child in self.playlist_list_frame.winfo_children():
            child.destroy()

        for idx, entry in enumerate(entries, start=1):
            variable = ctk.BooleanVar(value=True)
            self.playlist_selection_vars.append(variable)

            title = entry.get("title", "Unknown")

            # Ana container frame
            item_frame = ctk.CTkFrame(self.playlist_list_frame, fg_color=Colors.BG_SURFACE)
            item_frame.pack(fill="x", padx=2, pady=1)

            # Checkbox + başlık
            top_row = ctk.CTkFrame(item_frame, fg_color="transparent")
            top_row.pack(fill="x", padx=8, pady=(3, 2))

            item_checkbox = ctk.CTkCheckBox(
                top_row,
                text="",
                variable=variable,
                command=self._update_playlist_summary,
                font=Fonts.LABEL_BOLD
            )
            item_checkbox.pack(side="left", padx=(0, 6))

            item_title = ctk.CTkLabel(
                top_row,
                text=f"{idx}. {title}",
                font=Fonts.LABEL_BOLD,
                anchor="w",
                justify="left",
                text_color=Colors.TEXT_PRIMARY,
            )
            item_title.pack(side="left", fill="x", expand=True)

            # Tek satır detay bilgileri (uzun listelerde daha okunabilir)
            detail_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
            detail_frame.pack(fill="x", padx=38, pady=(0, 3))

            detail_label = ctk.CTkLabel(
                detail_frame,
                text=self._build_playlist_detail_text(entry, quality_label),
                font=Fonts.SMALL,
                text_color=Colors.TEXT_MUTED,
                anchor="w",
                justify="left",
            )
            detail_label.pack(fill="x")
            self.playlist_detail_rows.append((detail_label, entry))

        self._update_playlist_summary()
        self.playlist_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10), before=self.download_btn)
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} Seçilenleri İndir")
        self.download_status_label.configure(text="İndirilecek playlist öğelerini seçin.")
        self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.REFRESH} Playlist Verilerini Yenile")

    def _start_video_info_fetch(self, url: str):
        """Tek video için metadata bilgisini getir."""
        self.is_info_fetching = True
        self.error_frame.pack_forget()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback("Video bilgisi alınıyor")

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.RUNNING_STATUS} Veriler Getiriliyor...")
            self._set_button_loading_state(fetch_data_btn, is_loading=True)

        def run_info_fetch():
            info = self.downloader.extract_video_info(url)
            self.after(0, self._on_video_info_fetch_complete, info)

        threading.Thread(target=run_info_fetch, daemon=True).start()

    def _on_video_info_fetch_complete(self, info: Optional[Dict[str, Any]]):
        """Video metadata fetch sonucu."""
        self.is_info_fetching = False
        self._stop_processing_feedback()
        self._hide_progress()

        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            self._set_button_loading_state(fetch_data_btn, is_loading=False)
            fetch_data_btn.configure(text=f"{Icons.REFRESH} Video Bilgilerini Yenile")

        if not info:
            self.download_status_label.configure(text="")
            self._show_download_error(
                "Video bilgileri alınamadı. URL'yi kontrol edip tekrar deneyin.",
                "Video info not found",
            )
            return

        title = str(info.get("title") or "Bilinmiyor")
        uploader = str(info.get("uploader") or "Bilinmiyor")
        duration = self._format_duration(info.get("duration"))
        details = f"{title} • {uploader}"
        if duration:
            details = f"{details} • {duration}"
        self.download_status_label.configure(text=f"Hazır: {details}")
        self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)

    def _fetch_download_data(self):
        """İndir öncesi metadata/playlist içeriğini getir."""
        url = self.url_entry.get().strip()
        if not url:
            self._show_download_error("Lütfen bir URL girin.", "")
            return

        if self._looks_like_playlist_url(url):
            if self.is_playlist_fetching:
                return
            self._start_playlist_fetch(url)
            return

        if self.is_info_fetching:
            return
        self._start_video_info_fetch(url)

    def _start_single_download(
        self,
        url: str,
        output_dir: str,
        format_type: DownloadFormat,
        quality: DownloadQuality
    ):
        """Tek medya URL'si için indirme başlat."""
        self.error_frame.pack_forget()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback("İndiriliyor")
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} İndiriliyor...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        def run_download():
            try:
                result = self.downloader.download(
                    url=url,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    progress_callback=self._on_download_progress
                )
                if result.success:
                    self.after(0, self._on_download_success, result)
                else:
                    self.after(0, self._on_download_failure, result.error_message)
            except Exception as exc:
                self.after(0, self._on_download_failure, str(exc))

        thread = threading.Thread(target=run_download, daemon=True)
        thread.start()

    def _start_playlist_download(
        self,
        selected_entries: List[Dict[str, Any]],
        output_dir: str,
        format_type: DownloadFormat,
        quality: DownloadQuality
    ):
        """Seçilen playlist öğelerini sıralı olarak indir."""
        total = len(selected_entries)
        self.error_frame.pack_forget()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback(f"{total} öğe indiriliyor")
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} İndiriliyor...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        def run_playlist_download():
            all_files: List[str] = []
            for index, entry in enumerate(selected_entries, start=1):
                entry_url = entry.get("url", "")
                entry_title = entry.get("title", f"Öğe {index}")
                if not entry_url:
                    continue

                def item_progress(percent: int, message: str, current=index, title=entry_title):
                    overall = int(((current - 1) + max(0, min(100, percent)) / 100.0) / total * 100)
                    prefix = f"{current}/{total} • {title}"
                    if message:
                        self._on_download_progress(overall, f"{prefix} • {message}")
                    else:
                        self._on_download_progress(overall, prefix)

                result = self.downloader.download(
                    url=entry_url,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    progress_callback=item_progress,
                )

                if not result.success:
                    self.after(
                        0,
                        self._on_download_failure,
                        f"Playlist indirmesi başarısız ({index}/{total}): {result.error_message}",
                    )
                    return

                all_files.extend(result.output_files or [])

            class _PlaylistResult:
                def __init__(self, files: List[str]):
                    self.output_files = files

            self.after(0, self._on_download_success, _PlaylistResult(all_files))

        threading.Thread(target=run_playlist_download, daemon=True).start()

    def _download_video(self):
        """Videoyu arka planda indir"""
        if self.queue_paused:
            self._show_download_error("Kuyruk duraklatıldı. Devam etmek için tekrar etkinleştirin.", "")
            return

        # Batch mode check (safe for tests that don't initialize UI)
        batch_mode = False
        try:
            if hasattr(self, 'batch_mode_var'):
                batch_mode = self.batch_mode_var.get()
        except (AttributeError, RecursionError):
            pass

        if batch_mode:
            self._download_batch()
            return

        url = self.url_entry.get().strip()
        if not url:
            self._show_download_error("Lütfen bir URL girin.", "")
            return

        quality_label = self.quality_menu.get()
        format_label = self.format_menu.get()

        quality = _QUALITY_MAP.get(quality_label, DownloadQuality.BEST)
        format_type = _FORMAT_MAP.get(format_label, DownloadFormat.MP4)

        default_path = self.config_manager.get(
            'default_download_path',
            str(Path.home() / 'Downloads' / 'RAVN')
        )
        output_dir = str(Path(default_path))

        if self._looks_like_playlist_url(url):
            if self.is_playlist_fetching:
                return

            if self.playlist_source_url != url or not self.playlist_entries:
                self._show_download_error("Önce 'Verileri Getir' butonuna basarak playlist içeriğini alın.", "")
                return

            selected_entries = self._get_selected_playlist_entries()
            if not selected_entries:
                self._show_download_error("Lütfen indirilecek en az bir playlist öğesi seçin.", "")
                return

            self._start_playlist_download(selected_entries, output_dir, format_type, quality)
            return

        self._start_single_download(url, output_dir, format_type, quality)

    def _download_batch(self):
        """Download multiple URLs from batch text area"""
        batch_text = self.batch_url_text.get("1.0", "end").strip()
        if not batch_text:
            self._show_download_error("Lütfen en az bir URL girin.", "")
            return

        urls = [line.strip() for line in batch_text.split('\n') if line.strip()]
        if not urls:
            self._show_download_error("Geçerli URL bulunamadı.", "")
            return

        if len(urls) > 50:
            self._show_download_error("Maksimum 50 URL destekleniyor. İlk 50 URL indirilecek.", "")
            urls = urls[:50]

        quality_label = self.quality_menu.get()
        format_label = self.format_menu.get()

        quality = _QUALITY_MAP.get(quality_label, DownloadQuality.BEST)
        format_type = _FORMAT_MAP.get(format_label, DownloadFormat.MP4)

        default_path = self.config_manager.get(
            'default_download_path',
            str(Path.home() / 'Downloads' / 'RAVN')
        )
        output_dir = str(Path(default_path))

        # Queue all downloads
        self.download_status_label.configure(text=f"{len(urls)} URL kuyruğa ekleniyor...")
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} Kuyruğa Ekleniyor...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        for idx, url in enumerate(urls, start=1):
            task_name = f"Toplu İndirme {idx}/{len(urls)}"
            self.task_queue.add_task(
                task_type=TaskType.DOWNLOAD,
                name=task_name,
                execute_fn=lambda u=url: self.downloader.download(
                    url=u,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality
                )
            )

        self.download_status_label.configure(text=f"{len(urls)} URL kuyruğa eklendi. Kuyruk sekmesinden takip edin.")
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} İndir")

        # Switch to queue tab to show progress
        self.tabview.set(f"{Icons.QUEUE}  Kuyruk")

    def _on_download_progress(self, percent: int, message: str):
        """İlerleme callback'i — iş parçacığından çağrılır"""
        self.after(0, self._apply_progress_update, percent, message)

    def _apply_progress_update(self, percent: int, message: str):
        """Ana iş parçacığında ilerleme çubuğunu güncelle"""
        target = max(0.0, min(1.0, percent / 100.0))
        current = self.__dict__.get("_download_progress_value", 0.0)
        self._download_progress_value = self.animation_manager.smooth_progress(
            current,
            target,
            max_step=0.08,
        )
        self.download_progress.set(self._download_progress_value)
        if message:
            self.download_status_label.configure(text=message)

    def _on_download_success(self, result):
        """İndirme başarılı — UI'ı güncelle"""
        self._stop_processing_feedback()
        self.download_progress.set(1.0)
        self._download_progress_value = 1.0
        files = ", ".join(result.output_files) if result.output_files else "tamamlandı"
        self.download_status_label.configure(
            text=f"İndirme tamamlandı: {files}",
            text_color=Colors.STATUS_DONE
        )
        self.animation_manager.animate_success_flash(
            self.download_status_label,
            duration=Motion.SLOW,
            base_color=Colors.STATUS_DONE,
            flash_color=Colors.SUCCESS_FLASH,
        )
        self._animate_download_completion_pulse()
        try:
            self.bell()
        except Exception:
            pass
        if result.output_files:
            NotificationManager.show_download_complete(Path(result.output_files[0]).name)
        # POL-20: Show success toast
        if self.toast_manager:
            filename = Path(result.output_files[0]).name if result.output_files else "Dosya"
            self.toast_manager.show_success(f"İndirme tamamlandı: {filename}")
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} İndir")
        self.after(3000, lambda: (self._hide_progress(), self.download_status_label.configure(text="", text_color=Colors.TEXT_SECONDARY)))

    def _on_download_failure(self, error_message: str):
        """İndirme başarısız — hata mesajını göster"""
        self._stop_processing_feedback()
        self._hide_progress()
        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} İndir")
        self._show_download_error(error_message, error_message)
        # POL-21: Show warning toast for failures
        if self.toast_manager:
            short_msg = error_message[:50] + "..." if len(error_message) > 50 else error_message
            self.toast_manager.show_warning(f"İndirme başarısız: {short_msg}")

    def _animate_download_completion_pulse(self):
        """Pulse progress bar color briefly on completion."""
        progress_widget = self.__dict__.get("download_progress")
        if progress_widget is None:
            return

        progress_widget.configure(progress_color=Colors.SUCCESS_FLASH)
        self.after(
            Motion.SLOW,
            lambda: progress_widget.configure(progress_color=Colors.PROGRESS_FILL),
        )

    def _hide_progress(self):
        """İlerleme çubuğunu gizle"""
        self.download_progress.pack_forget()

    def _show_download_error(self, raw_error: str, raw_text: str):
        """Hata mesajını göster; hata çerçevesini görünür yap"""
        error_info = YtDlpErrorParser.parse(raw_error)
        user_message = format_error_for_user(error_info)
        self._set_url_validation_state(Icons.ERROR_INDICATOR, Colors.ERROR)

        self.error_message_label.configure(text=user_message)

        self.raw_error_textbox.configure(state="normal")
        self.raw_error_textbox.delete("1.0", "end")
        self.raw_error_textbox.insert("1.0", raw_text or raw_error)
        self.raw_error_textbox.configure(state="disabled")

        # Teknik detayları gizle
        if self._raw_error_visible:
            self.raw_error_textbox.pack_forget()
            self._raw_error_visible = False
            self.toggle_details_btn.configure(text=f"{Icons.INFO} Teknik Detaylar")

        self.error_frame.pack(padx=15, pady=5, fill="x")
        self.animation_manager.animate_color_transition(
            self.error_frame,
            "fg_color",
            Colors.BG_PRIMARY,
            Colors.ERROR_BG,
            duration=Motion.STANDARD,
        )

    def _toggle_error_details(self):
        """Ham hata metnini göster / gizle"""
        if self._raw_error_visible:
            self.animation_manager.animate_color_transition(
                self.error_frame,
                "border_color",
                Colors.ACCENT,
                Colors.BORDER,
                duration=Motion.MICRO,
            )

            def hide_box():
                self.raw_error_textbox.pack_forget()
                self._raw_error_visible = False
                self.toggle_details_btn.configure(text=f"{Icons.INFO} Teknik Detaylar")

            self._animate_error_details_height(0, on_done=hide_box)
        else:
            self.raw_error_textbox.pack(padx=10, pady=(0, 10), fill="x")
            self.raw_error_textbox.configure(height=1)
            self._raw_error_visible = True
            self.toggle_details_btn.configure(text=f"{Icons.CLOSE} Gizle")
            self.animation_manager.animate_color_transition(
                self.error_frame,
                "border_color",
                Colors.BORDER,
                Colors.ACCENT,
                duration=Motion.MICRO,
            )
            self._animate_error_details_height(100)

    def _setup_converter_tab(self, tab):
        """Dönüştürme sekmesini kur (Faz 2)"""
        converter = ConverterTab(
            tab,
            db_manager=self.db_manager,
            notify_callback=self._notify_conversion_complete,
            fg_color="transparent"
        )
        converter.pack(fill="both", expand=True)

    def _setup_subtitle_tab(self, tab):
        """Altyazı sekmesini kur (Faz 3)"""
        subtitle_manager = SubtitleTab(tab, fg_color="transparent")
        subtitle_manager.pack(fill="both", expand=True)

    def _setup_queue_tab(self, tab):
        """Kuyruk sekmesini kur (Faz 4)"""
        queue_panel = QueuePanel(
            tab,
            on_cancel_task=self._cancel_queue_task,
            on_open_folder=self._open_output_folder,
            fg_color="transparent"
        )
        queue_panel.pack(fill="both", expand=True)

    def _cancel_queue_task(self, task_id: str):
        """Cancel a task in the queue"""
        if self.task_queue.cancel_task(task_id):
            self.download_status_label.configure(text=f"Görev iptal edildi: {task_id}")
        else:
            self.download_status_label.configure(text=f"Görev iptal edilemedi: {task_id}")

    def _open_output_folder(self, file_path: str):
        """Open file explorer at output file location"""
        import platform
        import subprocess
        from pathlib import Path

        folder_path = Path(file_path).parent
        if not folder_path.exists():
            return

        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["explorer", "/select,", str(file_path)], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", "-R", str(file_path)], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", str(folder_path)], check=False)
        except Exception as e:
            logger.error(f"Failed to open folder: {e}")

    def _setup_history_tab(self, tab):
        """Geçmiş sekmesini kur (Faz 4)"""
        history_viewer = HistoryTab(tab, self.db_manager, fg_color="transparent")
        history_viewer.pack(fill="both", expand=True)

    def _setup_settings_tab_full(self, tab):
        """Ayarlar sekmesini kur (Faz 4 & 5 - Gelişmiş)"""
        settings_manager = SettingsTab(tab, self.config_manager, fg_color="transparent")
        settings_manager.pack(fill="both", expand=True)

    def _change_appearance(self, choice):
        """Görünüm modunu değiştir"""
        ctk.set_appearance_mode(choice)

    def _change_theme(self, choice):
        """Tema rengini değiştir"""
        ctk.set_default_color_theme(choice)

    def _notify_conversion_complete(self, output_file: str):
        """Conversion success notification callback."""
        NotificationManager.show_conversion_complete(Path(output_file).name)

    def _setup_tray_integration(self):
        """Initialize system tray integration if dependency is available."""
        self.tray = SystemTrayIntegration(
            app_name="RAVN",
            on_open=self._restore_from_tray,
            on_pause_queue=self._toggle_queue_pause,
            on_quit=self._quit_from_tray,
        )
        if self.tray.available:
            self.tray.run()

    def _toggle_queue_pause(self):
        """Pause/resume queue state used by UI-triggered jobs."""
        self.queue_paused = self.task_queue.toggle_pause()
        state_label = "Duraklatıldı" if self.queue_paused else "Devam"
        self.download_status_label.configure(text=f"Kuyruk: {state_label}")

    def _restore_from_tray(self):
        """Show and focus window when tray Open is clicked."""
        self.after(0, self._show_window)

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_window_close(self):
        """Minimize to tray instead of closing."""
        if not self.tray or not self.tray.available:
            self._quit_app()
            return
        self.withdraw()
        self.download_status_label.configure(
            text="Uygulama sistem çekmecesine küçültüldü."
        )

    def _quit_from_tray(self):
        """Terminate app via tray action."""
        self.after(0, self._quit_app)

    def _quit_app(self):
        if self.tray:
            self.tray.stop()
        self.destroy()


def main():
    """Uygulamayı başlat"""
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
