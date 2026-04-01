"""
Ana uygulama penceresi - CustomTkinter arayüzü (Sekmeli)
"""

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
from ravn_app.ui.design_tokens import Colors, Fonts, Icons, Spacing
from ravn_app.ui.tabs import (
    ConverterTab,
    DownloadTab,
    FiltersTab,
    HistoryTab,
    LibraryTab,
    MixerTab,
    QueueTab,
    SettingsTab,
    SubtitleTab,
    TorrentTab,
)
from ravn_app.ui.ui_components import ToastManager


logger = get_logger(__name__)


class YouTubeDownloaderApp(ctk.CTk):
    """Ana uygulama penceresi - Sekmeli arayüz"""

    def __init__(self):
        super().__init__()
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.title(t("common.appTitle"))
        self.geometry("1400x900")
        self.minsize(1200, 800)
        self._apply_window_icon()

        self.db_manager = DatabaseManager()
        self.config_manager = ConfigManager()
        self.i18n = get_i18n(self.config_manager)
        self.platform_manager = PlatformManager()
        self.downloader = YouTubeDownloader()
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
        self.download_tab: Optional[DownloadTab] = None
        self.converter_tab = None
        self.subtitle_tab = None
        self.mixer_tab = None
        self.library_tab = None
        self.filters_tab = None
        self._task_callback_after_id = None
        self._ui_callback_queue: queue.Queue = queue.Queue()
        self.tray = None

        self._setup_ui()
        self.after(100, self._center_window)
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
                self._icon_ref = photo  # prevent GC
        except Exception:
            pass  # icon is cosmetic; never crash on failure

    def _setup_ui(self):
        for child in list(self.winfo_children()):
            child.destroy()

        header_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        header_frame.pack(fill="x", padx=0, pady=0)

        header_inner = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_inner.pack(pady=(Spacing.SM, Spacing.XS))

        ctk.CTkLabel(
            header_inner,
            text=t("common.appHeading"),
            font=Fonts.TITLE,
        ).pack()

        ctk.CTkLabel(
            header_inner,
            text=t("common.appSubtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack()

        self.tabview = ctk.CTkTabview(self, anchor="n")
        self.tabview.pack(fill="both", expand=True, padx=Spacing.XS, pady=(0, Spacing.XS))
        self.bind("<Configure>", self._on_window_resize)
        self.tabview.configure(
            segmented_button_fg_color=Colors.BG_SURFACE,
            segmented_button_selected_color=Colors.ACCENT,
            segmented_button_selected_hover_color=Colors.ACCENT_HOVER,
            segmented_button_unselected_color=Colors.BG_CARD,
            segmented_button_unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
        )

        download_tab_container = self.tabview.add(f"{Icons.DOWNLOAD}  {t('tabs.download')}")
        self.download_tab = DownloadTab(
            download_tab_container,
            downloader=self.downloader,
            config_manager=self.config_manager,
            platform_manager=self.platform_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            queue_paused_getter=lambda: self.queue_paused,
            show_queue_tab_callback=lambda: self.tabview.set(f"{Icons.QUEUE}  {t('tabs.queue')}"),
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color="transparent",
        )
        self.download_tab.pack(fill="both", expand=True)

        converter_tab = self.tabview.add(f"{Icons.CONVERT}  {t('tabs.convert')}")
        self.converter_tab = ConverterTab(
            converter_tab,
            db_manager=self.db_manager,
            notify_callback=self._notify_conversion_complete,
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color="transparent",
        )
        self.converter_tab.pack(fill="both", expand=True)

        subtitle_tab = self.tabview.add(f"{Icons.SUBTITLE}  {t('tabs.subtitle')}")
        self.subtitle_tab = SubtitleTab(subtitle_tab, fg_color="transparent")
        self.subtitle_tab.pack(fill="both", expand=True)

        torrent_tab = self.tabview.add(f"{Icons.TORRENT}  {t('tabs.torrent')}")
        TorrentTab(
            torrent_tab,
            config_manager=self.config_manager,
            toast_manager_getter=lambda: self.toast_manager,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        mixer_tab = self.tabview.add(f"{Icons.MIXER}  {t('tabs.mixer')}")
        self.mixer_tab = MixerTab(
            mixer_tab,
            config_manager=self.config_manager,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            show_queue_tab_callback=lambda: self.tabview.set(f"{Icons.QUEUE}  {t('tabs.queue')}"),
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color="transparent",
        )
        self.mixer_tab.pack(fill="both", expand=True)

        filters_tab = self.tabview.add(f"{Icons.FILTERS}  {t('tabs.filters')}")
        self.filters_tab = FiltersTab(
            filters_tab,
            config_manager=self.config_manager,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            show_queue_tab_callback=lambda: self.tabview.set(f"{Icons.QUEUE}  {t('tabs.queue')}"),
            auto_add_to_library_callback=self._auto_add_outputs_to_library,
            fg_color="transparent",
        )
        self.filters_tab.pack(fill="both", expand=True)

        library_tab = self.tabview.add(f"{Icons.LIBRARY}  {t('tabs.library')}")
        self.library_tab = LibraryTab(
            library_tab,
            config_manager=self.config_manager,
            db_manager=self.db_manager,
            task_queue=self.task_queue,
            animation_manager=self.animation_manager,
            toast_manager_getter=lambda: self.toast_manager,
            show_queue_tab_callback=lambda: self.tabview.set(f"{Icons.QUEUE}  {t('tabs.queue')}"),
            fg_color="transparent",
        )
        self.library_tab.pack(fill="both", expand=True)

        queue_tab = self.tabview.add(f"{Icons.QUEUE}  {t('tabs.queue')}")
        QueueTab(
            queue_tab,
            on_cancel_task=self._cancel_queue_task,
            on_open_folder=self._open_output_folder,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        history_tab = self.tabview.add(f"{Icons.HISTORY}  {t('tabs.history')}")
        HistoryTab(history_tab, self.db_manager, fg_color="transparent").pack(fill="both", expand=True)

        settings_tab = self.tabview.add(f"{Icons.SETTINGS}  {t('tabs.settings')}")
        SettingsTab(
            settings_tab,
            self.config_manager,
            on_language_changed=self.refresh_i18n,
            fg_color="transparent",
        ).pack(fill="both", expand=True)

        self._setup_tab_switch_transition()

        footer_frame = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        footer_frame.pack(fill="x", padx=0, pady=0)

        ctk.CTkLabel(
            footer_frame,
            text=t("common.appReady"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(pady=(0, Spacing.XS))

    def _center_window(self):
        """Center the main window on the active display."""
        try:
            self.update_idletasks()
            width = self.winfo_width() or 1400
            height = self.winfo_height() or 900
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = max((screen_width - width) // 2, 0)
            y = max((screen_height - height) // 2, 0)
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _setup_global_shortcuts(self):
        """Set up global keyboard shortcuts for the entire application."""
        self.bind("<Control-Return>", self._on_ctrl_enter)
        self.bind("<Escape>", self._on_escape)
        self.bind("<Control-l>", self._on_ctrl_l)

    def _get_active_shortcut_tab(self):
        """Return the currently visible tab widget that supports global shortcuts."""
        for tab in (
            getattr(self, "download_tab", None),
            getattr(self, "converter_tab", None),
            getattr(self, "subtitle_tab", None),
            getattr(self, "mixer_tab", None),
            getattr(self, "filters_tab", None),
            getattr(self, "library_tab", None),
        ):
            if tab and getattr(tab, "winfo_viewable", lambda: False)():
                return tab
        return None

    def _on_ctrl_enter(self, event=None):
        """Handle Ctrl+Enter - delegate to active tab."""
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_ctrl_enter", None) if tab else None
        if callable(handler):
            return handler(event)

    def _on_escape(self, event=None):
        """Handle Escape - delegate to active tab."""
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_escape", None) if tab else None
        if callable(handler):
            return handler(event)

    def _on_ctrl_l(self, event=None):
        """Handle Ctrl+L - delegate to active tab."""
        tab = self._get_active_shortcut_tab()
        handler = getattr(tab, "_on_ctrl_l", None) if tab else None
        if callable(handler):
            return handler(event)

    def _setup_tab_switch_transition(self):
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
                duration=120,
            )
            self.after(
                120,
                lambda: self.animation_manager.animate_color_transition(
                    selected_tab,
                    "fg_color",
                    Colors.BG_SURFACE,
                    "transparent",
                    duration=120,
                ),
            )

            # MIC-04: aktif sekme metnini bold yap
            self._update_active_tab_font(tab_name)

        segmented.configure(command=wrapped_command)

        # MIC-04: İlk yüklemede de aktif sekmeyi bold yap
        try:
            initial_tab = self.tabview.get()
            if initial_tab:
                self.after(100, lambda: self._update_active_tab_font(initial_tab))
        except Exception:
            pass

    def _update_active_tab_font(self, active_tab_name: str):
        """MIC-04: Aktif sekme etiketini bold, diğerlerini normal yap."""
        segmented = getattr(self.tabview, "_segmented_button", None)
        if segmented is None:
            return
        try:
            for btn_name, btn_widget in segmented._buttons_dict.items():
                if btn_name == active_tab_name:
                    btn_widget.configure(font=Fonts.H2)
                else:
                    btn_widget.configure(font=Fonts.LABEL)
        except Exception:
            pass

    def _update_status_text(self, text: str):
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
        """Register generated outputs in the media library without blocking the UI thread."""
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
        """Synchronous helper used by the background auto-add worker and tests."""
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
        library_tab = getattr(self, "library_tab", None)
        if library_tab is None or not hasattr(library_tab, "refresh_dashboard"):
            return

        callback_queue = self.__dict__.get("_ui_callback_queue")
        if callback_queue is None:
            return

        callback_queue.put((library_tab.refresh_dashboard, (), {}))

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

    def refresh_i18n(self):
        """Rebuild the visible UI to apply language changes at runtime."""
        get_i18n(self.config_manager)
        self.title(t("common.appTitle"))
        self._setup_ui()

    def _schedule_task_queue_callback_pump(self):
        """Poll task queue callbacks so worker-thread UI updates land on the main thread."""
        try:
            self.task_queue.process_callbacks()
            self._process_ui_callbacks()
        finally:
            self._task_callback_after_id = self.after(120, self._schedule_task_queue_callback_pump)

    def _quit_from_tray(self):
        self.after(0, self._quit_app)

    def _on_window_resize(self, event):
        if event.widget is not self:
            return

        width = self.winfo_width()
        max_width = 1200
        padx = max(10, (width - max_width) // 2)
        try:
            self.tabview.pack_configure(padx=padx)
        except Exception:
            return

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
    """Uygulamayı başlat"""
    app = YouTubeDownloaderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
