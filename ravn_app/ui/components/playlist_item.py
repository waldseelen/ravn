"""Reusable playlist item row widget."""

from typing import Any, Callable, Dict

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Fonts


class PlaylistItemRow(ctk.CTkFrame):
    """Single playlist row with a checkbox, title and detail text."""

    def __init__(
        self,
        parent,
        index: int,
        entry: Dict[str, Any],
        variable: ctk.BooleanVar,
        detail_text: str,
        on_toggle: Callable[[], None],
        **kwargs,
    ):
        kwargs.setdefault("fg_color", Colors.BG_SURFACE)
        super().__init__(parent, **kwargs)

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=8, pady=(3, 2))

        checkbox = ctk.CTkCheckBox(
            top_row,
            text="",
            variable=variable,
            command=on_toggle,
            font=Fonts.LABEL_BOLD,
        )
        checkbox.pack(side="left", padx=(0, 6))

        title = entry.get("title", t("common.unknown"))
        title_label = ctk.CTkLabel(
            top_row,
            text=f"{index}. {title}",
            font=Fonts.LABEL_BOLD,
            anchor="w",
            justify="left",
            text_color=Colors.TEXT_PRIMARY,
        )
        title_label.pack(side="left", fill="x", expand=True)

        detail_frame = ctk.CTkFrame(self, fg_color="transparent")
        detail_frame.pack(fill="x", padx=38, pady=(0, 3))

        self.detail_label = ctk.CTkLabel(
            detail_frame,
            text=detail_text,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            justify="left",
        )
        self.detail_label.pack(fill="x")

    def set_detail_text(self, detail_text: str):
        self.detail_label.configure(text=detail_text)
