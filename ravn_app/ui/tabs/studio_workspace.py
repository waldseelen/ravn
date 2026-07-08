"""Studio workspace: a goal-first launcher that opens one focused processing tool at a time."""

from __future__ import annotations

from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.components.clickable_card import ClickableCard
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.tabs.converter_tab import ConverterTab
from ravn_app.ui.tabs.filters_tab import FiltersTab
from ravn_app.ui.tabs.mixer_tab import MixerTab
from ravn_app.ui.tabs.subtitle_tab import SubtitleTab
from ravn_app.ui.tabs.utilities_tab import UtilitiesTab


class StudioWorkspace(ctk.CTkFrame):
    """Media-processing workspace: pick a goal, then work in a single focused tool."""

    _TOOLS = ("convert", "subtitle", "filters", "mixer", "utilities")

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
        self._active_view_key = "launcher"
        self._tool_frames: dict[str, ctk.CTkFrame] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _goal_specs(self) -> list[tuple[str, str, str, str]]:
        return [
            ("convert", Icons.CONVERT, t("tabs.convert"), t("studio.goalConvertDesc")),
            ("subtitle", Icons.SUBTITLE, t("tabs.subtitle"), t("studio.goalSubtitleDesc")),
            ("filters", Icons.FILTERS, t("tabs.filters"), t("studio.goalFiltersDesc")),
            ("mixer", Icons.MIXER, t("tabs.mixer"), t("studio.goalMixerDesc")),
            ("utilities", Icons.FILE, t("tabs.utilities"), t("studio.goalUtilitiesDesc")),
        ]

    def _build_ui(self) -> None:
        # ── Goal launcher ────────────────────────────────────────────────
        self._launcher = ctk.CTkFrame(self, fg_color="transparent")

        ctk.CTkLabel(
            self._launcher,
            text=t("studio.launcherTitle"),
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, Spacing.XS))
        ctk.CTkLabel(
            self._launcher,
            text=t("studio.launcherSubtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(0, Spacing.MD))

        grid = ctk.CTkFrame(self._launcher, fg_color="transparent")
        grid.pack(fill="x")
        for column in range(3):
            grid.grid_columnconfigure(column, weight=1)

        for index, (key, icon, title, desc) in enumerate(self._goal_specs()):
            row, column = divmod(index, 3)
            self._build_goal_card(grid, key, icon, title, desc).grid(
                row=row, column=column, sticky="nsew", padx=Spacing.SM, pady=Spacing.SM
            )

        # ── Focused tool area (hidden until a goal is chosen) ─────────────
        self._tool_area = ctk.CTkFrame(self, fg_color="transparent")

        toolbar = ctk.CTkFrame(self._tool_area, fg_color="transparent")
        toolbar.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, 0))

        self._back_button = ctk.CTkButton(
            toolbar,
            text=f"{Icons.CHEVRON_LEFT}  {t('studio.back')}",
            command=self._show_launcher,
            width=120,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            cursor=Cursors.POINTER,
        )
        self._back_button.pack(side="left")

        self._tool_title_label = ctk.CTkLabel(
            toolbar,
            text="",
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
        )
        self._tool_title_label.pack(side="left", padx=Spacing.MD)

        self._tool_host = ctk.CTkFrame(self._tool_area, fg_color=Colors.BG_PRIMARY)
        self._tool_host.pack(fill="both", expand=True, padx=Spacing.LG, pady=(Spacing.SM, Spacing.LG))
        self._tool_host.grid_rowconfigure(0, weight=1)
        self._tool_host.grid_columnconfigure(0, weight=1)

        self.converter_tab = ConverterTab(
            self._tool_host,
            db_manager=self._db_manager,
            notify_callback=self._notify_conversion_complete,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.subtitle_tab = SubtitleTab(
            self._tool_host,
            config_manager=self._config_manager,
            fg_color=Colors.BG_PRIMARY,
        )
        self.filters_tab = FiltersTab(
            self._tool_host,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.mixer_tab = MixerTab(
            self._tool_host,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )
        self.utilities_tab = UtilitiesTab(
            self._tool_host,
            config_manager=self._config_manager,
            db_manager=self._db_manager,
            task_queue=self._task_queue,
            animation_manager=self._animation_manager,
            toast_manager_getter=self._toast_manager_getter,
            show_queue_tab_callback=self._show_queue_callback,
            auto_add_to_library_callback=self._auto_add_to_library_callback,
            fg_color=Colors.BG_PRIMARY,
        )

        self._tool_frames = {
            "convert": self.converter_tab,
            "subtitle": self.subtitle_tab,
            "filters": self.filters_tab,
            "mixer": self.mixer_tab,
            "utilities": self.utilities_tab,
        }
        for frame in self._tool_frames.values():
            frame.grid(row=0, column=0, sticky="nsew")

        self._tool_titles = {
            "convert": t("tabs.convert"),
            "subtitle": t("tabs.subtitle"),
            "filters": t("tabs.filters"),
            "mixer": t("tabs.mixer"),
            "utilities": t("tabs.utilities"),
        }

        # Restore whatever was active (defaults to the launcher).
        if self._active_view_key in self._tool_frames:
            self.select_view(self._active_view_key)
        else:
            self._show_launcher()

    def _build_goal_card(self, parent, key: str, icon: str, title: str, desc: str) -> ClickableCard:
        return ClickableCard(
            parent,
            title=title,
            detail=desc,
            command=lambda k=key: self.select_view(k),
            icon=icon,
            height=104,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh_i18n(self) -> None:
        active_view = self._active_view_key
        for child in list(self.winfo_children()):
            child.destroy()
        self._active_view_key = active_view
        self._build_ui()

    def select_view(self, view_key: str = "convert") -> None:
        if view_key == "launcher":
            self._show_launcher()
            return
        if view_key not in self._tool_frames:
            view_key = "convert"
        self._active_view_key = view_key

        if self._launcher.winfo_manager():
            self._launcher.pack_forget()
        if not self._tool_area.winfo_manager():
            self._tool_area.pack(fill="both", expand=True)

        self._tool_frames[view_key].tkraise()
        self._tool_title_label.configure(text=self._tool_titles.get(view_key, ""))

    def _show_launcher(self) -> None:
        self._active_view_key = "launcher"
        if self._tool_area.winfo_manager():
            self._tool_area.pack_forget()
        if not self._launcher.winfo_manager():
            self._launcher.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)
