"""Main desktop shell for the RAVN application."""

import ctypes
import platform
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any, Optional

import customtkinter as ctk

from ravn_app.core.animation_manager import get_animation_manager
from ravn_app.core.database import ConfigManager, DatabaseManager
from ravn_app.core.downloader import YouTubeDownloader
from ravn_app.core.i18n import get_i18n, t
from ravn_app.core.logging_config import get_logger
from ravn_app.core.persistence import MediaLibraryAutoAdder
from ravn_app.core.platform_support import PlatformManager
from ravn_app.core.task_manager import get_task_queue
from ravn_app.ui.advanced_features import NotificationManager, SystemTrayIntegration, ThemeManager
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.components.command_palette import CommandPaletteDialog, PaletteCommand
from ravn_app.ui.tabs.download_workspace import DownloadWorkspace
from ravn_app.ui.tabs.home_workspace import HomeWorkspace
from ravn_app.ui.tabs.library_workspace import LibraryWorkspace
from ravn_app.ui.tabs.queue_tab import QueueTab
from ravn_app.ui.tabs.settings_tab import SettingsTab
from ravn_app.ui.tabs.studio_workspace import StudioWorkspace
from ravn_app.ui.ui_components import ToastManager, Tooltip


logger = get_logger(__name__)


class YouTubeDownloaderApp(ctk.CTk):
    """Main desktop shell with sidebar workspaces and a queue utility drawer."""

    PRIMARY_VIEWS = ("home", "download", "studio", "library")
    AUXILIARY_VIEWS = ("settings",)
    DRAWER_VIEWS = ("queue",)

    def __init__(self):
        super().__init__()
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.withdraw()

        self.title(t("common.appTitle"))
        self.geometry("1360x840")
        self.minsize(1080, 720)
        self._apply_window_icon()

        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.i18n = get_i18n(self.config_manager)
        self.platform_manager = PlatformManager()
        self.downloader = YouTubeDownloader(
            ffmpeg_path=self.config_manager.get("ffmpeg_path", "ffmpeg"),
        )
        self.task_queue = get_task_queue()
        self.queue_paused = False
        self.animation_manager = get_animation_manager()
        self.media_library_auto_adder = MediaLibraryAutoAdder(
            config_manager=self.config_manager,
            ffmpeg_path=self.config_manager.get("ffmpeg_path", "ffmpeg"),
        )

        self.current_theme = self.config_manager.get("theme", "dark")
        ThemeManager.apply_theme(self.current_theme)
        self.toast_manager: Optional[ToastManager] = None
        self.download_tab = None
        self.torrent_tab = None
        self.converter_tab = None
        self.subtitle_tab = None
        self.mixer_tab = None
        self.library_tab = None
        self.filters_tab = None
        self.history_tab = None
        self.settings_tab = None
        self.queue_tab = None
        self.home_workspace = None
        self.download_workspace = None
        self.studio_workspace = None
        self.library_workspace = None
        self._task_callback_after_id = None
        self._ui_callback_queue: queue.Queue = queue.Queue()
        self._workspace_frames: dict[str, ctk.CTkFrame] = {}
        self._drawer_frames: dict[str, ctk.CTkFrame] = {}
        self._sidebar_buttons: dict[str, ctk.CTkButton] = {}
        self._sidebar_button_labels: dict[str, str] = {}
        self._quick_action_buttons: dict[str, ctk.CTkButton] = {}
        self._current_view_key: Optional[str] = None
        self._last_primary_view_key = "home"
        self._active_drawer_key: Optional[str] = None
        self._drawer_return_focus = None
        self._last_task_snapshot = self.task_queue.get_ui_snapshot()
        self._command_palette = None
        self.tray = None

        self._setup_ui()
        self.after(10, self._show_centered_initial_window)
        self._setup_global_shortcuts()
        self.toast_manager = ToastManager(self)
        self._setup_tray_integration()
        self._schedule_task_queue_callback_pump()
        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def __del__(self):
        db_manager = self.__dict__.get("db_manager")
        if db_manager:
            db_manager.close()

    def _apply_window_icon(self) -> None:
        """Set window icon from assets/ravn.ico (Windows) or ravn-icon-256.png."""
        assets = Path(__file__).parent.parent.parent / "assets"
        try:
            if platform.system() == "Windows":
                ico = assets / "ravn.ico"
                if ico.exists():
                    self.iconbitmap(str(ico))
                    return
            png = assets / "ravn-icon-256.png"
            if png.exists():
                from PIL import Image, ImageTk

                img = Image.open(png)
                photo = ImageTk.PhotoImage(img)
                self.iconphoto(True, photo)
                self._icon_ref = photo
        except Exception:
            pass

    def _setup_ui(self, initial_view: Optional[str] = None, initial_drawer: Optional[str] = None):
        for child in list(self.winfo_children()):
            child.destroy()

        self.bind("<Configure>", self._on_window_resize)
        self._workspace_frames = {}
        self._drawer_frames = {}
        self._sidebar_buttons = {}
        self._sidebar_button_labels = {}
        self._quick_action_buttons = {}
        self._current_view_key = None
        self._active_drawer_key = None
        self._sidebar_expanded = True

        shell = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        shell.pack(fill="both", expand=True)

        self.sidebar = ctk.CTkFrame(shell, fg_color=Colors.BG_SURFACE, width=230, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content_shell = ctk.CTkFrame(shell, fg_color=Colors.BG_PRIMARY)
        self.content_shell.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._build_header()
        self._build_main_stage()
        self._build_footer()

        target_view = initial_view if initial_view in (self.PRIMARY_VIEWS + self.AUXILIARY_VIEWS) else self._last_primary_view_key
        if target_view not in (self.PRIMARY_VIEWS + self.AUXILIARY_VIEWS):
            target_view = "home"
        self._show_view(target_view)

        self._apply_responsive_shell_state(self.winfo_width() or 1400)

        if initial_drawer in self.DRAWER_VIEWS:
            self._open_drawer(initial_drawer)
        else:
            self._refresh_header_actions()

    def _build_sidebar(self) -> None:
        brand = ctk.CTkFrame(self.sidebar, fg_color=Colors.BG_SURFACE)
        brand.pack(fill="x", padx=Spacing.MD, pady=(Spacing.LG, Spacing.LG))

        self.brand_heading_label = ctk.CTkLabel(
            brand,
            text=t("common.appHeading"),
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.brand_heading_label.pack(side="left")

        self.sidebar_toggle_button = ctk.CTkButton(
            brand,
            text="☰",
            width=30,
            command=self._toggle_sidebar,
            fg_color="transparent",
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.sidebar_toggle_button.pack(side="right")

        self.brand_subtitle_label = ctk.CTkLabel(
            brand,
            text=t("common.appSubtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.brand_subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        nav_frame = ctk.CTkFrame(self.sidebar, fg_color=Colors.BG_SURFACE)
        nav_frame.pack(fill="x", padx=Spacing.MD)

        self._create_sidebar_button(nav_frame, "home", f"{Icons.BROWSE}  {t('workspace.home')}")
        self._create_sidebar_button(nav_frame, "download", f"{Icons.DOWNLOAD}  {t('workspace.download')}")
        self._create_sidebar_button(nav_frame, "studio", f"{Icons.CONVERT}  {t('workspace.studio')}")
        self._create_sidebar_button(nav_frame, "library", f"{Icons.LIBRARY}  {t('workspace.library')}")

        helper = ctk.CTkFrame(self.sidebar, fg_color=Colors.BG_SURFACE)
        helper.pack(side="bottom", fill="x", padx=Spacing.MD, pady=Spacing.MD)

        toggle_row = ctk.CTkFrame(helper, fg_color=Colors.BG_SURFACE)
        toggle_row.pack(fill="x", pady=(0, Spacing.SM))

        self.theme_toggle_button = ctk.CTkButton(
            toggle_row,
            text="",
            command=self._toggle_theme,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL_BOLD,
            cursor=Cursors.POINTER,
        )
        self.theme_toggle_button.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))
        self._theme_toggle_tooltip = Tooltip(self.theme_toggle_button, "")

        self.language_toggle_button = ctk.CTkButton(
            toggle_row,
            text="",
            command=self._toggle_language,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL_BOLD,
            cursor=Cursors.POINTER,
        )
        self.language_toggle_button.pack(side="left", fill="x", expand=True, padx=(Spacing.XS, 0))
        self._language_toggle_tooltip = Tooltip(self.language_toggle_button, "")

        self._create_sidebar_button(helper, "settings", f"{Icons.SETTINGS}  {t('mainWindow.settingsAction')}")
        self._refresh_sidebar_utility_controls()

        self.sidebar_hint_label = ctk.CTkLabel(
            helper,
            text=t("mainWindow.sidebarHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            justify="left",
            wraplength=180,
        )
        self.sidebar_hint_label.pack(anchor="w", pady=(Spacing.XS, 0))

    def _create_sidebar_button(self, parent, view_key: str, text: str) -> None:
        self._sidebar_button_labels[view_key] = text
        icon = text.split("  ")[0] if "  " in text else ""
        self._sidebar_button_icons = getattr(self, "_sidebar_button_icons", {})
        self._sidebar_button_icons[view_key] = icon

        button = ctk.CTkButton(
            parent,
            text=text,
            command=lambda key=view_key: self.show_workspace(key),
            anchor="w",
            height=Sizes.BTN_HEIGHT_LG,
            fg_color="transparent",
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            border_width=0,
            border_color=Colors.BG_SURFACE,
            corner_radius=Sizes.CORNER_MD,
            cursor=Cursors.POINTER,
            font=Fonts.LABEL,
        )
        button.pack(fill="x", pady=(0, Spacing.SM))
        self._sidebar_buttons[view_key] = button

    def _toggle_sidebar(self) -> None:
        self._sidebar_expanded = not self._sidebar_expanded
        width = 230 if self._sidebar_expanded else 60
        self.sidebar.configure(width=width)
        
        if self._sidebar_expanded:
            self.brand_heading_label.pack(side="left")
            self.brand_subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))
            self.sidebar_hint_label.pack(anchor="w", pady=(Spacing.XS, 0))
        else:
            self.brand_heading_label.pack_forget()
            self.brand_subtitle_label.pack_forget()
            self.sidebar_hint_label.pack_forget()
            
        self._update_navigation_state()

    def _refresh_sidebar_utility_controls(self) -> None:
        theme_id = ThemeManager.normalize_theme_name(self.config_manager.get("theme", "dark"))
        language = str(self.config_manager.get("language", "tr") or "tr").strip().lower()
        if language not in {"tr", "en"}:
            language = "tr"

        theme_button = self.__dict__.get("theme_toggle_button")
        theme_tooltip = self.__dict__.get("_theme_toggle_tooltip")
        if theme_button is not None:
            theme_label = t("mainWindow.themeToggleDark") if theme_id == "dark" else t("mainWindow.themeToggleLight")
            theme_button.configure(text=theme_label)
            if theme_tooltip is not None:
                theme_tooltip.update_text(
                    t("mainWindow.themeToggleTooltipToLight") if theme_id == "dark" else t("mainWindow.themeToggleTooltipToDark")
                )

        language_button = self.__dict__.get("language_toggle_button")
        language_tooltip = self.__dict__.get("_language_toggle_tooltip")
        if language_button is not None:
            language_label = t("mainWindow.languageToggleTr") if language == "tr" else t("mainWindow.languageToggleEn")
            language_button.configure(text=language_label)
            if language_tooltip is not None:
                language_tooltip.update_text(
                    t("mainWindow.languageToggleTooltipToEn") if language == "tr" else t("mainWindow.languageToggleTooltipToTr")
                )

    def _toggle_theme(self) -> None:
        current_theme = ThemeManager.normalize_theme_name(self.config_manager.get("theme", "dark"))
        target_theme = "light" if current_theme == "dark" else "dark"
        self._apply_theme_preference(target_theme)

    def _toggle_language(self) -> None:
        current_language = str(self.config_manager.get("language", "tr") or "tr").strip().lower()
        target_language = "en" if current_language == "tr" else "tr"
        self._apply_language_preference(target_language)

    def _apply_theme_preference(self, theme_name: str) -> None:
        normalized_theme = ThemeManager.normalize_theme_name(theme_name)
        self.config_manager.set("theme", normalized_theme)
        self.current_theme = normalized_theme
        Tooltip.dismiss_all()

        # Pre-transition background stabilization to prevent white flash
        # Set root window background to target theme BG_PRIMARY before CTk mode switch
        target_bg = Colors.BG_PRIMARY[0] if normalized_theme == "light" else Colors.BG_PRIMARY[1]
        try:
            self.configure(bg=target_bg)  # Set Tk root background
            self.update_idletasks()  # Flush pending UI updates
        except Exception:
            pass

        ThemeManager.apply_theme(normalized_theme)

        # Brief delay to let CTk finish internal mode switch before refreshing widgets
        try:
            self.after(10, self._finish_theme_transition)
        except Exception:
            # Fallback for test environments where .after() may not work
            self._finish_theme_transition()

    def _finish_theme_transition(self) -> None:
        """Complete theme transition after CTk internal state stabilizes."""
        try:
            self._refresh_sidebar_utility_controls()
            self._refresh_header_actions()
        except Exception:
            pass

    def _apply_language_preference(self, language: str) -> None:
        normalized_language = "en" if str(language).strip().lower() == "en" else "tr"
        self.config_manager.set("language", normalized_language)
        manager = get_i18n(self.config_manager)
        manager.set_language(normalized_language, persist=False)
        self.i18n = manager
        Tooltip.dismiss_all()
        self.refresh_i18n()

    def _capture_shell_state(self) -> dict[str, Optional[str]]:
        state = {
            "view": self._current_view_key or self._last_primary_view_key,
            "drawer": self._active_drawer_key,
            "download_mode": None,
            "studio_view": None,
            "library_view": None,
        }
        download_workspace = self.__dict__.get("download_workspace")
        if download_workspace is not None:
            state["download_mode"] = getattr(download_workspace, "_active_mode_key", None)
        studio_workspace = self.__dict__.get("studio_workspace")
        if studio_workspace is not None:
            state["studio_view"] = getattr(studio_workspace, "_active_view_key", None)
        library_workspace = self.__dict__.get("library_workspace")
        if library_workspace is not None:
            state["library_view"] = getattr(library_workspace, "_active_view_key", None)
        return state

    def _restore_shell_state(self, state: dict[str, Optional[str]]) -> None:
        if state.get("view") == "download" and state.get("download_mode") and self.download_workspace is not None:
            self.download_workspace.select_mode(state["download_mode"])
        if state.get("view") == "studio" and state.get("studio_view") and self.studio_workspace is not None:
            self.studio_workspace.select_view(state["studio_view"])
        if state.get("view") == "library" and state.get("library_view") and self.library_workspace is not None:
            self.library_workspace.select_view(state["library_view"])

    def _rebuild_shell(self) -> None:
        Tooltip.dismiss_all()
        shell_state = self._capture_shell_state()
        palette = self.__dict__.get("_command_palette")
        if palette is not None:
            try:
                palette.close()
            except Exception:
                try:
                    palette.destroy()
                except Exception:
                    pass
            self._command_palette = None

        self.title(t("common.appTitle"))
        self._setup_ui(initial_view=shell_state.get("view"), initial_drawer=shell_state.get("drawer"))
        self._restore_shell_state(shell_state)

        tray = self.__dict__.get("tray")
        if tray is not None and getattr(tray, "available", False):
            tray.stop()
            self._setup_tray_integration()

    def _build_header(self) -> None:
        self.header = ctk.CTkFrame(self.content_shell, fg_color=Colors.BG_PRIMARY)
        self.header.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))

        header_left = ctk.CTkFrame(self.header, fg_color=Colors.BG_PRIMARY)
        header_left.pack(side="left", fill="x", expand=True)

        self.workspace_title_label = ctk.CTkLabel(
            header_left,
            text="",
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.workspace_title_label.pack(anchor="w")

        self.workspace_subtitle_label = ctk.CTkLabel(
            header_left,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.workspace_subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        actions = ctk.CTkFrame(self.header, fg_color=Colors.BG_PRIMARY)
        actions.pack(side="right")

        self.quick_actions_label = ctk.CTkLabel(
            actions,
            text=t("mainWindow.quickActionsLabel"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        )
        self.quick_actions_label.pack(side="left", padx=(0, Spacing.SM))

        quick_buttons = [
            ("paste", Icons.LINK_INPUT, t("mainWindow.quickPasteUrl"), self._quick_paste_url),
            ("torrent", Icons.TORRENT, t("mainWindow.quickAddTorrent"), lambda: self.show_download_view("torrent")),
            ("convert", Icons.CONVERT, t("mainWindow.quickConvertFile"), self._quick_convert_file),
            ("library", Icons.LIBRARY, t("mainWindow.quickOpenLibrary"), lambda: self.show_library_view("library")),
        ]
        for key, icon, label, command in quick_buttons:
            button = ctk.CTkButton(
                actions,
                text=f"{icon} {label}",
                command=command,
                height=Sizes.BTN_HEIGHT_LG,
                fg_color=Colors.BG_CARD,
                hover_color=Colors.BG_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                font=Fonts.SMALL,
                cursor=Cursors.POINTER,
            )
            button.pack(side="left", padx=(0, Spacing.XS))
            self._quick_action_buttons[key] = button

        self.command_palette_button = ctk.CTkButton(
            actions,
            text=f"{Icons.SEARCH} {t('mainWindow.commandPaletteAction')}",
            command=self.open_command_palette,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
        )
        self.command_palette_button.pack(side="left", padx=(Spacing.SM, Spacing.XS))
        self._command_palette_tooltip = Tooltip(self.command_palette_button, t("mainWindow.commandPaletteTooltip"))

        self.queue_action_button = ctk.CTkButton(
            actions,
            text="",
            command=self.show_queue_view,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL,
            cursor=Cursors.POINTER,
        )
        self.queue_action_button.pack(side="left")
        self._queue_action_tooltip = Tooltip(self.queue_action_button, t("mainWindow.queueTooltip"))

    def _build_main_stage(self) -> None:
        self.stage_frame = ctk.CTkFrame(self.content_shell, fg_color=Colors.BG_PRIMARY)
        self.stage_frame.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, 0))

        self.workspace_host = ctk.CTkFrame(self.stage_frame, fg_color=Colors.BG_PRIMARY)
        self.workspace_host.pack(side="left", fill="both", expand=True)
        self.workspace_host.grid_rowconfigure(0, weight=1)
        self.workspace_host.grid_columnconfigure(0, weight=1)

        self.drawer_shell = ctk.CTkFrame(
            self.stage_frame,
            fg_color=Colors.BG_SURFACE,
            width=380,
            corner_radius=Sizes.CORNER_MD,
            border_width=1,
            border_color=Colors.BORDER,
        )
        self.drawer_shell.pack_propagate(False)

        drawer_header = ctk.CTkFrame(self.drawer_shell, fg_color=Colors.BG_SURFACE)
        drawer_header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

        drawer_title_col = ctk.CTkFrame(drawer_header, fg_color=Colors.BG_SURFACE)
        drawer_title_col.pack(side="left", fill="x", expand=True)

        self.drawer_title_label = ctk.CTkLabel(
            drawer_title_col,
            text="",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.drawer_title_label.pack(anchor="w")

        self.drawer_subtitle_label = ctk.CTkLabel(
            drawer_title_col,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.drawer_subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.drawer_close_button = ctk.CTkButton(
            drawer_header,
            text=Icons.CLOSE,
            command=self._close_drawer,
            width=48,
            height=48,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.drawer_close_button.pack(side="right")

        self.drawer_content_host = ctk.CTkFrame(self.drawer_shell, fg_color=Colors.BG_SURFACE)
        self.drawer_content_host.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))

        self.home_workspace = HomeWorkspace(
            self.workspace_host,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            open_download_view=self.show_download_view,
            open_studio_view=self.show_studio_view,
            open_library_view=self.show_library_view,
            open_queue_view=self.show_queue_view,
            fg_color=Colors.BG_PRIMARY,
        )
        self.home_workspace.grid(row=0, column=0, sticky="nsew")
        self._workspace_frames["home"] = self.home_workspace

        self.download_workspace = DownloadWorkspace(
            self.workspace_host,
            downloader=self.downloader,
            config_manager=self.config_manager,
            platform_manager=self.platform_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            queue_paused_getter=lambda: self.queue_paused,
            show_queue_callback=self.show_queue_view,
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color=Colors.BG_PRIMARY,
        )
        self.download_workspace.grid(row=0, column=0, sticky="nsew")
        self.download_tab = self.download_workspace.download_tab
        self.torrent_tab = self.download_workspace.torrent_tab
        self._workspace_frames["download"] = self.download_workspace

        self.studio_workspace = StudioWorkspace(
            self.workspace_host,
            config_manager=self.config_manager,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            show_queue_callback=self.show_queue_view,
            notify_conversion_complete=self._notify_conversion_complete,
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color=Colors.BG_PRIMARY,
        )
        self.studio_workspace.grid(row=0, column=0, sticky="nsew")
        self.converter_tab = self.studio_workspace.converter_tab
        self.subtitle_tab = self.studio_workspace.subtitle_tab
        self.filters_tab = self.studio_workspace.filters_tab
        self.mixer_tab = self.studio_workspace.mixer_tab
        self._workspace_frames["studio"] = self.studio_workspace

        self.library_workspace = LibraryWorkspace(
            self.workspace_host,
            config_manager=self.config_manager,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            show_queue_callback=self.show_queue_view,
            fg_color=Colors.BG_PRIMARY,
        )
        self.library_workspace.grid(row=0, column=0, sticky="nsew")
        self.library_tab = self.library_workspace.library_tab
        self.history_tab = self.library_workspace.history_tab
        self._workspace_frames["library"] = self.library_workspace

        self.queue_tab = QueueTab(
            self.drawer_content_host,
            on_cancel_task=self._cancel_queue_task,
            on_open_folder=self._open_output_folder,
            fg_color=Colors.BG_SURFACE,
        )
        self._drawer_frames["queue"] = self.queue_tab

        settings_page = ctk.CTkFrame(self.workspace_host, fg_color=Colors.BG_PRIMARY)
        self.settings_tab = SettingsTab(
            settings_page,
            self.config_manager,
            on_language_changed=self.refresh_i18n,
            fg_color=Colors.BG_PRIMARY,
        )
        self.settings_tab.pack(fill="both", expand=True)
        settings_page.grid(row=0, column=0, sticky="nsew")
        self._workspace_frames["settings"] = settings_page

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self.content_shell, fg_color=Colors.BG_PRIMARY)
        footer.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.XS))

        self.footer_status_label = ctk.CTkLabel(
            footer,
            text=t("common.appReady"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.footer_status_label.pack(anchor="w")

    def _workspace_meta(self) -> dict[str, tuple[str, str]]:
        return {
            "home": (t("workspace.home"), t("home.subtitle")),
            "download": (t("workspace.download"), t("download.workspaceSubtitle")),
            "studio": (t("workspace.studio"), t("studio.subtitle")),
            "library": (t("workspace.library"), t("libraryWorkspace.subtitle")),
            "settings": (t("mainWindow.settingsAction"), t("mainWindow.settingsSubtitle")),
        }

    def _drawer_meta(self) -> dict[str, tuple[str, str]]:
        return {
            "queue": (t("mainWindow.queuePanelTitle"), t("mainWindow.queuePanelSubtitle")),
        }

    def show_workspace(self, view_key: str) -> None:
        if view_key not in self.PRIMARY_VIEWS:
            if view_key == "settings":
                self.show_settings_view()
            return
        self._last_primary_view_key = view_key
        self._show_view(view_key)

    def show_download_view(self, mode_key: str = "url") -> None:
        self._last_primary_view_key = "download"
        self._show_view("download")
        download_workspace = self.__dict__.get("download_workspace")
        if download_workspace is not None:
            download_workspace.select_mode(mode_key)

    def show_studio_view(self, tool_key: str = "convert") -> None:
        self._last_primary_view_key = "studio"
        self._show_view("studio")
        studio_workspace = self.__dict__.get("studio_workspace")
        if studio_workspace is not None:
            studio_workspace.select_view(tool_key)

    def show_library_view(self, view_key: Optional[str] = "library") -> None:
        self._last_primary_view_key = "library"
        self._show_view("library")
        library_workspace = self.__dict__.get("library_workspace")
        if library_workspace is not None:
            library_workspace.select_view(view_key or "library")

    def show_queue_view(self) -> None:
        self._open_drawer("queue")
        if self.queue_tab is not None and hasattr(self.queue_tab, "refresh_queue"):
            self.queue_tab.refresh_queue(force=True)

    def show_settings_view(self) -> None:
        self._show_view("settings")

    def open_command_palette(self) -> None:
        palette = self.__dict__.get("_command_palette")
        try:
            if palette is not None and palette.winfo_exists():
                palette.lift()
                palette.focus_force()
                if hasattr(palette, "_focus_search"):
                    palette._focus_search()
                return
        except Exception:
            pass

        palette = CommandPaletteDialog(self, self._build_command_palette_commands())
        self._command_palette = palette
        palette.bind("<Destroy>", lambda _event: self.__dict__.__setitem__("_command_palette", None), add="+")

    def _show_view(self, view_key: str) -> None:
        target = self._workspace_frames.get(view_key)
        if target is None:
            return

        try:
            target.tkraise()
        except Exception:
            if not target.winfo_manager():
                target.pack(fill="both", expand=True)
        self._current_view_key = view_key
        self._update_navigation_state()
        self._refresh_header_actions()

        title, subtitle = self._workspace_meta().get(view_key, (t("common.appTitle"), ""))
        self.workspace_title_label.configure(text=title)
        self.workspace_subtitle_label.configure(text=subtitle)

        if self.__dict__.get("_active_drawer_key"):
            self._close_drawer()

        if view_key == "home" and self.home_workspace is not None:
            self.home_workspace.refresh_dashboard()

    def _open_drawer(self, drawer_key: str) -> None:
        target = self._drawer_frames.get(drawer_key)
        if target is None:
            return

        if self._active_drawer_key and self._active_drawer_key in self._drawer_frames:
            self._drawer_frames[self._active_drawer_key].pack_forget()
        else:
            try:
                self._drawer_return_focus = self.focus_get()
            except Exception:
                self._drawer_return_focus = None

        if not self.drawer_shell.winfo_manager():
            self.drawer_shell.pack(side="right", fill="y", padx=(Spacing.MD, 0))

        target.pack(fill="both", expand=True)
        self._active_drawer_key = drawer_key
        title, subtitle = self._drawer_meta().get(drawer_key, ("", ""))
        self.drawer_title_label.configure(text=title)
        self.drawer_subtitle_label.configure(text=subtitle)
        self._refresh_header_actions()
        self.after(10, lambda: self.drawer_close_button.focus_set())

    def _close_drawer(self) -> None:
        if self._active_drawer_key and self._active_drawer_key in self._drawer_frames:
            self._drawer_frames[self._active_drawer_key].pack_forget()
        self._active_drawer_key = None
        if self.drawer_shell.winfo_manager():
            self.drawer_shell.pack_forget()
        self._refresh_header_actions()
        focus_target = self.__dict__.get("_drawer_return_focus")
        if focus_target is not None:
            try:
                focus_target.focus_set()
            except Exception:
                pass
        self._drawer_return_focus = None

    def _update_navigation_state(self) -> None:
        active_view = self._current_view_key
        for view_key, button in self._sidebar_buttons.items():
            base_label = self._sidebar_button_labels.get(view_key, button.cget("text"))
            icon = self._sidebar_button_icons.get(view_key, "")
            
            display_text = base_label if self._sidebar_expanded else icon
            
            if view_key == active_view:
                button.configure(
                    text=f"› {display_text}",
                    fg_color=Colors.ACCENT,
                    hover_color=Colors.ACCENT_HOVER,
                    text_color=Colors.BG_PRIMARY,
                    border_width=1,
                    border_color=Colors.ACCENT,
                    font=Fonts.LABEL_BOLD,
                )
            else:
                button.configure(
                    text=display_text,
                    fg_color="transparent",
                    hover_color=Colors.BG_HOVER,
                    text_color=Colors.TEXT_PRIMARY,
                    border_width=0,
                    border_color=Colors.BG_SURFACE,
                    font=Fonts.LABEL,
                )

    def _refresh_header_actions(self) -> None:
        pending = len(self.task_queue.get_pending_tasks())
        active = len(self.task_queue.get_active_tasks())
        total = pending + active
        if total:
            queue_text = t("mainWindow.queueActionWithCount", count=total)
        else:
            queue_text = t("mainWindow.queueAction")
        self.queue_action_button.configure(text=f"{Icons.QUEUE} {queue_text}")

        palette_button = self.__dict__.get("command_palette_button")
        if palette_button is not None:
            palette_button.configure(
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )

        if self._active_drawer_key == "queue":
            self.queue_action_button.configure(
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_HOVER,
                text_color=Colors.BG_PRIMARY,
            )
        else:
            self.queue_action_button.configure(
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )


    def _apply_responsive_shell_state(self, width: int) -> None:
        compact = width < 1320
        wide = width >= 1700

        sidebar_width = 210 if compact else 230
        if wide:
            sidebar_width = 248

        drawer_width = 340 if compact else 380
        if width >= 1500:
            drawer_width = 400
        if wide:
            drawer_width = 440

        max_width = 1180 if compact else 1320
        if wide:
            max_width = 1460
        padx = max(Spacing.MD, (width - max_width) // 2)

        quick_action_labels = {
            "paste": t("mainWindow.quickPasteUrlShort") if compact else t("mainWindow.quickPasteUrl"),
            "torrent": t("mainWindow.quickAddTorrentShort") if compact else t("mainWindow.quickAddTorrent"),
            "convert": t("mainWindow.quickConvertFileShort") if compact else t("mainWindow.quickConvertFile"),
            "library": t("mainWindow.quickOpenLibraryShort") if compact else t("mainWindow.quickOpenLibrary"),
            "queue": t("mainWindow.quickOpenQueueShort") if compact else t("mainWindow.quickOpenQueue"),
        }
        quick_action_icons = {
            "paste": Icons.LINK_INPUT,
            "torrent": Icons.TORRENT,
            "convert": Icons.CONVERT,
            "library": Icons.LIBRARY,
            "queue": Icons.QUEUE,
        }

        try:
            self.sidebar.configure(width=sidebar_width)
            self.header.pack_configure(padx=padx)
            self.stage_frame.pack_configure(padx=padx)
            self.footer_status_label.master.pack_configure(padx=padx)
            self.drawer_shell.configure(width=drawer_width)
            self.quick_actions_label.configure(
                text=t("mainWindow.quickActionsCompact") if compact else t("mainWindow.quickActionsLabel")
            )
            self.command_palette_button.configure(
                text=(
                    f"{Icons.SEARCH} {t('mainWindow.commandPaletteShort')}"
                    if compact
                    else f"{Icons.SEARCH} {t('mainWindow.commandPaletteAction')}"
                )
            )
            for key, button in self._quick_action_buttons.items():
                button.configure(text=f"{quick_action_icons[key]} {quick_action_labels[key]}")
        except Exception:
            return

    def _quick_paste_url(self) -> None:
        self.show_download_view("auto")
        try:
            clipboard_text = str(self.clipboard_get()).strip()
        except Exception:
            clipboard_text = ""

        download_workspace = getattr(self, "download_workspace", None)
        if not clipboard_text or download_workspace is None:
            return

        if hasattr(download_workspace, "apply_detected_source_text"):
            download_workspace.apply_detected_source_text(clipboard_text)
        elif hasattr(download_workspace, "set_source_text"):
            download_workspace.set_source_text(clipboard_text)
        if hasattr(download_workspace, "focus_source_input"):
            download_workspace.focus_source_input()

    def _quick_convert_file(self) -> None:
        self.show_studio_view("convert")
        converter_tab = getattr(self, "converter_tab", None)
        if converter_tab is not None and hasattr(converter_tab, "select_input_file"):
            converter_tab.select_input_file()

    def _build_command_palette_commands(self) -> list[PaletteCommand]:
        return [
            PaletteCommand(
                key="open-home",
                title=t("commandPalette.openHome"),
                subtitle=t("commandPalette.openHomeDetail"),
                action=lambda: self.show_workspace("home"),
                keywords=("home", "dashboard", "ana sayfa"),
            ),
            PaletteCommand(
                key="open-download",
                title=t("commandPalette.openDownload"),
                subtitle=t("commandPalette.openDownloadDetail"),
                action=lambda: self.show_download_view("url"),
                keywords=("download", "indir", "url"),
            ),
            PaletteCommand(
                key="open-playlist",
                title=t("commandPalette.openPlaylist"),
                subtitle=t("commandPalette.openPlaylistDetail"),
                action=lambda: self.show_download_view("playlist"),
                keywords=("playlist", "download", "indir"),
            ),
            PaletteCommand(
                key="open-torrent",
                title=t("commandPalette.openTorrent"),
                subtitle=t("commandPalette.openTorrentDetail"),
                action=lambda: self.show_download_view("torrent"),
                keywords=("torrent", "magnet"),
            ),
            PaletteCommand(
                key="open-studio",
                title=t("commandPalette.openStudio"),
                subtitle=t("commandPalette.openStudioDetail"),
                action=lambda: self.show_workspace("studio"),
                keywords=("studio", "edit", "process", "studyo"),
            ),
            PaletteCommand(
                key="open-convert",
                title=t("commandPalette.openConvert"),
                subtitle=t("commandPalette.openConvertDetail"),
                action=lambda: self.show_studio_view("convert"),
                keywords=("convert", "conversion", "donustur"),
            ),
            PaletteCommand(
                key="open-filters",
                title=t("commandPalette.openFilters"),
                subtitle=t("commandPalette.openFiltersDetail"),
                action=lambda: self.show_studio_view("filters"),
                keywords=("filters", "effects", "filtre"),
            ),
            PaletteCommand(
                key="open-library",
                title=t("commandPalette.openLibrary"),
                subtitle=t("commandPalette.openLibraryDetail"),
                action=lambda: self.show_library_view("library"),
                keywords=("library", "media", "kutuphane"),
            ),
            PaletteCommand(
                key="open-history",
                title=t("commandPalette.openHistory"),
                subtitle=t("commandPalette.openHistoryDetail"),
                action=lambda: self.show_library_view("history"),
                keywords=("history", "gecmis"),
            ),
            PaletteCommand(
                key="open-queue",
                title=t("commandPalette.openQueue"),
                subtitle=t("commandPalette.openQueueDetail"),
                action=self.show_queue_view,
                keywords=("queue", "tasks", "kuyruk"),
            ),
            PaletteCommand(
                key="open-settings",
                title=t("commandPalette.openSettings"),
                subtitle=t("commandPalette.openSettingsDetail"),
                action=self.show_settings_view,
                keywords=("settings", "ayarlar"),
            ),
            PaletteCommand(
                key="paste-url",
                title=t("commandPalette.pasteUrl"),
                subtitle=t("commandPalette.pasteUrlDetail"),
                action=self._quick_paste_url,
                keywords=("paste", "url", "clipboard", "yapistir"),
            ),
            PaletteCommand(
                key="convert-file",
                title=t("commandPalette.convertFile"),
                subtitle=t("commandPalette.convertFileDetail"),
                action=self._quick_convert_file,
                keywords=("convert", "file", "donustur"),
            ),
        ]

    def _get_screen_work_area(self) -> tuple[int, int, int, int]:
        """Return taskbar-aware usable bounds, preferring the active monitor on Windows."""
        try:
            if platform.system() == "Windows":
                user32 = ctypes.windll.user32
                MONITOR_DEFAULTTONEAREST = 2

                class RECT(ctypes.Structure):
                    _fields_ = [
                        ("left", ctypes.c_long),
                        ("top", ctypes.c_long),
                        ("right", ctypes.c_long),
                        ("bottom", ctypes.c_long),
                    ]

                class POINT(ctypes.Structure):
                    _fields_ = [
                        ("x", ctypes.c_long),
                        ("y", ctypes.c_long),
                    ]

                class MONITORINFO(ctypes.Structure):
                    _fields_ = [
                        ("cbSize", ctypes.c_ulong),
                        ("rcMonitor", RECT),
                        ("rcWork", RECT),
                        ("dwFlags", ctypes.c_ulong),
                    ]

                def _rect_to_work_area(rect: RECT) -> tuple[int, int, int, int] | None:
                    width = max(int(rect.right - rect.left), 0)
                    height = max(int(rect.bottom - rect.top), 0)
                    if width <= 0 or height <= 0:
                        return None
                    return int(rect.left), int(rect.top), width, height

                def _monitor_work_area_from_handle(handle) -> tuple[int, int, int, int] | None:
                    if not handle:
                        return None
                    info = MONITORINFO()
                    info.cbSize = ctypes.sizeof(MONITORINFO)
                    if not user32.GetMonitorInfoW(handle, ctypes.byref(info)):
                        return None
                    return _rect_to_work_area(info.rcWork)

                try:
                    foreground = user32.GetForegroundWindow()
                    if foreground:
                        monitor = user32.MonitorFromWindow(foreground, MONITOR_DEFAULTTONEAREST)
                        work_area = _monitor_work_area_from_handle(monitor)
                        if work_area is not None:
                            return work_area
                except Exception:
                    pass

                try:
                    point = POINT()
                    if user32.GetCursorPos(ctypes.byref(point)):
                        point_value = POINT(point.x, point.y)
                        monitor = user32.MonitorFromPoint(point_value, MONITOR_DEFAULTTONEAREST)
                        work_area = _monitor_work_area_from_handle(monitor)
                        if work_area is not None:
                            return work_area
                except Exception:
                    pass

                rect = RECT()
                if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    work_area = _rect_to_work_area(rect)
                    if work_area is not None:
                        return work_area
        except Exception:
            pass

        try:
            left = int(getattr(self, "winfo_vrootx", lambda: 0)() or 0)
            top = int(getattr(self, "winfo_vrooty", lambda: 0)() or 0)
            width = int(getattr(self, "winfo_vrootwidth", lambda: 0)() or 0)
            height = int(getattr(self, "winfo_vrootheight", lambda: 0)() or 0)
            if width > 0 and height > 0:
                return left, top, width, height
        except Exception:
            pass

        return 0, 0, int(self.winfo_screenwidth()), int(self.winfo_screenheight())

    def _show_centered_initial_window(self) -> None:
        """Show the initial window only after it has been centered."""
        try:
            self._center_window()
            self.deiconify()
            self.lift()
        except Exception:
            try:
                self.deiconify()
            except Exception:
                pass

    def _center_window(self):
        """Center the main window within the taskbar-aware work area."""
        try:
            self.update_idletasks()
            width = int(self.winfo_width() or 1360)
            height = int(self.winfo_height() or 840)
            frame_width = max(int(self.winfo_rootx() - self.winfo_x()), 0)
            titlebar_height = max(int(self.winfo_rooty() - self.winfo_y()), 0)
            outer_width = width + (frame_width * 2)
            outer_height = height + frame_width + titlebar_height
            left, top, work_width, work_height = self._get_screen_work_area()
            x = left + max((work_width - outer_width) // 2, 0)
            y = top + max((work_height - outer_height) // 2, 0)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _setup_global_shortcuts(self):
        """Set up global keyboard shortcuts for the entire application."""
        self.bind("<Control-Return>", self._on_ctrl_enter)
        self.bind("<Escape>", self._on_escape)
        self.bind("<Control-l>", self._on_ctrl_l)
        self.bind("<Control-k>", lambda _event: self.open_command_palette())
        self.bind("<Control-comma>", lambda _event: self.show_settings_view())

    def _get_active_shortcut_tab(self):
        """Return the currently visible feature widget that supports global shortcuts."""
        for tab in (
            self.__dict__.get("torrent_tab"),
            self.__dict__.get("download_tab"),
            self.__dict__.get("converter_tab"),
            self.__dict__.get("subtitle_tab"),
            self.__dict__.get("mixer_tab"),
            self.__dict__.get("filters_tab"),
            self.__dict__.get("library_tab"),
        ):
            if tab and getattr(tab, "winfo_viewable", lambda: False)():
                return tab
        return None

    def _on_ctrl_enter(self, event=None):
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_ctrl_enter", None) if tab else None
        if callable(handler):
            return handler(event)

    def _on_escape(self, event=None):
        if self.__dict__.get("_active_drawer_key"):
            self._close_drawer()
            return "break"
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_escape", None) if tab else None
        if callable(handler):
            return handler(event)

    def _on_ctrl_l(self, event=None):
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_ctrl_l", None) if tab else None
        if callable(handler):
            return handler(event)

    def _update_status_text(self, text: str):
        footer = self.__dict__.get("footer_status_label")
        if footer is not None:
            footer.configure(text=text)
        download_tab = self.__dict__.get("download_tab")
        if download_tab is not None:
            download_tab.set_status_text(text)

    def _cancel_queue_task(self, task_id: str):
        if self.task_queue.cancel_task(task_id):
            self._update_status_text(t("mainWindow.taskCancelled", taskId=task_id))
            return
        self._update_status_text(t("mainWindow.taskCancelFailed", taskId=task_id))

    def _open_output_folder(self, file_path: str):
        folder_path = Path(file_path).parent
        if not folder_path.exists():
            return

        system = platform.system()
        try:
            if system == "Windows":
                subprocess.run(["explorer", "/select,", str(file_path)], check=False)
            elif system == "Darwin":
                subprocess.run(["open", "-R", str(file_path)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder_path)], check=False)
        except Exception as exc:
            logger.error(f"Failed to open folder: {exc}")

    def _notify_conversion_complete(self, output_file: str):
        NotificationManager.show_conversion_complete(Path(output_file).name)

    def _auto_add_outputs_to_library(
        self,
        file_paths: Any,
        *,
        source_type: str,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        auto_adder = getattr(self, "media_library_auto_adder", None)
        if auto_adder is None:
            return

        def worker() -> None:
            self._register_outputs_with_library(
                file_paths,
                source_type=source_type,
                title=title,
                tags=tags,
                metadata=metadata,
            )

        threading.Thread(target=worker, daemon=True, name="MediaLibraryAutoAdd").start()

    def _register_outputs_with_library(
        self,
        file_paths: Any,
        *,
        source_type: str,
        title: Optional[str] = None,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        auto_adder = getattr(self, "media_library_auto_adder", None)
        if auto_adder is None:
            return []

        results = auto_adder.register_outputs(
            file_paths,
            source_type=source_type,
            title=title,
            tags=tags,
            metadata=metadata,
        )
        if any(result.added for result in results):
            self._schedule_library_refresh()
        return results

    def _schedule_library_refresh(self) -> None:
        callback_queue = self.__dict__.get("_ui_callback_queue")
        if callback_queue is None:
            return

        library_tab = getattr(self, "library_tab", None)
        if library_tab is not None and hasattr(library_tab, "refresh_dashboard"):
            callback_queue.put((library_tab.refresh_dashboard, (), {}))

        home_workspace = getattr(self, "home_workspace", None)
        if home_workspace is not None and hasattr(home_workspace, "refresh_dashboard"):
            callback_queue.put((home_workspace.refresh_dashboard, (), {}))

    def _process_ui_callbacks(self) -> None:
        callback_queue = self.__dict__.get("_ui_callback_queue")
        if callback_queue is None:
            return
        while True:
            try:
                callback, args, kwargs = callback_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback(*args, **kwargs)
            except Exception as exc:
                logger.debug("UI callback failed: %s", exc)

    def _setup_tray_integration(self):
        self.tray = SystemTrayIntegration(
            app_name="RAVN",
            on_open=self._restore_from_tray,
            on_pause_queue=self._toggle_queue_pause,
            on_quit=self._quit_from_tray,
        )
        if self.tray.available:
            self.tray.run()

    def _toggle_queue_pause(self):
        self.queue_paused = self.task_queue.toggle_pause()
        state_label = t("mainWindow.queuePaused") if self.queue_paused else t("mainWindow.queueResumed")
        self._update_status_text(t("mainWindow.queueState", state=state_label))
        self._refresh_header_actions()

    def _restore_from_tray(self):
        self.after(0, self._show_window)

    def _show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_window_close(self):
        close_to_tray = self.config_manager.get("close_to_tray", True)
        if not close_to_tray or not self.tray or not self.tray.available:
            self._quit_app()
            return

        self.withdraw()
        self._update_status_text(t("mainWindow.minimizedToTray"))

    def _resync_workspace_tab_references(self) -> None:
        if self.download_workspace is not None:
            self.download_tab = self.download_workspace.download_tab
            self.torrent_tab = self.download_workspace.torrent_tab
        if self.studio_workspace is not None:
            self.converter_tab = self.studio_workspace.converter_tab
            self.subtitle_tab = self.studio_workspace.subtitle_tab
            self.filters_tab = self.studio_workspace.filters_tab
            self.mixer_tab = self.studio_workspace.mixer_tab
        if self.library_workspace is not None:
            self.library_tab = self.library_workspace.library_tab
            self.history_tab = self.library_workspace.history_tab

    def refresh_i18n(self):
        """Update visible shell/workspace text in place for runtime language changes."""
        manager = get_i18n(self.config_manager)
        configured_language = str(self.config_manager.get("language", "tr") or "tr").strip().lower()
        manager.set_language("en" if configured_language == "en" else "tr", persist=False)
        self.i18n = manager
        Tooltip.dismiss_all()

        palette = self.__dict__.get("_command_palette")
        if palette is not None:
            try:
                palette.close()
            except Exception:
                pass
            self._command_palette = None

        try:
            self.title(t("common.appTitle"))
        except Exception:
            pass
        brand_heading = self.__dict__.get("brand_heading_label")
        if brand_heading is not None:
            brand_heading.configure(text=t("common.appHeading"))
        brand_subtitle = self.__dict__.get("brand_subtitle_label")
        if brand_subtitle is not None:
            brand_subtitle.configure(text=t("common.appSubtitle"))
        sidebar_hint = self.__dict__.get("sidebar_hint_label")
        if sidebar_hint is not None:
            sidebar_hint.configure(text=t("mainWindow.sidebarHint"))
        footer = self.__dict__.get("footer_status_label")
        if footer is not None:
            footer.configure(text=t("common.appReady"))

        self._sidebar_button_labels.update(
            {
                "home": f"{Icons.BROWSE}  {t('workspace.home')}",
                "download": f"{Icons.DOWNLOAD}  {t('workspace.download')}",
                "studio": f"{Icons.CONVERT}  {t('workspace.studio')}",
                "library": f"{Icons.LIBRARY}  {t('workspace.library')}",
                "settings": f"{Icons.SETTINGS}  {t('mainWindow.settingsAction')}",
            }
        )
        self._update_navigation_state()
        self._refresh_sidebar_utility_controls()

        command_tooltip = self.__dict__.get("_command_palette_tooltip")
        if command_tooltip is not None:
            command_tooltip.update_text(t("mainWindow.commandPaletteTooltip"))
        queue_tooltip = self.__dict__.get("_queue_action_tooltip")
        if queue_tooltip is not None:
            queue_tooltip.update_text(t("mainWindow.queueTooltip"))

        for workspace in (
            self.home_workspace,
            self.download_workspace,
            self.studio_workspace,
            self.library_workspace,
        ):
            if workspace is not None and hasattr(workspace, "refresh_i18n"):
                workspace.refresh_i18n()
        if self.settings_tab is not None and hasattr(self.settings_tab, "refresh_i18n"):
            self.settings_tab.refresh_i18n()
        if self.queue_tab is not None and hasattr(self.queue_tab, "refresh_i18n"):
            self.queue_tab.refresh_i18n()

        self._resync_workspace_tab_references()
        self._apply_responsive_shell_state(self.winfo_width() or 1400)

        title, subtitle = self._workspace_meta().get(self._current_view_key or self._last_primary_view_key, (t("common.appTitle"), ""))
        self.workspace_title_label.configure(text=title)
        self.workspace_subtitle_label.configure(text=subtitle)
        if self._active_drawer_key:
            drawer_title, drawer_subtitle = self._drawer_meta().get(self._active_drawer_key, ("", ""))
            self.drawer_title_label.configure(text=drawer_title)
            self.drawer_subtitle_label.configure(text=drawer_subtitle)
        self._refresh_header_actions()

    def _refresh_task_bound_surfaces_if_needed(
        self,
        task_snapshot: Optional[tuple[tuple[str, str, int, str, str], ...]] = None,
    ) -> bool:
        """Refresh Home/Queue shell surfaces only when the task snapshot actually changes."""
        current_snapshot = task_snapshot if task_snapshot is not None else self.task_queue.get_ui_snapshot()
        if current_snapshot == self._last_task_snapshot:
            return False

        self._last_task_snapshot = current_snapshot
        self._refresh_header_actions()
        if self._current_view_key == "home" and self.home_workspace is not None:
            self.home_workspace.refresh_dashboard()
        if self.queue_tab is not None and hasattr(self.queue_tab, "refresh_queue"):
            self.queue_tab.refresh_queue(force=True)
        return True

    def _schedule_task_queue_callback_pump(self):
        """Pump task/UI callbacks and refresh queue-bound surfaces only when state changes."""
        try:
            self.task_queue.process_callbacks()
            self._process_ui_callbacks()
            self._refresh_task_bound_surfaces_if_needed()
        finally:
            self._task_callback_after_id = self.after(120, self._schedule_task_queue_callback_pump)

    def _quit_from_tray(self):
        self.after(0, self._quit_app)

    def _on_window_resize(self, event):
        if event.widget is not self:
            return
        self._apply_responsive_shell_state(self.winfo_width())

    def _quit_app(self):
        if self._task_callback_after_id is not None:
            try:
                self.after_cancel(self._task_callback_after_id)
            except Exception:
                pass
            self._task_callback_after_id = None
        if self.tray:
            self.tray.stop()
        self.destroy()


def main():
    """Start the application."""
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
