"""
RAVN - History and Settings Tab (Faz 4)
Geçmiş ve ayarlar arayüzü
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter.ttk as ttk
from pathlib import Path
import unicodedata
from ..core.database import DatabaseManager, ConfigManager
from ravn_app.core.i18n import t
from .advanced_features import SearchFilter, ThemeManager
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Spacing, Sizes, Icons
from ravn_app.ui.ui_components import style_combo, style_entry, Tooltip


class HistoryTab(ctk.CTkFrame):
    """Geçmiş görüntüleme sekmesi"""

    def __init__(self, parent, database_manager: DatabaseManager, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = database_manager
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        """UI'ı oluştur"""
        # Başlık
        header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        header_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(
            header_frame,
            text=t("history.title"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=Spacing.SM)

        # İstatistikler butonu
        self.stats_btn = ctk.CTkButton(
            header_frame,
            text=t("history.statistics"),
            command=self.show_statistics,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            cursor=Cursors.POINTER,
        )
        self.stats_btn.pack(side="right", padx=Spacing.XS)
        Tooltip(self.stats_btn, t("history.statisticsTooltip"))

        # Temizle butonu
        self.clear_btn = ctk.CTkButton(
            header_frame,
            text=t("history.clear"),
            command=self.clear_history,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            cursor=Cursors.POINTER,
        )
        self.clear_btn.pack(side="right", padx=Spacing.XS)
        Tooltip(self.clear_btn, t("history.clearTooltip"))

        # Arama ve filtre
        search_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        search_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.XS)

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text=f"{Icons.SEARCH} {t('history.search')}",
            width=300
        )
        style_entry(self.search_entry)
        self.search_entry.pack(side="left", padx=Spacing.XS)
        self.search_entry.bind("<KeyRelease>", lambda e: self.filter_history())
        Tooltip(self.search_entry, t("history.searchTooltip"))

        ctk.CTkLabel(search_frame, text=t("history.format"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=Spacing.XS)
        self.format_filter = ctk.CTkComboBox(
            search_frame,
            values=[t("common.all"), "MP4", "MP3", "MKV", "AVI"],
            command=lambda v: self.filter_history(),
            width=100
        )
        style_combo(self.format_filter)
        self.format_filter.pack(side="left", padx=Spacing.XS)
        Tooltip(self.format_filter, t("history.formatFilterTooltip"))

        ctk.CTkLabel(search_frame, text=t("history.status"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=Spacing.XS)
        self.status_filter = ctk.CTkComboBox(
            search_frame,
            values=[t("common.all"), "completed", "failed", "cancelled"],
            command=lambda v: self.filter_history(),
            width=120
        )
        style_combo(self.status_filter)
        self.status_filter.pack(side="left", padx=Spacing.XS)
        Tooltip(self.status_filter, t("history.statusFilterTooltip"))

        # Scrollable liste
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_CARD)
        self.scrollable_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)

    def load_history(self):
        """Geçmişi yükle"""
        # Mevcut öğeleri temizle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        downloads = self.db.get_downloads(limit=100)

        if not downloads:
            ctk.CTkLabel(
                self.scrollable_frame,
                text=t("history.noHistory"),
                font=Fonts.LABEL,
                text_color=Colors.TEXT_MUTED
            ).pack(pady=Spacing.XL)
            return

        for download in downloads:
            self.create_history_item(download)

    def create_history_item(self, download):
        """Geçmiş öğesi oluştur"""
        item_frame = ctk.CTkFrame(self.scrollable_frame, fg_color=Colors.BG_SURFACE)
        item_frame.pack(fill="x", pady=3)

        # Sol taraf - Bilgiler
        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="x", expand=True, padx=Spacing.XS, pady=Spacing.XS)

        # Başlık
        title_label = ctk.CTkLabel(
            info_frame,
            text=download.title or t("history.noTitle"),
            font=Fonts.LABEL_BOLD,
            anchor="w",
            text_color=Colors.TEXT_PRIMARY,
            wraplength=400,
        )
        title_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Detaylar
        details = f"{Icons.FOLDER} {download.format} | {Icons.INFO} {download.quality} | {Icons.INFO} {self.format_size(download.file_size)}"
        details_label = ctk.CTkLabel(
            info_frame,
            text=details,
            font=Fonts.SMALL,
            anchor="w",
            text_color=Colors.TEXT_MUTED
        )
        details_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Tarih
        date_label = ctk.CTkLabel(
            info_frame,
            text=f"{Icons.HISTORY} {download.download_date}",
            font=Fonts.SMALL,
            anchor="w",
            text_color=Colors.TEXT_MUTED
        )
        date_label.pack(fill="x", padx=Spacing.XS, pady=2)

        # Sağ taraf - Butonlar
        button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=Spacing.XS)

        # Durum badge
        status_colors = {
            "completed": Colors.SUCCESS,
            "failed": Colors.ERROR,
            "cancelled": Colors.WARNING,
        }
        status_label = ctk.CTkLabel(
            button_frame,
            text=download.status,
            fg_color=status_colors.get(download.status, Colors.BTN_SECONDARY),
            corner_radius=Sizes.CORNER_SM,
            width=80,
            text_color=Colors.BG_PRIMARY,
        )
        status_label.pack(pady=2)

        # Dosyayı aç butonu
        if download.file_path and Path(download.file_path).exists():
            ctk.CTkButton(
                button_frame,
                text=f"{Icons.FOLDER} {t('history.open')}",
                width=80,
                command=lambda: self.open_file(download.file_path),
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                cursor=Cursors.POINTER,
            ).pack(pady=2)

    def filter_history(self):
        """Geçmişi filtrele"""
        search_term = self.search_entry.get()
        format_filter = self.format_filter.get()
        status_filter = self.status_filter.get()

        # Tüm kayıtları al
        all_downloads = self.db.get_downloads(limit=1000)

        # Filtreleme uygula
        filtered = SearchFilter.filter_downloads(
            [d.__dict__ for d in all_downloads],
            search_term,
            None if format_filter == t("common.all") else format_filter,
            None if status_filter == t("common.all") else status_filter
        )

        # UI'ı güncelle
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        for download_dict in filtered:
            from ..core.database import DownloadRecord
            download = DownloadRecord(**download_dict)
            self.create_history_item(download)

    def show_statistics(self):
        """İstatistikleri göster"""
        stats = self.db.get_statistics()

        stats_text = t(
            "history.statsTemplate",
            totalDownloads=stats['total_downloads'],
            successDownloads=stats['successful_downloads'],
            totalSize=self.format_size(stats['total_size']),
            totalConversions=stats['total_conversions'],
            popularFormat=(stats['most_popular_format']['format'] if stats['most_popular_format'] else 'N/A'),
        )
        messagebox.showinfo(t("history.statsTitle"), stats_text)

    def clear_history(self):
        """Geçmişi temizle"""
        response = messagebox.askyesno(
            t("history.clearConfirmTitle"),
            t("history.clearConfirmMessage")
        )
        if response:
            self.db.clear_history("downloads")
            self.load_history()
            messagebox.showinfo(t("settings.saveSuccessTitle"), t("history.clearSuccess"))

    @staticmethod
    def open_file(file_path: str):
        """Dosyayı aç"""
        import os
        import platform

        if platform.system() == 'Windows':
            os.startfile(file_path)
        elif platform.system() == 'Darwin':  # macOS
            os.system(f'open "{file_path}"')
        else:  # Linux
            os.system(f'xdg-open "{file_path}"')

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Dosya boyutunu formatla"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"


