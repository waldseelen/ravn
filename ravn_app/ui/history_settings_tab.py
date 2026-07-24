"""Legacy-compatible shared History/Settings implementation module.

Canonical desktop imports should use ``ravn_app.ui.tabs.history_tab`` and
``ravn_app.ui.tabs.settings_tab``. This file remains as a shared implementation
module while Phase 5 clarifies feature ownership without risky UI rewrites.
"""

import threading
import unicodedata
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from ravn_app import __version__
from ravn_app.core import tool_installer
from ravn_app.core.download_naming import normalize_naming_preset
from ravn_app.core.i18n import t
from ravn_app.core.tool_health import get_tool_health_checker
from ravn_app.core.update_manager import UpdateManager
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import Tooltip, style_combo, style_entry

from ..core.database import ConfigManager, DatabaseManager
from .advanced_features import SearchFilter, ThemeManager


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
        import subprocess

        # subprocess with an argument LIST (never a shell string) so a maliciously-named
        # file path can't inject shell commands — os.system(f'open "{path}"') was exploitable.
        if platform.system() == 'Windows':
            os.startfile(file_path)  # noqa: S606 - Windows-native, not a shell
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(["open", file_path], check=False)
        else:  # Linux
            subprocess.run(["xdg-open", file_path], check=False)

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

    @staticmethod
    def _naming_preset_options() -> dict[str, str]:
        return {
            "standard": t("settings.namingPresetStandard"),
            "clean": t("settings.namingPresetClean"),
            "playlist": t("settings.namingPresetPlaylist"),
        }

    @classmethod
    def _naming_preset_for_display(cls, value: str) -> str:
        options = cls._naming_preset_options()
        return options.get(normalize_naming_preset(value), options["standard"])

    @classmethod
    def _normalize_naming_preset_for_storage(cls, value: str) -> str:
        options = cls._naming_preset_options()
        reverse_options = {label.lower(): preset for preset, label in options.items()}
        normalized_value = str(value or "").strip().lower()
        return normalize_naming_preset(reverse_options.get(normalized_value, normalized_value))

    @staticmethod
    def _postprocess_audio_format_options() -> list[str]:
        return ["MP3", "M4A", "AAC", "FLAC", "OPUS", "WAV"]

    @staticmethod
    def _postprocess_convert_format_options() -> list[str]:
        return ["MP4", "MKV", "WebM", "MP3", "M4A", "AAC", "FLAC", "OPUS"]

    @staticmethod
    def _normalize_postprocess_format(value: str, *, default: str = "mp3") -> str:
        normalized = str(value or "").strip().lower()
        if normalized == "webm":
            return "webm"
        return normalized or default

    @staticmethod
    def _postprocess_format_for_display(value: str, *, default: str = "MP3") -> str:
        normalized = str(value or "").strip().lower()
        if normalized == "webm":
            return "WebM"
        return normalized.upper() if normalized else default

    @staticmethod
    def _download_cookie_mode_options() -> dict[str, str]:
        return {
            "none": t("settings.downloadAdvancedCookiesNone"),
            "browser": t("settings.downloadAdvancedCookiesBrowser"),
            "file": t("settings.downloadAdvancedCookiesFile"),
        }

    @staticmethod
    def _download_cookie_browser_options() -> list[str]:
        return ["chrome", "firefox", "edge", "safari", "brave", "chromium", "opera"]

    @classmethod
    def _download_cookie_mode_for_display(cls, value: str) -> str:
        options = cls._download_cookie_mode_options()
        return options.get(str(value or "none").strip().lower(), options["none"])

    @classmethod
    def _normalize_download_cookie_mode_for_storage(cls, value: str) -> str:
        options = cls._download_cookie_mode_options()
        reverse_options = {label.lower(): key for key, label in options.items()}
        normalized_value = str(value or "none").strip().lower()
        return reverse_options.get(normalized_value, normalized_value or "none")

    @staticmethod
    def _safe_int(value, default: int = 0, *, minimum: int = 0) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, parsed)

    @staticmethod
    def _subtitle_fallback_options() -> dict[str, str]:
        return {
            "none": t("settings.noFallbackSubtitle"),
            "tr": "tr",
            "en": "en",
            "de": "de",
            "fr": "fr",
            "es": "es",
        }

    @classmethod
    def _subtitle_fallback_for_display(cls, value: str) -> str:
        options = cls._subtitle_fallback_options()
        normalized_value = str(value or "none").strip().lower()
        return options.get(normalized_value, options["none"])

    @classmethod
    def _normalize_subtitle_fallback_for_storage(cls, value: str) -> str:
        options = cls._subtitle_fallback_options()
        reverse_options = {label.lower(): key for key, label in options.items()}
        normalized_value = str(value or "").strip().lower()
        return reverse_options.get(normalized_value, normalized_value or "none")

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

    def _create_tool_health_section(self, parent):
        """Create tool health status section"""
        self.tool_health_section_frame = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE)
        self.tool_health_section_frame.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        health_frame = self.tool_health_section_frame

        # Header with refresh button
        header_frame = ctk.CTkFrame(health_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            header_frame,
            text=t("settings.toolHealthSection"),
            font=Fonts.H2
        ).pack(side="left", anchor="w")

        refresh_btn = ctk.CTkButton(
            header_frame,
            text=t("settings.toolHealthRefresh"),
            command=self._refresh_tool_health,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            width=120,
            cursor=Cursors.POINTER,
        )
        refresh_btn.pack(side="right")

        self.install_missing_tools_button = ctk.CTkButton(
            header_frame,
            text=t("settings.toolHealthInstallMissing"),
            command=self._install_missing_tools_clicked,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.BG_PRIMARY,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_SM,
            width=150,
            cursor=Cursors.POINTER,
        )
        self.install_missing_tools_button.pack(side="right", padx=(0, Spacing.XS))
        Tooltip(self.install_missing_tools_button, t("settings.toolHealthInstallTooltip"))

        # Overall status
        self.tool_health_status_label = ctk.CTkLabel(
            health_frame,
            text="",
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w"
        )
        self.tool_health_status_label.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        # Tool details frame
        self.tool_health_details_frame = ctk.CTkFrame(health_frame, fg_color="transparent")
        self.tool_health_details_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        # Load initial status
        self._refresh_tool_health()

    def _refresh_tool_health(self):
        """Refresh tool health status display"""
        # Clear existing details
        for widget in self.tool_health_details_frame.winfo_children():
            widget.destroy()
        help_frame = getattr(self, 'tool_health_help_frame', None)
        if help_frame is not None:
            help_frame.destroy()
            self.tool_health_help_frame = None

        # The health check spawns subprocess version probes for each tool; run them off the
        # UI thread so opening/refreshing Settings never freezes (previously ~1-2s, and up to
        # each tool's 5s timeout if a binary hangs).
        self.tool_health_status_label.configure(
            text=t("settings.toolHealthChecking"), text_color=Colors.TEXT_MUTED
        )

        def _worker():
            checker = get_tool_health_checker()
            checker.clear_cache()  # Force fresh check
            summary = checker.get_health_summary()
            self.after(0, lambda: self._render_tool_health(summary))

        threading.Thread(target=_worker, daemon=True).start()

    def _render_tool_health(self, summary) -> None:
        """Render the tool-health UI from a computed summary (runs on the main thread)."""
        if not self.winfo_exists():
            return

        # Clear any prior details/help (idempotent against back-to-back refreshes).
        for widget in self.tool_health_details_frame.winfo_children():
            widget.destroy()
        help_frame = getattr(self, 'tool_health_help_frame', None)
        if help_frame is not None:
            help_frame.destroy()
            self.tool_health_help_frame = None

        # Update overall status
        status_text = ""
        status_color = Colors.TEXT_PRIMARY

        if summary['overall_status'] == 'healthy':
            status_text = t("settings.toolHealthHealthy")
            status_color = Colors.SUCCESS
        elif summary['overall_status'] == 'degraded':
            status_text = t("settings.toolHealthDegraded")
            status_color = Colors.WARNING
        else:  # critical
            status_text = t("settings.toolHealthCritical")
            status_color = Colors.ERROR

        status_text += f" • {t('settings.toolHealthAvailable', count=summary['available_tools'], total=summary['total_tools'])}"
        self.tool_health_status_label.configure(text=status_text, text_color=status_color)

        missing_tools = summary['missing_required'] + summary['missing_optional']
        install_button = self.__dict__.get("install_missing_tools_button")
        if install_button is not None:
            install_button.configure(state="normal", text=t("settings.toolHealthInstallMissing"))
            if missing_tools and tool_installer.is_winget_available():
                if not install_button.winfo_manager():
                    install_button.pack(side="right", padx=(0, Spacing.XS))
            else:
                if install_button.winfo_manager():
                    install_button.pack_forget()

        # Display each tool
        for tool_name, tool_info in summary['tools'].items():
            tool_frame = ctk.CTkFrame(self.tool_health_details_frame, fg_color=Colors.BG_CARD)
            tool_frame.pack(fill="x", pady=2)

            # Tool name and status
            status_icon = "✅" if tool_info.status.value == "available" else "❌"
            required_label = t("settings.toolHealthRequired") if tool_info.required else t("settings.toolHealthOptional")

            name_label = ctk.CTkLabel(
                tool_frame,
                text=f"{status_icon} {tool_name} ({required_label})",
                font=Fonts.LABEL_BOLD,
                text_color=Colors.TEXT_PRIMARY,
                anchor="w"
            )
            name_label.pack(fill="x", padx=Spacing.XS, pady=(Spacing.XS, 0))

            # Version and path
            if tool_info.version:
                version_label = ctk.CTkLabel(
                    tool_frame,
                    text=t("settings.toolHealthVersion", version=tool_info.version),
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w"
                )
                version_label.pack(fill="x", padx=Spacing.XS)

            if tool_info.path:
                path_label = ctk.CTkLabel(
                    tool_frame,
                    text=t("settings.toolHealthPath", path=tool_info.path),
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w"
                )
                path_label.pack(fill="x", padx=Spacing.XS)
            elif tool_info.status.value == "missing":
                missing_label = ctk.CTkLabel(
                    tool_frame,
                    text=t("settings.toolHealthNoPath"),
                    font=Fonts.SMALL,
                    text_color=Colors.ERROR,
                    anchor="w"
                )
                missing_label.pack(fill="x", padx=Spacing.XS)

            # Affected features
            if tool_info.affected_features:
                features_text = ", ".join(tool_info.affected_features[:3])
                if len(tool_info.affected_features) > 3:
                    features_text += f" +{len(tool_info.affected_features) - 3} more"

                features_label = ctk.CTkLabel(
                    tool_frame,
                    text=t("settings.toolHealthAffectedFeatures", features=features_text),
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w",
                    wraplength=540
                )
                features_label.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        # Help messages for missing tools
        if summary['missing_required'] or summary['missing_optional']:
            self.tool_health_help_frame = ctk.CTkFrame(
                self.tool_health_section_frame,
                fg_color=Colors.BG_CARD,
                border_width=1,
                border_color=Colors.WARNING,
            )
            help_frame = self.tool_health_help_frame
            help_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.SM)

            if summary['missing_required']:
                required_text = t("settings.toolHealthMissingRequiredTools", tools=", ".join(summary['missing_required']))
                ctk.CTkLabel(
                    help_frame,
                    text=required_text,
                    font=Fonts.LABEL,
                    text_color=Colors.ERROR,
                    anchor="w",
                    wraplength=540
                ).pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

            if summary['missing_optional']:
                optional_text = t("settings.toolHealthMissingOptionalTools", tools=", ".join(summary['missing_optional']))
                ctk.CTkLabel(
                    help_frame,
                    text=optional_text,
                    font=Fonts.LABEL,
                    text_color=Colors.WARNING,
                    anchor="w",
                    wraplength=540
                ).pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

            # Installation help
            ctk.CTkLabel(
                help_frame,
                text=t("settings.toolHealthInstallHelp"),
                font=Fonts.SMALL,
                text_color=Colors.TEXT_MUTED,
                anchor="w",
                wraplength=540
            ).pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

    def _install_missing_tools_clicked(self) -> None:
        """Install every currently-missing tool via winget, in the background, then re-check."""
        checker = get_tool_health_checker()
        checker.clear_cache()
        summary = checker.get_health_summary()
        missing_tools = summary['missing_required'] + summary['missing_optional']

        if not missing_tools:
            return

        if not tool_installer.is_winget_available():
            messagebox.showerror(
                t("settings.toolHealthInstallTitle"),
                t("settings.toolHealthInstallNoWinget"),
            )
            return

        self.install_missing_tools_button.configure(
            state="disabled",
            text=t("settings.toolHealthInstalling"),
        )
        self.tool_health_status_label.configure(text=t("settings.toolHealthInstalling"))

        def _worker() -> None:
            results = tool_installer.install_missing_tools(missing_tools)
            self.after(0, lambda: self._on_install_missing_tools_done(results))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_install_missing_tools_done(self, results) -> None:
        if not self.winfo_exists():
            return

        failed_tools = [name for name, outcome in results.items() if not outcome.success]

        # Tool status refreshes immediately (in-process PATH was already merged
        # by install_missing_tools), no application restart required.
        self._refresh_tool_health()

        if failed_tools:
            messagebox.showwarning(
                t("settings.toolHealthInstallTitle"),
                t("settings.toolHealthInstallPartial", tools=", ".join(failed_tools)),
            )
        else:
            messagebox.showinfo(
                t("settings.toolHealthInstallTitle"),
                t("settings.toolHealthInstallDone"),
            )

    def create_general_settings(self, parent):
        """Genel ayarlar"""
        # Tool Health Status
        self._create_tool_health_section(parent)

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

        self.crash_reporting_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            notification_frame,
            text=t("settings.crashReportingEnabled"),
            variable=self.crash_reporting_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        # Manual Update Check
        update_btn_frame = ctk.CTkFrame(notification_frame, fg_color="transparent")
        update_btn_frame.pack(fill="x", padx=Spacing.XS, pady=Spacing.SM)

        self.check_updates_btn = ctk.CTkButton(
            update_btn_frame,
            text=t("settings.checkUpdatesBtn"),
            command=self._on_check_updates_clicked,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            cursor=Cursors.POINTER,
        )
        self.check_updates_btn.pack(side="left", padx=(0, Spacing.SM))

        self.update_status_label = ctk.CTkLabel(
            update_btn_frame,
            text="",
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
        )
        self.update_status_label.pack(side="left", padx=Spacing.XS)

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

        subtitle_languages = ["tr", "en", "de", "fr", "es"]

        ctk.CTkLabel(subtitle_frame, text=t("settings.preferredSubtitle"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)
        self.subtitle_lang_combo = ctk.CTkComboBox(
            subtitle_frame,
            values=subtitle_languages
        )
        style_combo(self.subtitle_lang_combo)
        self.subtitle_lang_combo.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(subtitle_frame, text=t("settings.subtitleFallback"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))
        self.subtitle_fallback_combo = ctk.CTkComboBox(
            subtitle_frame,
            values=list(self._subtitle_fallback_options().values())
        )
        style_combo(self.subtitle_fallback_combo)
        self.subtitle_fallback_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        self.subtitle_auto_generated_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            subtitle_frame,
            text=t("settings.subtitleIncludeAutoGenerated"),
            variable=self.subtitle_auto_generated_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.auto_embed_subtitles_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            subtitle_frame,
            text=t("settings.autoEmbedSubtitles"),
            variable=self.auto_embed_subtitles_var,
            font=Fonts.LABEL
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

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

        ctk.CTkLabel(metadata_frame, text=t("settings.namingPreset"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))
        self.naming_preset_combo = ctk.CTkComboBox(
            metadata_frame,
            values=list(self._naming_preset_options().values()),
        )
        style_combo(self.naming_preset_combo)
        self.naming_preset_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(metadata_frame, text=t("settings.filenameTemplate"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))
        self.filename_template_entry = ctk.CTkEntry(
            metadata_frame,
            placeholder_text=t("settings.filenameTemplatePlaceholder"),
        )
        style_entry(self.filename_template_entry)
        self.filename_template_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(
            metadata_frame,
            text=t("settings.filenameTemplateHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(metadata_frame, text=t("settings.postProcessSection"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))

        self.postprocess_extract_audio_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.postProcessExtractAudio"),
            variable=self.postprocess_extract_audio_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(metadata_frame, text=t("settings.postProcessAudioFormat"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.postprocess_audio_format_combo = ctk.CTkComboBox(
            metadata_frame,
            values=self._postprocess_audio_format_options(),
        )
        style_combo(self.postprocess_audio_format_combo)
        self.postprocess_audio_format_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(metadata_frame, text=t("settings.postProcessAudioBitrate"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.postprocess_audio_bitrate_combo = ctk.CTkComboBox(
            metadata_frame,
            values=["128k", "192k", "320k"],
        )
        style_combo(self.postprocess_audio_bitrate_combo)
        self.postprocess_audio_bitrate_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        self.postprocess_convert_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.postProcessConvert"),
            variable=self.postprocess_convert_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(metadata_frame, text=t("settings.postProcessConvertFormat"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.postprocess_convert_format_combo = ctk.CTkComboBox(
            metadata_frame,
            values=self._postprocess_convert_format_options(),
        )
        style_combo(self.postprocess_convert_format_combo)
        self.postprocess_convert_format_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        self.postprocess_embed_subtitles_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.postProcessEmbedSubtitles"),
            variable=self.postprocess_embed_subtitles_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(
            metadata_frame,
            text=t("settings.postProcessHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(metadata_frame, text=t("settings.downloadReliabilitySection"), font=Fonts.H2).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))

        self.download_archive_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.downloadArchive"),
            variable=self.download_archive_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.download_duplicate_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.downloadDuplicateDetection"),
            variable=self.download_duplicate_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.download_continue_partial_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.downloadContinuePartial"),
            variable=self.download_continue_partial_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        self.download_format_fallback_var = ctk.BooleanVar()
        ctk.CTkCheckBox(
            metadata_frame,
            text=t("settings.downloadFormatFallback"),
            variable=self.download_format_fallback_var,
            font=Fonts.LABEL,
        ).pack(anchor="w", padx=Spacing.XS, pady=Spacing.XS)

        ctk.CTkLabel(metadata_frame, text=t("settings.downloadRateLimit"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.SM, Spacing.XS))
        self.download_rate_limit_entry = ctk.CTkEntry(
            metadata_frame,
            placeholder_text=t("settings.downloadRateLimitPlaceholder"),
        )
        style_entry(self.download_rate_limit_entry)
        self.download_rate_limit_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(
            metadata_frame,
            text=t("settings.downloadReliabilityHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        advanced_panel = CollapsiblePanel(
            parent,
            title=t("settings.downloadAdvancedSection"),
            subtitle=t("settings.downloadAdvancedHelp"),
            expanded=False,
        )
        advanced_panel.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)
        advanced_body = advanced_panel.content_frame()

        auth_frame = ctk.CTkFrame(advanced_body, fg_color="transparent")
        auth_frame.pack(fill="x")
        ctk.CTkLabel(auth_frame, text=t("settings.downloadAdvancedAuthSection"), font=Fonts.LABEL_BOLD).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(auth_frame, text=t("settings.downloadAdvancedCookiesMode"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_cookie_mode_combo = ctk.CTkComboBox(
            auth_frame,
            values=list(self._download_cookie_mode_options().values()),
            command=lambda _value: self._update_download_advanced_controls_state(),
        )
        style_combo(self.download_cookie_mode_combo)
        self.download_cookie_mode_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(auth_frame, text=t("settings.downloadAdvancedCookiesBrowserLabel"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_cookie_browser_combo = ctk.CTkComboBox(
            auth_frame,
            values=self._download_cookie_browser_options(),
        )
        style_combo(self.download_cookie_browser_combo)
        self.download_cookie_browser_combo.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(auth_frame, text=t("settings.downloadAdvancedCookiesProfileLabel"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_cookie_profile_entry = ctk.CTkEntry(
            auth_frame,
            placeholder_text=t("settings.downloadAdvancedCookiesProfilePlaceholder"),
        )
        style_entry(self.download_cookie_profile_entry)
        self.download_cookie_profile_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(auth_frame, text=t("settings.downloadAdvancedCookiesFileLabel"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        cookie_file_row = ctk.CTkFrame(auth_frame, fg_color="transparent")
        cookie_file_row.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))
        self.download_cookie_file_entry = ctk.CTkEntry(
            cookie_file_row,
            placeholder_text=t("settings.downloadAdvancedCookiesFilePlaceholder"),
        )
        style_entry(self.download_cookie_file_entry)
        self.download_cookie_file_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))
        ctk.CTkButton(
            cookie_file_row,
            text=t("common.browse"),
            width=80,
            command=self.select_cookies_file,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.LABEL,
        ).pack(side="right")

        ctk.CTkLabel(
            auth_frame,
            text=t("settings.downloadAdvancedAuthHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        tuning_frame = ctk.CTkFrame(advanced_body, fg_color="transparent")
        tuning_frame.pack(fill="x", pady=(Spacing.SM, 0))
        ctk.CTkLabel(tuning_frame, text=t("settings.downloadAdvancedTuningSection"), font=Fonts.LABEL_BOLD).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(tuning_frame, text=t("settings.downloadAdvancedConcurrentFragments"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_concurrent_fragments_entry = ctk.CTkEntry(
            tuning_frame,
            placeholder_text="1",
        )
        style_entry(self.download_concurrent_fragments_entry)
        self.download_concurrent_fragments_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(tuning_frame, text=t("settings.downloadAdvancedFragmentRetries"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_fragment_retries_entry = ctk.CTkEntry(
            tuning_frame,
            placeholder_text="10",
        )
        style_entry(self.download_fragment_retries_entry)
        self.download_fragment_retries_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(tuning_frame, text=t("settings.downloadAdvancedSocketTimeout"), font=Fonts.LABEL).pack(anchor="w", padx=Spacing.XS, pady=(Spacing.XS, 0))
        self.download_socket_timeout_entry = ctk.CTkEntry(
            tuning_frame,
            placeholder_text="30",
        )
        style_entry(self.download_socket_timeout_entry)
        self.download_socket_timeout_entry.pack(fill="x", padx=Spacing.XS, pady=(0, Spacing.XS))

        ctk.CTkLabel(
            tuning_frame,
            text=t("settings.downloadAdvancedTuningHelp"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=560,
        ).pack(anchor="w", padx=Spacing.XS, pady=(0, Spacing.XS))

        self._update_download_advanced_controls_state()

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

    def _update_download_advanced_controls_state(self):
        mode_combo = getattr(self, 'download_cookie_mode_combo', None)
        browser_combo = getattr(self, 'download_cookie_browser_combo', None)
        profile_entry = getattr(self, 'download_cookie_profile_entry', None)
        file_entry = getattr(self, 'download_cookie_file_entry', None)

        mode = self._normalize_download_cookie_mode_for_storage(mode_combo.get() if mode_combo is not None else 'none')
        browser_state = 'normal' if mode == 'browser' else 'disabled'
        file_state = 'normal' if mode == 'file' else 'disabled'

        for widget in (browser_combo, profile_entry):
            if widget is not None:
                try:
                    widget.configure(state=browser_state)
                except Exception:
                    pass
        if file_entry is not None:
            try:
                file_entry.configure(state=file_state)
            except Exception:
                pass

    def load_settings(self):
        """Ayarları yükle"""
        self.theme_combo.set(ThemeManager.get_theme_display_name(self.config.get('theme', 'dark')))
        self.language_combo.set("Türkçe" if self.config.get('language') == 'tr' else "English")
        self.notifications_var.set(self.config.get('notifications_enabled', True))
        self.auto_update_var.set(self.config.get('auto_update_check', True))
        if hasattr(self, 'crash_reporting_var'):
            self.crash_reporting_var.set(self.config.get('crash_reporting_enabled', True))

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
        subtitle_fallback_combo = getattr(self, 'subtitle_fallback_combo', None)
        subtitle_auto_generated_var = getattr(self, 'subtitle_auto_generated_var', None)
        auto_embed_subtitles_var = getattr(self, 'auto_embed_subtitles_var', None)
        if subtitle_fallback_combo is not None:
            subtitle_fallback_combo.set(self._subtitle_fallback_for_display(self.config.get('subtitle_fallback_language', 'en')))
        if subtitle_auto_generated_var is not None:
            subtitle_auto_generated_var.set(self.config.get('subtitle_include_auto_generated', True))
        if auto_embed_subtitles_var is not None:
            auto_embed_subtitles_var.set(self.config.get('auto_embed_subtitles', False))
        embed_metadata_var = getattr(self, 'embed_metadata_var', getattr(self, 'auto_id3_var', None))
        auto_sort_var = getattr(self, 'auto_sort_var', None)
        naming_preset_combo = getattr(self, 'naming_preset_combo', None)
        filename_template_entry = getattr(self, 'filename_template_entry', None)
        postprocess_extract_audio_var = getattr(self, 'postprocess_extract_audio_var', None)
        postprocess_audio_format_combo = getattr(self, 'postprocess_audio_format_combo', None)
        postprocess_audio_bitrate_combo = getattr(self, 'postprocess_audio_bitrate_combo', None)
        postprocess_convert_var = getattr(self, 'postprocess_convert_var', None)
        postprocess_convert_format_combo = getattr(self, 'postprocess_convert_format_combo', None)
        postprocess_embed_subtitles_var = getattr(self, 'postprocess_embed_subtitles_var', None)
        download_archive_var = getattr(self, 'download_archive_var', None)
        download_duplicate_var = getattr(self, 'download_duplicate_var', None)
        download_continue_partial_var = getattr(self, 'download_continue_partial_var', None)
        download_format_fallback_var = getattr(self, 'download_format_fallback_var', None)
        download_rate_limit_entry = getattr(self, 'download_rate_limit_entry', None)
        download_cookie_mode_combo = getattr(self, 'download_cookie_mode_combo', None)
        download_cookie_browser_combo = getattr(self, 'download_cookie_browser_combo', None)
        download_cookie_profile_entry = getattr(self, 'download_cookie_profile_entry', None)
        download_cookie_file_entry = getattr(self, 'download_cookie_file_entry', None)
        download_concurrent_fragments_entry = getattr(self, 'download_concurrent_fragments_entry', None)
        download_fragment_retries_entry = getattr(self, 'download_fragment_retries_entry', None)
        download_socket_timeout_entry = getattr(self, 'download_socket_timeout_entry', None)
        postprocess_section = self.config.get('download_postprocess', {}) or {}
        robustness_section = self.config.get('download_robustness', {}) or {}
        advanced_section = self.config.get('download_advanced', {}) or {}
        if embed_metadata_var is not None:
            embed_metadata_var.set(self.config.get('embed_metadata', False))
        if auto_sort_var is not None:
            auto_sort_var.set(self.config.get('auto_sort_downloads', self.config.get('auto_sort_by_channel', False)))
        if naming_preset_combo is not None:
            naming_preset_combo.set(self._naming_preset_for_display(self.config.get('download_naming_preset', 'standard')))
        if filename_template_entry is not None:
            filename_template_entry.insert(0, self.config.get('download_filename_template', ''))
        if postprocess_extract_audio_var is not None:
            postprocess_extract_audio_var.set(bool(postprocess_section.get('extract_audio', False)))
        if postprocess_audio_format_combo is not None:
            postprocess_audio_format_combo.set(self._postprocess_format_for_display(postprocess_section.get('audio_format', 'mp3'), default='MP3'))
        if postprocess_audio_bitrate_combo is not None:
            postprocess_audio_bitrate_combo.set(str(postprocess_section.get('audio_bitrate', '192k') or '192k'))
        if postprocess_convert_var is not None:
            postprocess_convert_var.set(bool(postprocess_section.get('convert_enabled', False)))
        if postprocess_convert_format_combo is not None:
            postprocess_convert_format_combo.set(self._postprocess_format_for_display(postprocess_section.get('convert_format', 'mkv'), default='MKV'))
        if postprocess_embed_subtitles_var is not None:
            postprocess_embed_subtitles_var.set(bool(postprocess_section.get('embed_subtitles', False)))
        if download_archive_var is not None:
            download_archive_var.set(bool(robustness_section.get('enable_archive', True)))
        if download_duplicate_var is not None:
            download_duplicate_var.set(bool(robustness_section.get('detect_duplicates', True)))
        if download_continue_partial_var is not None:
            download_continue_partial_var.set(bool(robustness_section.get('continue_partial', True)))
        if download_format_fallback_var is not None:
            download_format_fallback_var.set(bool(robustness_section.get('format_fallback', True)))
        if download_rate_limit_entry is not None:
            download_rate_limit_entry.insert(0, str(robustness_section.get('rate_limit_kbps', 0) or 0))
        if download_cookie_mode_combo is not None:
            download_cookie_mode_combo.set(self._download_cookie_mode_for_display(advanced_section.get('cookies_mode', 'none')))
        if download_cookie_browser_combo is not None:
            download_cookie_browser_combo.set(str(advanced_section.get('cookies_browser', 'chrome') or 'chrome'))
        if download_cookie_profile_entry is not None:
            download_cookie_profile_entry.insert(0, str(advanced_section.get('cookies_profile', '') or ''))
        if download_cookie_file_entry is not None:
            download_cookie_file_entry.insert(0, str(advanced_section.get('cookies_file', '') or ''))
        if download_concurrent_fragments_entry is not None:
            download_concurrent_fragments_entry.insert(0, str(advanced_section.get('concurrent_fragments', 1) or 1))
        if download_fragment_retries_entry is not None:
            download_fragment_retries_entry.insert(0, str(advanced_section.get('fragment_retries', 0) or 0))
        if download_socket_timeout_entry is not None:
            download_socket_timeout_entry.insert(0, str(advanced_section.get('socket_timeout_seconds', 0) or 0))
        self._update_download_advanced_controls_state()

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
        if hasattr(self, 'crash_reporting_var'):
            self.config.set('crash_reporting_enabled', self.crash_reporting_var.get())

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
        subtitle_fallback_combo = getattr(self, 'subtitle_fallback_combo', None)
        subtitle_auto_generated_var = getattr(self, 'subtitle_auto_generated_var', None)
        auto_embed_subtitles_var = getattr(self, 'auto_embed_subtitles_var', None)
        if subtitle_fallback_combo is not None:
            self.config.set('subtitle_fallback_language', self._normalize_subtitle_fallback_for_storage(subtitle_fallback_combo.get()))
        if subtitle_auto_generated_var is not None:
            self.config.set('subtitle_include_auto_generated', subtitle_auto_generated_var.get())
        if auto_embed_subtitles_var is not None:
            self.config.set('auto_embed_subtitles', auto_embed_subtitles_var.get())
        self.config.set('close_to_tray', self.close_behavior_combo.get() == t("settings.closeToTray"))
        embed_metadata_var = getattr(self, 'embed_metadata_var', getattr(self, 'auto_id3_var', None))
        auto_sort_var = getattr(self, 'auto_sort_var', None)
        auto_sort_mode_combo = getattr(self, 'auto_sort_mode_combo', None)
        auto_lyrics_var = getattr(self, 'auto_lyrics_var', None)
        naming_preset_combo = getattr(self, 'naming_preset_combo', None)
        filename_template_entry = getattr(self, 'filename_template_entry', None)
        postprocess_extract_audio_var = getattr(self, 'postprocess_extract_audio_var', None)
        postprocess_audio_format_combo = getattr(self, 'postprocess_audio_format_combo', None)
        postprocess_audio_bitrate_combo = getattr(self, 'postprocess_audio_bitrate_combo', None)
        postprocess_convert_var = getattr(self, 'postprocess_convert_var', None)
        postprocess_convert_format_combo = getattr(self, 'postprocess_convert_format_combo', None)
        postprocess_embed_subtitles_var = getattr(self, 'postprocess_embed_subtitles_var', None)
        download_archive_var = getattr(self, 'download_archive_var', None)
        download_duplicate_var = getattr(self, 'download_duplicate_var', None)
        download_continue_partial_var = getattr(self, 'download_continue_partial_var', None)
        download_format_fallback_var = getattr(self, 'download_format_fallback_var', None)
        download_rate_limit_entry = getattr(self, 'download_rate_limit_entry', None)
        download_cookie_mode_combo = getattr(self, 'download_cookie_mode_combo', None)
        download_cookie_browser_combo = getattr(self, 'download_cookie_browser_combo', None)
        download_cookie_profile_entry = getattr(self, 'download_cookie_profile_entry', None)
        download_cookie_file_entry = getattr(self, 'download_cookie_file_entry', None)
        download_concurrent_fragments_entry = getattr(self, 'download_concurrent_fragments_entry', None)
        download_fragment_retries_entry = getattr(self, 'download_fragment_retries_entry', None)
        download_socket_timeout_entry = getattr(self, 'download_socket_timeout_entry', None)

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
        if naming_preset_combo is not None:
            self.config.set('download_naming_preset', self._normalize_naming_preset_for_storage(naming_preset_combo.get()))
        if filename_template_entry is not None:
            self.config.set('download_filename_template', filename_template_entry.get().strip())

        postprocess_payload = {
            'extract_audio': bool(postprocess_extract_audio_var.get()) if postprocess_extract_audio_var is not None else False,
            'audio_format': self._normalize_postprocess_format(
                postprocess_audio_format_combo.get() if postprocess_audio_format_combo is not None else 'MP3',
                default='mp3',
            ),
            'audio_bitrate': str(
                postprocess_audio_bitrate_combo.get()
                if postprocess_audio_bitrate_combo is not None
                else '192k'
            ).strip().lower(),
            'convert_enabled': bool(postprocess_convert_var.get()) if postprocess_convert_var is not None else False,
            'convert_format': self._normalize_postprocess_format(
                postprocess_convert_format_combo.get() if postprocess_convert_format_combo is not None else 'MKV',
                default='mkv',
            ),
            'embed_subtitles': bool(postprocess_embed_subtitles_var.get()) if postprocess_embed_subtitles_var is not None else False,
        }
        self.config.set('download_postprocess', postprocess_payload)

        try:
            rate_limit_kbps = int(download_rate_limit_entry.get()) if download_rate_limit_entry is not None else 0
        except ValueError:
            rate_limit_kbps = 0
        self.config.set(
            'download_robustness',
            {
                'enable_archive': bool(download_archive_var.get()) if download_archive_var is not None else True,
                'detect_duplicates': bool(download_duplicate_var.get()) if download_duplicate_var is not None else True,
                'continue_partial': bool(download_continue_partial_var.get()) if download_continue_partial_var is not None else True,
                'format_fallback': bool(download_format_fallback_var.get()) if download_format_fallback_var is not None else True,
                'rate_limit_kbps': max(0, rate_limit_kbps),
            },
        )
        self.config.set(
            'download_advanced',
            {
                'cookies_mode': self._normalize_download_cookie_mode_for_storage(
                    download_cookie_mode_combo.get() if download_cookie_mode_combo is not None else 'none'
                ),
                'cookies_browser': str(
                    download_cookie_browser_combo.get() if download_cookie_browser_combo is not None else 'chrome'
                ).strip().lower() or 'chrome',
                'cookies_profile': str(
                    download_cookie_profile_entry.get() if download_cookie_profile_entry is not None else ''
                ).strip(),
                'cookies_file': str(
                    download_cookie_file_entry.get() if download_cookie_file_entry is not None else ''
                ).strip(),
                'concurrent_fragments': self._safe_int(
                    download_concurrent_fragments_entry.get() if download_concurrent_fragments_entry is not None else 1,
                    1,
                    minimum=1,
                ),
                'fragment_retries': self._safe_int(
                    download_fragment_retries_entry.get() if download_fragment_retries_entry is not None else 0,
                    0,
                    minimum=0,
                ),
                'socket_timeout_seconds': self._safe_int(
                    download_socket_timeout_entry.get() if download_socket_timeout_entry is not None else 0,
                    0,
                    minimum=0,
                ),
            },
        )

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

    def _on_check_updates_clicked(self):
        """Manual trigger for checking GitHub Releases for updates."""
        check_btn = getattr(self, 'check_updates_btn', None)
        status_lbl = getattr(self, 'update_status_label', None)
        if check_btn is not None:
            check_btn.configure(state="disabled")
        if status_lbl is not None:
            status_lbl.configure(
                text=t("settings.checkingForUpdates"), text_color=Colors.TEXT_MUTED
            )

        def worker():
            try:
                mgr = UpdateManager(
                    current_version=__version__,
                    github_owner="waldseelen",
                    github_repo="ravn",
                )
                is_update_available = mgr.check_for_updates()
                if is_update_available:
                    latest = mgr.get_latest_release()
                    version_str = latest.version if latest is not None else "?"
                    msg = t("settings.updateAvailable").format(version=version_str)
                    color = Colors.ACCENT
                else:
                    msg = t("settings.upToDate").format(version=__version__)
                    color = Colors.TEXT_MUTED
            except Exception:
                msg = t("settings.updateCheckFailed")
                color = Colors.TEXT_MUTED

            def update_ui():
                if status_lbl is not None:
                    status_lbl.configure(text=msg, text_color=color)
                if check_btn is not None:
                    check_btn.configure(state="normal")

            self.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()

    def select_download_dir(self):
        """İndirme dizini seç"""
        dir_path = filedialog.askdirectory()
        if dir_path:
            self.download_dir_entry.delete(0, "end")
            self.download_dir_entry.insert(0, dir_path)

    def select_cookies_file(self):
        """cookies.txt dosyası seç"""
        file_path = filedialog.askopenfilename(
            filetypes=[("Cookie files", "*.txt *.cookies"), ("All files", "*.*")]
        )
        if file_path and getattr(self, 'download_cookie_file_entry', None) is not None:
            self.download_cookie_file_entry.delete(0, "end")
            self.download_cookie_file_entry.insert(0, file_path)

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
