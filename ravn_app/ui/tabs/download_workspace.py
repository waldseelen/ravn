"""Download workspace that groups standard and torrent download flows."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Fonts, Sizes, Spacing
from ravn_app.ui.tabs.download_tab import DownloadTab
from ravn_app.ui.tabs.torrent_tab import TorrentTab


class DownloadWorkspace(ctk.CTkFrame):
    """Grouped download workspace for URL / playlist / batch / torrent flows."""

    _MODE_KEYS = ("url", "playlist", "batch", "torrent")

    def __init__(
        self,
        parent,
        downloader: Any,
        config_manager: Any,
        platform_manager: Any,
        task_queue: Any,
        animation_manager: Any,
        toast_manager_getter: Callable[[], Any],
        queue_paused_getter: Callable[[], bool],
        show_queue_callback: Callable[[], None],
        auto_add_to_library_callback: Optional[Callable[..., None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self._downloader = downloader
        self._config_manager = config_manager
        self._platform_manager = platform_manager
        self._task_queue = task_queue
        self._animation_manager = animation_manager
        self._toast_manager_getter = toast_manager_getter
        self._queue_paused_getter = queue_paused_getter
        self._show_queue_callback = show_queue_callback
        self._auto_add_to_library_callback = auto_add_to_library_callback
        self._segment_value_to_key: dict[str, str] = {}
        self._active_mode_key = "url"

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        self.title_label = ctk.CTkLabel(
            header,
            text=t("download.workspaceTitle"),
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text=t("download.workspaceSubtitle"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.mode_selector = ctk.CTkSegmentedButton(
            self,
            values=self._build_segment_values(),
            fg_color=Colors.BG_SURFACE,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
            unselected_color=Colors.BG_CARD,
            unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            command=self._on_segment_selected,
        )
        self.mode_selector.pack(anchor="w", padx=Spacing.LG, pady=(0, Spacing.SM))

        self.guide_panel = CollapsiblePanel(
            self,
            title=t("download.guideTitle"),
            subtitle=t("download.guideSubtitle"),
            expanded=False,
        )
        self.guide_panel.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        guide_body = self.guide_panel.content_frame()
        self._guide_labels = []
        for key in ("download.guideLine1", "download.guideLine2", "download.guideLine3"):
            label = ctk.CTkLabel(
                guide_body,
                text=f"• {t(key)}",
                font=Fonts.SMALL,
                text_color=Colors.TEXT_MUTED,
                anchor="w",
                justify="left",
            )
            label.pack(fill="x", pady=(0, Spacing.XS))
            self._guide_labels.append((label, key))

        self.content_host = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        self.content_host.pack(fill="both", expand=True)
        self.content_host.grid_rowconfigure(0, weight=1)
        self.content_host.grid_columnconfigure(0, weight=1)

        self.download_tab = DownloadTab(
            self.content_host,
            downloader=self._downloader,
            config_manager=self._config_manager,
            platform_manager=self._platform_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            queue_paused_getter=self._queue_paused_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.download_tab.grid(row=0, column=0, sticky="nsew")

        self.torrent_tab = TorrentTab(
            self.content_host,
            config_manager=self._config_manager,
            toast_manager_getter=self._toast_manager_getter,
            fg_color=Colors.BG_PRIMARY,
        )
        self.torrent_tab.grid(row=0, column=0, sticky="nsew")

        initial_label = next((label for label, key in self._segment_value_to_key.items() if key == "url"), None)
        if initial_label:
            self.mode_selector.set(initial_label)
        self.select_mode(self._active_mode_key)

    def refresh_i18n(self) -> None:
        mode_key = self._active_mode_key
        for child in list(self.winfo_children()):
            child.destroy()
        self._segment_value_to_key = {}
        self._build_ui()
        self.select_mode(mode_key)

    def _build_segment_values(self) -> list[str]:
        labels = [
            (t("download.workspaceModeUrl"), "url"),
            (t("download.workspaceModePlaylist"), "playlist"),
            (t("download.workspaceModeBatch"), "batch"),
            (t("download.workspaceModeTorrent"), "torrent"),
        ]
        self._segment_value_to_key = {label: key for label, key in labels}
        return [label for label, _key in labels]

    def _on_segment_selected(self, selected_label: str) -> None:
        self.select_mode(self._segment_value_to_key.get(selected_label, "url"))

    def select_mode(self, mode_key: str) -> None:
        if mode_key not in self._MODE_KEYS:
            mode_key = "url"
        self._active_mode_key = mode_key

        selected_label = next((label for label, key in self._segment_value_to_key.items() if key == mode_key), None)
        if selected_label and self.mode_selector.get() != selected_label:
            self.mode_selector.set(selected_label)

        if mode_key == "torrent":
            self._show_mode_frame(self.torrent_tab, self.download_tab)
            return

        self._show_mode_frame(self.download_tab, self.torrent_tab)
        self._sync_standard_mode(mode_key)

    def _show_mode_frame(self, active_frame, inactive_frame) -> None:
        content_host = getattr(self, "content_host", None)
        if content_host is not None and hasattr(active_frame, "tkraise"):
            active_frame.tkraise()
            return

        if hasattr(inactive_frame, "pack_forget"):
            inactive_frame.pack_forget()
        if hasattr(active_frame, "pack"):
            active_frame.pack(fill="both", expand=True)

    def _sync_standard_mode(self, mode_key: str) -> None:
        batch_enabled = mode_key == "batch"
        current_batch_state = bool(self.download_tab.batch_mode_var.get())
        if batch_enabled != current_batch_state:
            self.download_tab.batch_mode_var.set(batch_enabled)
            self.download_tab._toggle_batch_mode()

        if mode_key == "playlist":
            self.download_tab.set_status_text(t("download.workspacePlaylistHint"))
        elif mode_key == "batch":
            self.download_tab.set_status_text(t("download.workspaceBatchHint"))
        else:
            self.download_tab.set_status_text(t("download.workspaceUrlHint"))
