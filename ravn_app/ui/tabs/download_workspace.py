"""Download workspace that groups media and torrent acquisition behind one smart source bar."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import customtkinter as ctk
from tkinter import filedialog

from ravn_app.core.i18n import t
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Fonts, Sizes, Spacing
from ravn_app.ui.tabs.download_tab import DownloadTab
from ravn_app.ui.tabs.torrent_tab import TorrentTab


class DownloadWorkspace(ctk.CTkFrame):
    """Unified acquisition workspace for URLs, playlists, batches, and torrents."""

    _MODE_KEYS = ("auto", "url", "playlist", "batch", "torrent")
    _OVERRIDE_KEYS = ("auto", "media", "playlist", "batch", "torrent")
    _MEDIA_OUTPUT_KEYS = ("video", "audio")

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

        self._override_value_to_key: dict[str, str] = {}
        self._media_output_value_to_key: dict[str, str] = {}
        self._source_override_key = "auto"
        self._media_output_key = "video"
        self._detected_mode_key = "url"
        self._active_mode_key = "url"
        self._compact_layout_active = False

        self._build_ui()
        self.bind("<Configure>", self._on_workspace_resize)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        source_card = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        source_card.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.SM))

        source_header = ctk.CTkFrame(source_card, fg_color="transparent")
        source_header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        ctk.CTkLabel(
            source_header,
            text=t("download.workspaceSourceLabel"),
            font=Fonts.LABEL_BOLD,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")

        self.detected_source_badge = ctk.CTkLabel(
            source_header,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.BTN_SECONDARY,
            corner_radius=Sizes.CORNER_SM,
            padx=10,
            pady=4,
        )
        self.detected_source_badge.pack(side="right")

        self.source_textbox = ctk.CTkTextbox(
            source_card,
            height=60,
            font=Fonts.LABEL,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.BORDER,
            border_width=1,
            wrap="word",
        )
        self.source_textbox.pack(fill="x", padx=Spacing.MD)
        self.source_textbox.bind("<KeyRelease>", self._on_source_text_changed)

        source_actions = ctk.CTkFrame(source_card, fg_color="transparent")
        source_actions.pack(fill="x", padx=Spacing.MD, pady=(Spacing.XS, Spacing.SM))

        self.source_helper_label = ctk.CTkLabel(
            source_actions,
            text=t("download.workspaceSourceHelper"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.source_helper_label.pack(side="left", fill="x", expand=True)

        self.source_browse_button = ctk.CTkButton(
            source_actions,
            text=t("download.workspaceSourceBrowseTorrent"),
            command=self._browse_torrent_source,
            font=Fonts.SMALL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
        )
        self.source_browse_button.pack(side="right")
        
        self.source_preview_button = ctk.CTkButton(
            source_actions,
            text=t("download.previewAction") if t("download.previewAction") != "download.previewAction" else "Önizleme",
            command=self._preview_source,
            font=Fonts.SMALL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
        )
        self.source_preview_button.pack(side="right", padx=(0, Spacing.XS))

        override_row = ctk.CTkFrame(self, fg_color="transparent")
        override_row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.XS))

        ctk.CTkLabel(
            override_row,
            text=t("download.workspaceOverrideLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, Spacing.SM))

        self.mode_selector = ctk.CTkSegmentedButton(
            override_row,
            values=self._build_override_values(),
            fg_color=Colors.BG_SURFACE,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
            unselected_color=Colors.BG_CARD,
            unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            command=self._on_override_selected,
        )
        self.mode_selector.pack(side="left")

        media_output_row = ctk.CTkFrame(self, fg_color="transparent")
        media_output_row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.XS))
        self.media_output_row = media_output_row
        
        ctk.CTkLabel(
            media_output_row,
            text="Önayar:" if t("download.presetLabel") == "download.presetLabel" else t("download.presetLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, Spacing.SM))
        
        self.preset_selector = ctk.CTkComboBox(
            media_output_row,
            values=["Özel (Custom)", "Arşiv (Archive)", "Mobil (Mobile)", "Yayın (Broadcast)"],
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BG_INPUT,
            border_color=Colors.BORDER,
            command=self._on_preset_selected,
        )
        self.preset_selector.pack(side="left", padx=(0, Spacing.MD))

        ctk.CTkLabel(
            media_output_row,
            text=t("download.workspaceOutputLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(side="left", padx=(0, Spacing.SM))

        self.media_output_selector = ctk.CTkSegmentedButton(
            media_output_row,
            values=self._build_media_output_values(),
            fg_color=Colors.BG_SURFACE,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
            unselected_color=Colors.BG_CARD,
            unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            command=self._on_media_output_selected,
        )
        self.media_output_selector.pack(side="left")

        self.guide_panel = CollapsiblePanel(
            self,
            title=t("download.guideTitle"),
            subtitle=t("download.guideSubtitle"),
            expanded=False,
        )
        self.guide_panel.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.SM))
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

        self.download_scroll_frame = ctk.CTkScrollableFrame(
            self.content_host,
            fg_color=Colors.BG_PRIMARY,
            corner_radius=0,
        )
        self.download_scroll_frame.grid(row=0, column=0, sticky="nsew")
        self.download_scroll_frame.grid_columnconfigure(0, weight=1)

        self.download_tab = DownloadTab(
            self.download_scroll_frame,
            downloader=self._downloader,
            config_manager=self._config_manager,
            platform_manager=self._platform_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            queue_paused_getter=self._queue_paused_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            use_embedded_workspace_source_bar=True,
            embedded_source_getter=self.get_source_text,
            embedded_source_setter=self.set_source_text,
            embedded_source_focus=self.focus_source_input,
            fg_color=Colors.BG_PRIMARY,
        )
        self.download_tab.pack(fill="x", expand=True)

        self.torrent_tab = TorrentTab(
            self.content_host,
            config_manager=self._config_manager,
            toast_manager_getter=self._toast_manager_getter,
            use_embedded_workspace_source_bar=True,
            fg_color=Colors.BG_PRIMARY,
        )
        self.torrent_tab.grid(row=0, column=0, sticky="nsew")

        self.select_mode("url")
        self.set_output_surface("video")
        initial_height = self.winfo_height()
        self._apply_workspace_layout_profile(initial_height if initial_height > 100 else 900)
        self._apply_workspace_state()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def refresh_i18n(self) -> None:
        source_text = self.get_source_text()
        override_key = self._source_override_key
        media_output_key = self._media_output_key
        for child in list(self.winfo_children()):
            child.destroy()
        self._override_value_to_key = {}
        self._media_output_value_to_key = {}
        self._build_ui()
        self._source_override_key = override_key
        self._media_output_key = media_output_key
        self.set_source_text(source_text)
        self._set_override_selector_value(override_key)
        self._set_media_output_selector_value(media_output_key)
        self._apply_workspace_state()

    def select_mode(self, mode_key: str) -> None:
        normalized_override = self._normalize_override_key(mode_key)
        self._source_override_key = normalized_override
        self._set_override_selector_value(normalized_override)
        self._apply_workspace_state()

    def set_output_surface(self, output_key: str) -> None:
        normalized = output_key if output_key in self._MEDIA_OUTPUT_KEYS else "video"
        self._media_output_key = normalized
        self._set_media_output_selector_value(normalized)
        if self.download_tab is not None and hasattr(self.download_tab, "set_output_surface"):
            self.download_tab.set_output_surface(normalized)

    def get_source_text(self) -> str:
        return self.source_textbox.get("1.0", "end").rstrip("\n")

    def set_source_text(self, value: str, _event=None) -> None:
        self.source_textbox.delete("1.0", "end")
        if value:
            self.source_textbox.insert("1.0", value)
        self._apply_workspace_state()

    def focus_source_input(self) -> None:
        self.source_textbox.focus_set()

    def apply_detected_source_text(self, value: str) -> None:
        self._source_override_key = "auto"
        self._set_override_selector_value("auto")
        self.set_source_text(value)

    def set_status_text(self, text: str) -> None:
        if self.download_tab is not None and hasattr(self.download_tab, "set_status_text"):
            self.download_tab.set_status_text(text)

    # ------------------------------------------------------------------
    # Internal state coordination
    # ------------------------------------------------------------------

    def _build_override_values(self) -> list[str]:
        labels = [
            (t("download.workspaceOverrideAuto"), "auto"),
            (t("download.workspaceOverrideMedia"), "media"),
            (t("download.workspaceOverridePlaylist"), "playlist"),
            (t("download.workspaceOverrideBatch"), "batch"),
            (t("download.workspaceOverrideTorrent"), "torrent"),
        ]
        self._override_value_to_key = {label: key for label, key in labels}
        return [label for label, _key in labels]

    def _build_media_output_values(self) -> list[str]:
        labels = [
            (t("download.modeVideo"), "video"),
            (t("download.qualityAudioOnly"), "audio"),
        ]
        self._media_output_value_to_key = {label: key for label, key in labels}
        return [label for label, _key in labels]

    def _set_override_selector_value(self, override_key: str) -> None:
        label = next((value for value, key in self._override_value_to_key.items() if key == override_key), None)
        if label and self.mode_selector.get() != label:
            self.mode_selector.set(label)

    def _set_media_output_selector_value(self, output_key: str) -> None:
        label = next((value for value, key in self._media_output_value_to_key.items() if key == output_key), None)
        if label and self.media_output_selector.get() != label:
            self.media_output_selector.set(label)

    def _on_override_selected(self, selected_label: str) -> None:
        self._source_override_key = self._override_value_to_key.get(selected_label, "auto")
        self._apply_workspace_state()

    def _on_media_output_selected(self, selected_label: str) -> None:
        self.set_output_surface(self._media_output_value_to_key.get(selected_label, "video"))

    def _on_preset_selected(self, selected_label: str) -> None:
        pass  # Will coordinate with DownloadTab for advanced preset logic
        
    def _preview_source(self) -> None:
        source_text = self.get_source_text()
        if not source_text:
            return
        if self.download_tab is not None and hasattr(self.download_tab, "set_status_text"):
            self.download_tab.set_status_text("Önizleme yükleniyor...")
            # Trigger analysis
            self.download_tab._start_analysis()

    def _on_source_text_changed(self, _event=None) -> None:
        self._apply_workspace_state()

    def _browse_torrent_source(self) -> None:
        path = filedialog.askopenfilename(
            title=t("download.workspaceSourceBrowseTorrent"),
            filetypes=[("Torrent files", "*.torrent"), ("All files", "*.*")],
        )
        if not path:
            return
        self._source_override_key = "auto"
        self._set_override_selector_value("auto")
        self.set_source_text(str(Path(path)))

    def _apply_workspace_state(self) -> None:
        source_text = self.get_source_text()
        self._detected_mode_key = self._classify_source_text(source_text)
        effective_mode = self._resolve_effective_mode_key()
        self._active_mode_key = effective_mode

        if self.download_tab is not None and hasattr(self.download_tab, "set_embedded_source_text"):
            self.download_tab.set_embedded_source_text(source_text)
        if self.torrent_tab is not None and hasattr(self.torrent_tab, "set_source_text"):
            self.torrent_tab.set_source_text(source_text)

        self._update_detected_source_badge(effective_mode)
        self._update_source_helper_text(effective_mode)
        self._show_effective_panel(effective_mode)

        if effective_mode == "torrent":
            self.media_output_row.pack_forget()
            return

        if not self.media_output_row.winfo_manager():
            self.media_output_row.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.SM), before=self.guide_panel)
        self.set_output_surface(self._media_output_key)
        self._sync_standard_mode(effective_mode)

    def _resolve_effective_mode_key(self) -> str:
        override = self._source_override_key
        if override == "auto":
            return self._detected_mode_key
        if override == "media":
            return "url"
        return override

    def _normalize_override_key(self, mode_key: str) -> str:
        normalized = str(mode_key or "url").strip().lower()
        if normalized == "url":
            return "media"
        if normalized in self._OVERRIDE_KEYS:
            return normalized
        if normalized in {"video", "audio"}:
            return "media"
        return "media"

    def _classify_source_text(self, source_text: str) -> str:
        normalized = str(source_text or "").strip()
        if not normalized:
            return "url"

        lines = [line.strip() for line in normalized.splitlines() if line.strip()]
        if len(lines) > 1:
            return "batch"

        lowered = normalized.lower()
        if lowered.startswith("magnet:?"):
            return "torrent"

        normalized_path = lowered.split("?", 1)[0]
        if normalized_path.endswith(".torrent"):
            return "torrent"

        if DownloadTab._looks_like_playlist_url(normalized):
            return "playlist"
        return "url"

    def _update_detected_source_badge(self, effective_mode: str) -> None:
        badge_key = {
            "url": "download.workspaceDetectedMedia",
            "playlist": "download.workspaceDetectedPlaylist",
            "batch": "download.workspaceDetectedBatch",
            "torrent": "download.workspaceDetectedTorrent",
        }.get(self._detected_mode_key, "download.workspaceDetectedMedia")
        active_color = {
            "url": Colors.BTN_SECONDARY,
            "playlist": Colors.ACCENT,
            "batch": Colors.BTN_SECONDARY_HOVER,
            "torrent": Colors.WARNING_BG,
        }.get(effective_mode, Colors.BTN_SECONDARY)
        self.detected_source_badge.configure(text=t(badge_key), fg_color=active_color)

    def _update_source_helper_text(self, effective_mode: str) -> None:
        helper_key = {
            "url": "download.workspaceSourceHintMedia",
            "playlist": "download.workspaceSourceHintPlaylist",
            "batch": "download.workspaceSourceHintBatch",
            "torrent": "download.workspaceSourceHintTorrent",
        }.get(effective_mode, "download.workspaceSourceHintMedia")
        self.source_helper_label.configure(text=t(helper_key))

    def _show_effective_panel(self, mode_key: str) -> None:
        if mode_key == "torrent":
            self._show_mode_frame(self.torrent_tab, self.download_scroll_frame)
            return
        self._show_mode_frame(self.download_scroll_frame, self.torrent_tab)

    def _show_mode_frame(self, active_frame, inactive_frame) -> None:
        content_host = getattr(self, "content_host", None)
        if content_host is not None:
            if hasattr(inactive_frame, "grid_remove"):
                try:
                    inactive_frame.grid_remove()
                except Exception:
                    pass

            if hasattr(active_frame, "winfo_manager") and hasattr(active_frame, "grid"):
                try:
                    if active_frame.winfo_manager() != "grid":
                        active_frame.grid(row=0, column=0, sticky="nsew")
                except Exception:
                    pass

            if hasattr(active_frame, "tkraise"):
                try:
                    active_frame.tkraise()
                except Exception:
                    pass
            return

        if hasattr(inactive_frame, "pack_forget"):
            inactive_frame.pack_forget()
        if hasattr(active_frame, "pack"):
            active_frame.pack(fill="both", expand=True)

    def _sync_standard_mode(self, mode_key: str) -> None:
        if self.download_tab is None:
            return

        if hasattr(self.download_tab, "set_workspace_mode"):
            self.download_tab.set_workspace_mode(mode_key)

        if mode_key == "playlist":
            self.download_tab.set_status_text(t("download.workspacePlaylistHint"))
        elif mode_key == "batch":
            self.download_tab.set_status_text(t("download.workspaceBatchHint"))
        else:
            self.download_tab.set_status_text(t("download.workspaceUrlHint"))

    # ------------------------------------------------------------------
    # Layout adaptation
    # ------------------------------------------------------------------

    def _on_workspace_resize(self, event) -> None:
        height = getattr(event, "height", None) or self.winfo_height() or 900
        if int(height or 0) <= 0:
            height = 900
        self._apply_workspace_layout_profile(int(height))

    def _apply_workspace_layout_profile(self, height: int) -> None:
        compact = int(height or 0) < 860
        if compact == self._compact_layout_active:
            if hasattr(self.download_tab, "apply_layout_profile"):
                self.download_tab.apply_layout_profile(height=height, compact=compact)
            return

        self._compact_layout_active = compact
        if hasattr(self.guide_panel, "set_expanded") and compact:
            self.guide_panel.set_expanded(False)

        try:
            self.source_textbox.configure(height=52 if compact else 60)
        except Exception:
            pass

        if hasattr(self.download_tab, "apply_layout_profile"):
            self.download_tab.apply_layout_profile(height=height, compact=compact)
