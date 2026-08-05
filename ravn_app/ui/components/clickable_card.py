"""Reusable clickable card with an icon, a bold title and muted detail text.

Replaces the older single-button `text="{title}\n{detail}"` pattern (both lines in one
font, so no visual hierarchy) used by Home quick actions and the Studio launcher. A frame
lets the title and detail carry distinct type weights, and the whole card — including its
children — is click- and keyboard-activatable with a hover state.
"""

from typing import Callable, Optional

import customtkinter as ctk

from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Sizes, Spacing


class ClickableCard(ctk.CTkFrame):
    def __init__(
        self,
        parent,
        title: str,
        detail: str,
        command: Callable[[], None],
        icon: str = "",
        height: int = 96,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", Colors.BG_SURFACE)
        kwargs.setdefault("corner_radius", Sizes.CORNER_MD)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Colors.BORDER)
        super().__init__(parent, height=height, **kwargs)
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._command = command
        self._base_color = kwargs["fg_color"]
        self._hover_color = Colors.BG_HOVER
        self.configure(cursor=Cursors.POINTER)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.SM)

        if icon:
            icon_label = ctk.CTkLabel(
                row, text=icon, font=Fonts.H2, text_color=Colors.ACCENT, width=34
            )
            icon_label.pack(side="left", padx=(0, Spacing.SM))

        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        self.title_label = ctk.CTkLabel(
            text_col, text=title, font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY,
            anchor="w", justify="left",
        )
        self.title_label.pack(fill="x", anchor="w")

        self.detail_label = ctk.CTkLabel(
            text_col, text=detail, font=Fonts.SMALL, text_color=Colors.TEXT_MUTED,
            anchor="w", justify="left", wraplength=280,
        )
        self.detail_label.pack(fill="x", anchor="w", pady=(2, 0))

        # Labels don't bubble clicks to their parent in Tk, so bind every piece.
        for widget in (self, row, text_col, self.title_label, self.detail_label):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)
        if icon:
            icon_label.bind("<Button-1>", self._on_click)
            icon_label.bind("<Enter>", self._on_enter)
            icon_label.bind("<Leave>", self._on_leave)

        # Keyboard activation for accessibility.
        self.bind("<Return>", self._on_click)
        self.bind("<space>", self._on_click)

        # Make the card reachable by Tab and show a focus ring when it has focus. Focus
        # lands on CustomTkinter's internal canvas, so bind there; guard defensively in
        # case the private attribute changes across CTk versions.
        focus_target = getattr(self, "_canvas", None)
        if focus_target is not None:
            try:
                focus_target.configure(takefocus=1)
                focus_target.bind("<FocusIn>", self._on_focus_in)
                focus_target.bind("<FocusOut>", self._on_focus_out)
                focus_target.bind("<Return>", self._on_click)
                focus_target.bind("<space>", self._on_click)
                for widget in (self, row, self.title_label, self.detail_label):
                    widget.bind("<Button-1>", lambda _e: focus_target.focus_set(), add="+")
            except Exception:
                pass

    def _on_click(self, _event=None):
        if callable(self._command):
            self._command()
        return "break"

    def _on_enter(self, _event=None):
        self.configure(fg_color=self._hover_color)

    def _on_leave(self, _event=None):
        self.configure(fg_color=self._base_color)

    def _on_focus_in(self, _event=None):
        try:
            self.configure(border_color=Colors.FOCUS_RING)
        except Exception:
            pass

    def _on_focus_out(self, _event=None):
        try:
            self.configure(border_color=Colors.BORDER)
        except Exception:
            pass

    def set_content(self, title: Optional[str] = None, detail: Optional[str] = None) -> None:
        if title is not None:
            self.title_label.configure(text=title)
        if detail is not None:
            self.detail_label.configure(text=detail)
