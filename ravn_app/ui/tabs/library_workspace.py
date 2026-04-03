"""Library workspace grouping library and history views."""

from __future__ import annotations

from typing import Any, Callable

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Fonts, Icons, Spacing
from ravn_app.ui.tabs.history_tab import HistoryTab
from ravn_app.ui.tabs.library_tab import LibraryTab


class LibraryWorkspace(ctk.CTkFrame):
    """Workspace for browsing local media and related history."""

    def __init__(
        self,
        parent,
        config_manager: Any,
        db_manager: Any,
        task_queue: Any,
        animation_manager: Any,
        toast_manager_getter: Callable[[], Any],
        show_queue_callback: Callable[[], None],
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self._config_manager = config_manager
        self._db_manager = db_manager
        self._task_queue = task_queue
        self._animation_manager = animation_manager
        self._toast_manager_getter = toast_manager_getter
        self._show_queue_callback = show_queue_callback
        self._active_view_key = "library"

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        self.title_label = ctk.CTkLabel(
            header,
            text=t("libraryWorkspace.title"),
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text=t("libraryWorkspace.subtitle"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.guide_panel = CollapsiblePanel(
            self,
            title=t("libraryWorkspace.guideTitle"),
            subtitle=t("libraryWorkspace.guideSubtitle"),
            expanded=False,
        )
        self.guide_panel.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        guide_body = self.guide_panel.content_frame()
        self._guide_labels = []
        for key in (
            "libraryWorkspace.guideLine1",
            "libraryWorkspace.guideLine2",
            "libraryWorkspace.guideLine3",
        ):
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

        self.tabview = ctk.CTkTabview(self, anchor="n")
        self.tabview.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, Spacing.LG))
        self.tabview.configure(
            segmented_button_fg_color=Colors.BG_SURFACE,
            segmented_button_selected_color=Colors.ACCENT,
            segmented_button_selected_hover_color=Colors.ACCENT_HOVER,
            segmented_button_unselected_color=Colors.BG_CARD,
            segmented_button_unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
        )

        library_tab = self.tabview.add(f"{Icons.LIBRARY}  {t('tabs.library')}")
        self.library_tab = LibraryTab(
            library_tab,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.library_tab.pack(fill="both", expand=True)

        history_tab = self.tabview.add(f"{Icons.HISTORY}  {t('tabs.history')}")
        self.history_tab = HistoryTab(history_tab, self._db_manager, fg_color=Colors.BG_PRIMARY)
        self.history_tab.pack(fill="both", expand=True)

    def refresh_i18n(self) -> None:
        active_view = self._active_view_key
        for child in list(self.winfo_children()):
            child.destroy()
        self._build_ui()
        self.select_view(active_view)

    def select_view(self, view_key: str = "library") -> None:
        mapping = {
            "library": f"{Icons.LIBRARY}  {t('tabs.library')}",
            "history": f"{Icons.HISTORY}  {t('tabs.history')}",
        }
        normalized_view = view_key if view_key in mapping else "library"
        self._active_view_key = normalized_view
        self.tabview.set(mapping[normalized_view])
