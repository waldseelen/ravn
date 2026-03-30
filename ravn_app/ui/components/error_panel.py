"""Reusable error panel with optional technical details toggle."""

from typing import Callable, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Fonts, Icons, Motion


class ErrorPanel(ctk.CTkFrame):
    """Show user-facing errors with expandable technical details."""

    def __init__(
        self,
        parent,
        animation_manager,
        on_retry: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", Colors.ERROR_BG)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", Colors.BORDER)
        super().__init__(parent, **kwargs)

        self.animation_manager = animation_manager
        self._raw_error_visible = False

        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=5)

        self.error_message_label = ctk.CTkLabel(
            top_row,
            text="",
            text_color=Colors.ERROR,
            font=Fonts.LABEL,
            wraplength=700,
            justify="left",
        )
        self.error_message_label.pack(side="left", fill="x", expand=True)

        self.toggle_details_btn = ctk.CTkButton(
            top_row,
            text=f"{Icons.INFO} {t('errorPanel.technicalDetails')}",
            command=self.toggle_details,
            width=130,
            height=28,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL,
        )
        self.toggle_details_btn.pack(side="right", padx=5)

        self.retry_btn = ctk.CTkButton(
            top_row,
            text=f"{Icons.RETRY} {t('errorPanel.retry')}",
            command=on_retry,
            width=120,
            height=28,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            font=Fonts.SMALL,
        )
        self.retry_btn.pack(side="right", padx=5)

        self.raw_error_textbox = ctk.CTkTextbox(
            self,
            height=100,
            font=Fonts.MONO,
            text_color=Colors.TEXT_SECONDARY,
            fg_color=Colors.BG_PRIMARY,
        )

    def set_retry_callback(self, callback: Optional[Callable[[], None]]):
        """Update retry action."""
        self.retry_btn.configure(command=callback)

    def show_error(self, message: str, raw_text: str):
        """Populate the panel and make it visible."""
        self.error_message_label.configure(text=message)

        self.raw_error_textbox.configure(state="normal")
        self.raw_error_textbox.delete("1.0", "end")
        self.raw_error_textbox.insert("1.0", raw_text)
        self.raw_error_textbox.configure(state="disabled")

        if self._raw_error_visible:
            self.raw_error_textbox.pack_forget()
            self._raw_error_visible = False
            self.toggle_details_btn.configure(text=f"{Icons.INFO} Teknik Detaylar")

        self.pack(padx=15, pady=5, fill="x")
        self.animation_manager.animate_color_transition(
            self,
            "fg_color",
            Colors.BG_PRIMARY,
            Colors.ERROR_BG,
            duration=Motion.STANDARD,
        )

    def hide_error(self):
        """Hide panel if visible."""
        self.pack_forget()

    def toggle_details(self):
        """Toggle technical details area with height animation."""
        if self._raw_error_visible:
            self.animation_manager.animate_color_transition(
                self,
                "border_color",
                Colors.ACCENT,
                Colors.BORDER,
                duration=Motion.MICRO,
            )

            def hide_box():
                self.raw_error_textbox.pack_forget()
                self._raw_error_visible = False
                self.toggle_details_btn.configure(text=f"{Icons.INFO} {t('errorPanel.technicalDetails')}")

            self._animate_error_details_height(0, on_done=hide_box)
            return

        self.raw_error_textbox.pack(padx=10, pady=(0, 10), fill="x")
        self.raw_error_textbox.configure(height=1)
        self._raw_error_visible = True
        self.toggle_details_btn.configure(text=f"{Icons.CLOSE} {t('errorPanel.hide')}")
        self.animation_manager.animate_color_transition(
            self,
            "border_color",
            Colors.BORDER,
            Colors.ACCENT,
            duration=Motion.MICRO,
        )
        self._animate_error_details_height(100)

    def _animate_error_details_height(self, target_height: int, on_done=None):
        current_height = int(self.raw_error_textbox.cget("height") or 0)
        target_height = max(0, int(target_height))

        if current_height == target_height:
            if on_done:
                on_done()
            return

        direction = 1 if target_height > current_height else -1
        step = 10

        def tick():
            nonlocal current_height
            current_height += step * direction
            reached = current_height >= target_height if direction > 0 else current_height <= target_height
            if reached:
                current_height = target_height
            self.raw_error_textbox.configure(height=current_height)
            if not reached:
                self.after(16, tick)
            elif on_done:
                on_done()

        tick()
