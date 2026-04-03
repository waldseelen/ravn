"""Studio workspace grouping convert / subtitle / filters / mixer."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Fonts, Icons, Spacing
from ravn_app.ui.tabs.converter_tab import ConverterTab
from ravn_app.ui.tabs.filters_tab import FiltersTab
from ravn_app.ui.tabs.mixer_tab import MixerTab
from ravn_app.ui.tabs.subtitle_tab import SubtitleTab


class StudioWorkspace(ctk.CTkFrame):
    """Media-processing workspace composed from existing feature frames."""

    def __init__(
        self,
        parent,
        config_manager: Any,
        db_manager: Any,
        task_queue: Any,
        animation_manager: Any,
        toast_manager_getter: Callable[[], Any],
        show_queue_callback: Callable[[], None],
        notify_conversion_complete: Callable[[str], None],
        auto_add_to_library_callback: Optional[Callable[..., None]] = None,
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
        self._notify_conversion_complete = notify_conversion_complete
        self._auto_add_to_library_callback = auto_add_to_library_callback
        self._active_view_key = "convert"

        self._build_ui()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.LG, pady=(Spacing.LG, Spacing.SM))

        self.title_label = ctk.CTkLabel(
            header,
            text=t("studio.title"),
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            header,
            text=t("studio.subtitle"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.guide_panel = CollapsiblePanel(
            self,
            title=t("studio.guideTitle"),
            subtitle=t("studio.guideSubtitle"),
            expanded=False,
        )
        self.guide_panel.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
        guide_body = self.guide_panel.content_frame()
        self._guide_labels = []
        for key in ("studio.guideLine1", "studio.guideLine2", "studio.guideLine3"):
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

        convert_tab = self.tabview.add(f"{Icons.CONVERT}  {t('tabs.convert')}")
        self.converter_tab = ConverterTab(
            convert_tab,
            db_manager=self._db_manager,
            notify_callback=self._notify_conversion_complete,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.converter_tab.pack(fill="both", expand=True)

        subtitle_tab = self.tabview.add(f"{Icons.SUBTITLE}  {t('tabs.subtitle')}")
        self.subtitle_tab = SubtitleTab(subtitle_tab, fg_color=Colors.BG_PRIMARY)
        self.subtitle_tab.pack(fill="both", expand=True)

        filters_tab = self.tabview.add(f"{Icons.FILTERS}  {t('tabs.filters')}")
        self.filters_tab = FiltersTab(
            filters_tab,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.filters_tab.pack(fill="both", expand=True)

        mixer_tab = self.tabview.add(f"{Icons.MIXER}  {t('tabs.mixer')}")
        self.mixer_tab = MixerTab(
            mixer_tab,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.mixer_tab.pack(fill="both", expand=True)

    def refresh_i18n(self) -> None:
        active_view = self._active_view_key
        for child in list(self.winfo_children()):
            child.destroy()
        self._build_ui()
        self.select_view(active_view)

    def select_view(self, view_key: str = "convert") -> None:
        mapping = {
            "convert": f"{Icons.CONVERT}  {t('tabs.convert')}",
            "subtitle": f"{Icons.SUBTITLE}  {t('tabs.subtitle')}",
            "filters": f"{Icons.FILTERS}  {t('tabs.filters')}",
            "mixer": f"{Icons.MIXER}  {t('tabs.mixer')}",
        }
        normalized_view = view_key if view_key in mapping else "convert"
        self._active_view_key = normalized_view
        self.tabview.set(mapping[normalized_view])
