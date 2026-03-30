"""Reusable URL input row used by download workflows."""

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Sizes


class UrlInputRow(ctk.CTkFrame):
    """URL input with validation icon and size estimate label."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        self.url_entry = ctk.CTkEntry(
            self,
            placeholder_text=t("download.urlPlaceholder"),
            width=400,
            corner_radius=Sizes.CORNER_SM,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_MUTED,
            border_color=Colors.BORDER,
        )
        self.url_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.url_entry.configure(cursor=Cursors.TEXT)

        self.validation_icon = ctk.CTkLabel(
            self,
            text="",
            width=26,
            font=Fonts.LABEL,
        )
        self.validation_icon.pack(side="left", padx=(2, 4))

        self.size_estimate_label = ctk.CTkLabel(
            self,
            text="",
            width=100,
            font=Fonts.SMALL,
        )
        self.size_estimate_label.pack(side="left", padx=(2, 8))
