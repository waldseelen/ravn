"""Global command palette dialog for quick navigation and actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Sequence

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Sizes, Spacing


@dataclass
class PaletteCommand:
    """Single command-palette item."""

    key: str
    title: str
    subtitle: str
    action: Callable[[], None]
    keywords: Sequence[str] = field(default_factory=tuple)

    @property
    def search_blob(self) -> str:
        parts = [self.key, self.title, self.subtitle, *self.keywords]
        return " ".join(str(part or "").casefold() for part in parts)


class _CommandRow(ctk.CTkFrame):
    def __init__(self, parent, command: PaletteCommand, on_activate: Callable[[], None]):
        super().__init__(parent, fg_color=Colors.BG_CARD, corner_radius=Sizes.CORNER_MD)
        self.command = command
        self._on_activate = on_activate

        self.grid_columnconfigure(0, weight=1)

        text_col = ctk.CTkFrame(self, fg_color="transparent")
        text_col.grid(row=0, column=0, sticky="nsew", padx=(Spacing.MD, Spacing.SM), pady=Spacing.SM)

        self.title_label = ctk.CTkLabel(
            text_col,
            text=command.title,
            font=Fonts.LABEL_BOLD,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(fill="x")

        self.subtitle_label = ctk.CTkLabel(
            text_col,
            text=command.subtitle,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=480,
        )
        self.subtitle_label.pack(fill="x", pady=(Spacing.XS, 0))

        self.key_badge = ctk.CTkLabel(
            self,
            text=command.key,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.BG_SURFACE,
            corner_radius=Sizes.CORNER_SM,
            padx=Spacing.SM,
            pady=Spacing.XS,
        )
        self.key_badge.grid(row=0, column=1, sticky="e", padx=(0, Spacing.MD), pady=Spacing.SM)

        self.bind("<Button-1>", self._handle_click)
        text_col.bind("<Button-1>", self._handle_click)
        self.title_label.bind("<Button-1>", self._handle_click)
        self.subtitle_label.bind("<Button-1>", self._handle_click)
        self.key_badge.bind("<Button-1>", self._handle_click)

    def _handle_click(self, _event=None):
        self._on_activate()

    def set_selected(self, selected: bool) -> None:
        if selected:
            self.configure(fg_color=Colors.ACCENT, border_width=1, border_color=Colors.ACCENT_HOVER)
            self.title_label.configure(text_color=Colors.BG_PRIMARY)
            self.subtitle_label.configure(text_color=Colors.BG_PRIMARY)
            self.key_badge.configure(fg_color=Colors.ACCENT_HOVER, text_color=Colors.BG_PRIMARY)
        else:
            self.configure(fg_color=Colors.BG_CARD, border_width=0, border_color=Colors.BG_CARD)
            self.title_label.configure(text_color=Colors.TEXT_PRIMARY)
            self.subtitle_label.configure(text_color=Colors.TEXT_SECONDARY)
            self.key_badge.configure(fg_color=Colors.BG_SURFACE, text_color=Colors.TEXT_PRIMARY)


class CommandPaletteDialog(ctk.CTkToplevel):
    """Keyboard-first global command palette."""

    def __init__(self, parent, commands: Iterable[PaletteCommand]):
        super().__init__(parent)
        self._all_commands: List[PaletteCommand] = list(commands)
        self._filtered_commands: List[PaletteCommand] = list(self._all_commands)
        self._command_rows: List[_CommandRow] = []
        self._selected_index = 0

        self.title(t("commandPalette.title"))
        self.geometry("780x540")
        self.minsize(700, 440)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.transient(parent)
        self.grab_set()
        self.after(10, self._focus_search)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self._build_ui()
        self._refresh_results()

    @staticmethod
    def filter_commands(commands: Iterable[PaletteCommand], query: str) -> List[PaletteCommand]:
        normalized = str(query or "").strip().casefold()
        if not normalized:
            return list(commands)
        return [command for command in commands if normalized in command.search_blob]

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

        ctk.CTkLabel(
            container,
            text=t("commandPalette.title"),
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            container,
            text=t("commandPalette.subtitle"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
        ).pack(anchor="w", pady=(Spacing.XS, Spacing.MD))

        self.search_entry = ctk.CTkEntry(
            container,
            placeholder_text=t("commandPalette.placeholder"),
            fg_color=Colors.BG_SURFACE,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_SECONDARY,
            border_color=Colors.BORDER_STRONG,
            height=Sizes.BTN_HEIGHT_LG,
            font=Fonts.LABEL,
        )
        self.search_entry.pack(fill="x", pady=(0, Spacing.MD))
        self.search_entry.bind("<KeyRelease>", self._on_query_changed)
        self.search_entry.bind("<Down>", self._on_down)
        self.search_entry.bind("<Up>", self._on_up)
        self.search_entry.bind("<Return>", self._on_execute_selected)
        self.search_entry.bind("<Escape>", lambda _event: self.close())

        self.hint_bar = ctk.CTkFrame(container, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        self.hint_bar.pack(fill="x", pady=(0, Spacing.MD))
        ctk.CTkLabel(
            self.hint_bar,
            text=t("commandPalette.hint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
        ).pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

        self.results_frame = ctk.CTkScrollableFrame(container, fg_color=Colors.BG_SURFACE)
        self.results_frame.pack(fill="both", expand=True)

    def _focus_search(self) -> None:
        try:
            self.search_entry.focus_set()
        except Exception:
            pass

    def close(self) -> None:
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()

    def _on_query_changed(self, _event=None) -> None:
        query = self.search_entry.get()
        self._filtered_commands = self.filter_commands(self._all_commands, query)
        self._selected_index = 0
        self._refresh_results()

    def _on_down(self, _event=None):
        if not self._filtered_commands:
            return "break"
        self._selected_index = min(self._selected_index + 1, len(self._filtered_commands) - 1)
        self._refresh_row_states()
        return "break"

    def _on_up(self, _event=None):
        if not self._filtered_commands:
            return "break"
        self._selected_index = max(self._selected_index - 1, 0)
        self._refresh_row_states()
        return "break"

    def _on_execute_selected(self, _event=None):
        if not self._filtered_commands:
            return "break"
        self._execute_command(self._filtered_commands[self._selected_index])
        return "break"

    def _refresh_results(self) -> None:
        for child in list(self.results_frame.winfo_children()):
            child.destroy()
        self._command_rows = []

        if not self._filtered_commands:
            ctk.CTkLabel(
                self.results_frame,
                text=t("commandPalette.noResults"),
                font=Fonts.LABEL,
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)
            return

        for command in self._filtered_commands:
            row = _CommandRow(self.results_frame, command=command, on_activate=lambda item=command: self._execute_command(item))
            row.pack(fill="x", padx=Spacing.XS, pady=Spacing.XS)
            self._command_rows.append(row)

        self._refresh_row_states()

    def _refresh_row_states(self) -> None:
        for index, row in enumerate(self._command_rows):
            row.set_selected(index == self._selected_index)

    def _execute_command(self, command: PaletteCommand) -> None:
        self.close()
        command.action()