class SettingsTab(ctk.CTkFrame):
    """Ayarlar sekmesi"""

    def __init__(self, parent, config_manager: ConfigManager, on_language_changed=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config_manager
        self.on_language_changed = on_language_changed
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.setup_ui()
        self.load_settings()

    @staticmethod
    def _normalize_quality_for_storage(value: str) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "").strip())
        normalized = normalized.encode("ascii", "ignore").decode("ascii").strip().lower()
        if normalized in {"best", "en iyi"}:
            return "best"
        return value

    @staticmethod
    def _quality_for_display(value: str) -> str:
        if str(value or "").strip().lower() == "best":
            return t("download.qualityBest")
        return value

    def setup_ui(self):
        """UI'ı oluştur"""
        # Başlık
        ctk.CTkLabel(
            self,
            text=t("settings.title"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(pady=(Spacing.SM, Spacing.XS))

        ctk.CTkLabel(
            self,
            text=t("settings.compactHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.SM))

        self.content_frame = ctk.CTkScrollableFrame(self, fg_color=Colors.BG_CARD)
        self.content_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.XS)

        self._create_section_header(self.content_frame, t("settings.general"))
        self.create_general_settings(self.content_frame)

        self._create_section_header(self.content_frame, t("settings.download"))
        self.create_download_settings(self.content_frame)

        self._create_section_header(self.content_frame, t("settings.conversion"))
        self.create_conversion_settings(self.content_frame)

        # Alt butonlar
        button_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        button_frame.pack(fill="x", padx=Spacing.LG, pady=Spacing.SM)

        ctk.CTkButton(
            button_frame,
            text=t("common.save"),
            command=self.save_settings,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text=t("common.reset"),
            command=self.reset_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text=t("common.export"),
            command=self.export_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

        ctk.CTkButton(
            button_frame,
            text=t("common.import"),
            command=self.import_settings,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD
        ).pack(side="left", padx=Spacing.XS)

    def _create_section_header(self, parent, text: str):
        ctk.CTkLabel(
            parent,
            text=text,
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(fill="x", padx=Spacing.SM, pady=(Spacing.SM, Spacing.XS))

    def create_general_settings(self, parent):
        """Genel ayarlar"""
        # Tema
        theme_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        theme_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(theme_frame, text=t("settings.theme"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.theme_combo = ctk.CTkComboBox(
            theme_frame,
            values=ThemeManager.get_theme_names(),
            command=lambda _value: self._preview_theme_selection(),
        )
        style_combo(self.theme_combo)
        self.theme_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Dil
        lang_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        lang_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(lang_frame, text=t("settings.language"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.language_combo = ctk.CTkComboBox(
            lang_frame,
            values=["Türkçe", "English"]
        )
        style_combo(self.language_combo)
        self.language_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Bildirimler
        notification_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        notification_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.notifications_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            notification_frame,
            text=t("settings.notifications"),
            variable=self.notifications_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.auto_update_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            notification_frame,
            text=t("settings.autoUpdate"),
            variable=self.auto_update_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        # Kapatma davranışı
        tray_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        tray_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(tray_frame, text=t("settings.closeBehavior"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.close_behavior_combo = ctk.CTkComboBox(
            tray_frame,
            values=[t("settings.closeToTray"), t("settings.closeFully")],
            state="readonly"
        )
        style_combo(self.close_behavior_combo)
        self.close_behavior_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)
        ctk.CTkLabel(
            tray_frame,
            text=t("settings.closeHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", padx=Spacing.XS)

    def create_download_settings(self, parent):
        """İndirme ayarları"""
        # Varsayılan dizin
        dir_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        dir_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(dir_frame, text=t("settings.downloadDir"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        dir_select_frame = ctk.CTkFrame(dir_frame, fg_color="transparent")
        dir_select_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        self.download_dir_entry = ctk.CTkEntry(dir_select_frame)
        style_entry(self.download_dir_entry)
        self.download_dir_entry.pack(side="left", fill="x", expand=True, padx=Spacing.XS)

        ctk.CTkButton(
            dir_select_frame,
            text=t("common.browse"),
            width=80,
            command=self.select_download_dir,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL
        ).pack(side="right", padx=Spacing.XS)

        # Varsayılan format ve kalite
        format_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        format_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(format_frame, text=t("settings.defaultFormat"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.default_format_combo = ctk.CTkComboBox(
            format_frame,
            values=["MP4", "MP3", "MKV"]
        )
        style_combo(self.default_format_combo)
        self.default_format_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(format_frame, text=t("settings.defaultQuality"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.default_quality_combo = ctk.CTkComboBox(
            format_frame,
            values=[t("download.qualityBest"), "1080p", "720p", "480p"]
        )
        style_combo(self.default_quality_combo)
        self.default_quality_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Eşzamanlı indirme
        concurrent_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        concurrent_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(concurrent_frame, text=t("settings.concurrentDownloads"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.concurrent_slider = ctk.CTkSlider(
            concurrent_frame,
            from_=1,
            to=5,
            number_of_steps=4
        )
        self.concurrent_slider.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        self.concurrent_label = ctk.CTkLabel(concurrent_frame, text="1", font=Fonts.LABEL)
        self.concurrent_label.pack(padx=Spacing.XS, pady=Spacing.XS)
        self.concurrent_slider.configure(
            command=lambda v: self.concurrent_label.configure(text=str(int(v)))
        )

        # Geçmiş limiti
        history_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        history_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(history_frame, text=t("settings.historyLimit"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.history_limit_entry = ctk.CTkEntry(history_frame)
        style_entry(self.history_limit_entry)
        self.history_limit_entry.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Altyazı ayarları
        subtitle_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        subtitle_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.auto_subtitle_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            subtitle_frame,
            text=t("settings.autoSubtitle"),
            variable=self.auto_subtitle_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(subtitle_frame, text=t("settings.preferredSubtitle"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.subtitle_lang_combo = ctk.CTkComboBox(
            subtitle_frame,
            values=["tr", "en", "de", "fr", "es"]
        )
        style_combo(self.subtitle_lang_combo)
        self.subtitle_lang_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Metadata ve dosya düzenleme ayarları
        metadata_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        metadata_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(metadata_frame, text=t("settings.metadataSection"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.embed_metadata_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.embedMetadata"),
            variable=self.embed_metadata_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.auto_sort_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.autoSort"),
            variable=self.auto_sort_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        # Torrent / aria2c ayarları
        torrent_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        torrent_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(torrent_frame, text=t("settings.torrentSection"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(torrent_frame, text=t("settings.aria2Path"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS)
        self.aria2c_path_entry = ctk.CTkEntry(torrent_frame)
        style_entry(self.aria2c_path_entry)
        self.aria2c_path_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(torrent_frame, text=t("settings.seedTime"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS)
        self.torrent_seed_time_entry = ctk.CTkEntry(torrent_frame, width=80)
        style_entry(self.torrent_seed_time_entry)
        self.torrent_seed_time_entry.pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(torrent_frame, text=t("settings.maxConnections"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS)
        self.torrent_max_connections_entry = ctk.CTkEntry(torrent_frame, width=80)
        style_entry(self.torrent_max_connections_entry)
        self.torrent_max_connections_entry.pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

    def create_conversion_settings(self, parent):
        """Dönüştürme ayarları"""
        # FFmpeg yolu
        ffmpeg_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        ffmpeg_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        ctk.CTkLabel(ffmpeg_frame, text=t("settings.ffmpegPath"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.ffmpeg_entry = ctk.CTkEntry(ffmpeg_frame)
        style_entry(self.ffmpeg_entry)
        self.ffmpeg_entry.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Otomatik temizlik
        cleanup_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        cleanup_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        self.auto_cleanup_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            cleanup_frame,
            text=t("settings.autoCleanup"),
            variable=self.auto_cleanup_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

    def load_settings(self):
        """Ayarları yükle"""
        self.theme_combo.set(ThemeManager.get_theme_display_name(self.config.get('theme', 'dark')))
        self.language_combo.set("Türkçe" if self.config.get('language') == 'tr' else "English")
        self.notifications_var.set(self.config.get('notifications_enabled', True))
        self.auto_update_var.set(self.config.get('auto_update_check', True))

        self.download_dir_entry.insert(0, self.config.get('default_download_path', ''))
        self.default_format_combo.set(self.config.get('default_format', 'MP4'))
        self.default_quality_combo.set(self._quality_for_display(self.config.get('default_quality', '1080p')))
        self.concurrent_slider.set(self.config.get('concurrent_downloads', 1))
        self.concurrent_label.configure(text=str(self.config.get('concurrent_downloads', 1)))

        self.ffmpeg_entry.insert(0, self.config.get('ffmpeg_path', 'ffmpeg'))
        self.auto_cleanup_var.set(self.config.get('auto_cleanup', False))

        self.history_limit_entry.insert(0, str(self.config.get('history_limit', 1000)))
        self.auto_subtitle_var.set(self.config.get('auto_subtitle_download', False))
        self.subtitle_lang_combo.set(self.config.get('preferred_subtitle_language', 'tr'))
        embed_metadata_var = getattr(self, 'embed_metadata_var', getattr(self, 'auto_id3_var', None))
        auto_sort_var = getattr(self, 'auto_sort_var', None)
        if embed_metadata_var is not None:
            embed_metadata_var.set(self.config.get('embed_metadata', False))
        if auto_sort_var is not None:
            auto_sort_var.set(self.config.get('auto_sort_downloads', self.config.get('auto_sort_by_channel', False)))

        self.aria2c_path_entry.insert(0, self.config.get('aria2c_path', 'aria2c'))
        self.torrent_seed_time_entry.insert(0, str(self.config.get('torrent_seed_time', 0)))
        self.torrent_max_connections_entry.insert(0, str(self.config.get('torrent_max_connections', 16)))

        close_to_tray = self.config.get('close_to_tray', True)
        self.close_behavior_combo.set(
            t("settings.closeToTray") if close_to_tray else t("settings.closeFully")
        )

    def save_settings(self):
        """Ayarları kaydet"""
        theme_combo = getattr(self, 'theme_combo', None)
        language_combo = getattr(self, 'language_combo', None)

        selected_theme = (
            ThemeManager.normalize_theme_name(theme_combo.get())
            if theme_combo is not None
            else None
        )
        old_language = self.config.get('language', 'tr')
        if selected_theme is not None:
            self.config.set('theme', selected_theme)
        if language_combo is not None:
            self.config.set('language', 'tr' if language_combo.get() == "Türkçe" else 'en')
        self.config.set('notifications_enabled', self.notifications_var.get())
        self.config.set('auto_update_check', self.auto_update_var.get())

        self.config.set('default_download_path', self.download_dir_entry.get())
        self.config.set('default_format', self.default_format_combo.get())
        self.config.set('default_quality', self._normalize_quality_for_storage(self.default_quality_combo.get()))
        self.config.set('concurrent_downloads', int(self.concurrent_slider.get()))

        self.config.set('ffmpeg_path', self.ffmpeg_entry.get())
        self.config.set('auto_cleanup', self.auto_cleanup_var.get())

        aria2c_path_entry = getattr(self, 'aria2c_path_entry', None)
        torrent_seed_time_entry = getattr(self, 'torrent_seed_time_entry', None)
        torrent_max_connections_entry = getattr(self, 'torrent_max_connections_entry', None)

        self.config.set('aria2c_path', (aria2c_path_entry.get() if aria2c_path_entry else '') or 'aria2c')
        try:
            self.config.set(
                'torrent_seed_time',
                int(torrent_seed_time_entry.get()) if torrent_seed_time_entry else 0,
            )
        except ValueError:
            self.config.set('torrent_seed_time', 0)
        try:
            self.config.set(
                'torrent_max_connections',
                int(torrent_max_connections_entry.get()) if torrent_max_connections_entry else 16,
            )
        except ValueError:
            self.config.set('torrent_max_connections', 16)

        self.config.set('history_limit', int(self.history_limit_entry.get()))
        self.config.set('auto_subtitle_download', self.auto_subtitle_var.get())
        self.config.set('preferred_subtitle_language', self.subtitle_lang_combo.get())
        self.config.set('close_to_tray', self.close_behavior_combo.get() == t("settings.closeToTray"))
        embed_metadata_var = getattr(self, 'embed_metadata_var', getattr(self, 'auto_id3_var', None))
        auto_sort_var = getattr(self, 'auto_sort_var', None)
        auto_sort_mode_combo = getattr(self, 'auto_sort_mode_combo', None)
        auto_lyrics_var = getattr(self, 'auto_lyrics_var', None)

        if embed_metadata_var is not None:
            embed_metadata_enabled = embed_metadata_var.get()
            self.config.set('embed_metadata', embed_metadata_enabled)
            self.config.set('auto_id3_tagging', embed_metadata_enabled)
        if auto_lyrics_var is not None:
            self.config.set('auto_embed_lyrics', auto_lyrics_var.get())
        if auto_sort_var is not None:
            auto_sort_enabled = auto_sort_var.get()
            self.config.set('auto_sort_by_channel', auto_sort_enabled)
            self.config.set('auto_sort_downloads', auto_sort_enabled)
        if auto_sort_mode_combo is not None:
            self.config.set('auto_sort_mode', auto_sort_mode_combo.get())

        if selected_theme is not None:
            ThemeManager.apply_theme(selected_theme)

        messagebox.showinfo(t("settings.saveSuccessTitle"), t("settings.saved"))

        new_language = self.config.get('language', 'tr') if language_combo is not None else old_language
        on_language_changed = getattr(self, 'on_language_changed', None)
        if old_language != new_language and callable(on_language_changed):
            try:
                on_language_changed()
            except Exception:
                pass

    def _preview_theme_selection(self):
        """Seçilen temayı önizleme olarak uygula."""
        try:
            ThemeManager.apply_theme(self.theme_combo.get())
        except Exception:
            return

    def reset_settings(self):
        """Ayarları sıfırla"""
        response = messagebox.askyesno(
            t("settings.resetConfirmTitle"),
            t("settings.resetConfirmMessage")
        )
        if response:
            self.config.reset()
            self.load_settings()
            messagebox.showinfo(t("settings.saveSuccessTitle"), t("settings.resetDone"))

    def select_download_dir(self):
        """İndirme dizini seç"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.download_dir_entry.delete(0, "end")
            self.download_dir_entry.insert(0, dir_path)

    def export_settings(self):
        """Ayarları dışa aktar"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        if file_path:
            if self.config.export_config(file_path):
                messagebox.showinfo(t("settings.saveSuccessTitle"), t("settings.exportDone"))

    def import_settings(self):
        """Ayarları içe aktar"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")]
        )
        if file_path:
            if self.config.import_config(file_path):
                self.load_settings()
                messagebox.showinfo(t("settings.saveSuccessTitle"), t("settings.importDone"))
