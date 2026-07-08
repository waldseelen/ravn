"""Reusable playlist item row widget."""

from typing import Any, Callable, Dict

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.components.thumbnail_loader import get_thumbnail_loader
from ravn_app.ui.design_tokens import Colors, Fonts, Icons, Spacing

_THUMB_SIZE = (64, 36)  # 16:9 compact cover


class PlaylistItemRow(ctk.CTkFrame):
    """Single playlist row with a cover thumbnail, checkbox, title and detail text."""

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
        top_row.pack(fill="x", padx=Spacing.SM, pady=(3, 2))

        checkbox = ctk.CTkCheckBox(
            top_row,
            text="",
            variable=variable,
            command=on_toggle,
            font=Fonts.LABEL_BOLD,
        )
        checkbox.pack(side="left", padx=(0, 6))

        # Cover thumbnail: a fixed-size placeholder that fills in asynchronously once the
        # remote image is fetched/decoded, so the row renders instantly and never blocks.
        self.thumb_label = ctk.CTkLabel(
            top_row,
            text=Icons.PLAY if hasattr(Icons, "PLAY") else "▶",
            width=_THUMB_SIZE[0],
            height=_THUMB_SIZE[1],
            fg_color=Colors.BG_CARD,
            text_color=Colors.TEXT_MUTED,
            corner_radius=4,
        )
        self.thumb_label.pack(side="left", padx=(0, 8))
        self._request_thumbnail(entry.get("thumbnail_url", ""))

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

    def _request_thumbnail(self, url: str) -> None:
        if not url:
            return
        image = get_thumbnail_loader().request(
            url,
            _THUMB_SIZE,
            on_ready=self._apply_thumbnail,
            schedule_on_ui=self._schedule_on_ui,
        )
        if image is not None:
            self._apply_thumbnail(image)

    def _schedule_on_ui(self, fn: Callable[[], None]) -> None:
        try:
            self.after(0, fn)
        except Exception:
            # Widget already torn down between request and delivery — safe to ignore.
            pass

    def _apply_thumbnail(self, image: object) -> None:
        try:
            if self.thumb_label.winfo_exists():
                self.thumb_label.configure(image=image, text="")
        except Exception:
            pass

    def set_detail_text(self, detail_text: str):
        self.detail_label.configure(text=detail_text)
