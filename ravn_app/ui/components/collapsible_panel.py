"""Reusable collapsible panel for progressive disclosure patterns."""

from __future__ import annotations

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Sizes, Spacing


class CollapsiblePanel(ctk.CTkFrame):
    """Simple collapsible content container."""

    def __init__(self, parent, title: str, subtitle: str = "", expanded: bool = False, **kwargs):
        kwargs.setdefault("fg_color", Colors.BG_SURFACE)
        super().__init__(parent, **kwargs)
        self.configure(corner_radius=Sizes.CORNER_MD)
        self._expanded = expanded

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

        text_col = ctk.CTkFrame(header, fg_color="transparent")
        text_col.pack(side="left", fill="x", expand=True)

        self.title_label = ctk.CTkLabel(
            text_col,
            text=title,
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.title_label.pack(anchor="w")

        self.subtitle_label = ctk.CTkLabel(
            text_col,
            text=subtitle,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        if subtitle:
            self.subtitle_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.toggle_button = ctk.CTkButton(
            header,
            text="",
            command=self.toggle,
            width=96,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BG_CARD,
            hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            cursor=Cursors.POINTER,
        )
        self.toggle_button.pack(side="right")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self._sync_state(initial=True)

    def content_frame(self):
        return self.body

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._sync_state()

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = bool(expanded)
        self._sync_state()

    def _sync_state(self, initial: bool = False) -> None:
        if self._expanded:
            self.toggle_button.configure(text=f"▾ {t('workspaceGuides.hide')}")
            if initial or not self.body.winfo_manager():
                self.body.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))
        else:
            self.toggle_button.configure(text=f"▸ {t('workspaceGuides.show')}")
            if self.body.winfo_manager():
                self.body.pack_forget()
