"""
RAVN - Reusable UI Components
Toast notifications, inline error labels, and other shared UI elements.
"""

import customtkinter as ctk
from typing import Optional, List, Callable
from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes, Motion, Icons


class Toast(ctk.CTkFrame):
    """
    Single toast notification widget.

    Slides in from top-right, auto-dismisses after timeout.
    """

    def __init__(
        self,
        parent,
        message: str,
        toast_type: str = "success",  # "success", "warning", "error", "info"
        duration_ms: int = 3000,
        on_dismiss: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.on_dismiss = on_dismiss
        self.duration_ms = duration_ms
        self._dismiss_after_id: Optional[str] = None
        self._animation_after_id: Optional[str] = None

        # Style based on type
        config = self._get_type_config(toast_type)

        self.configure(
            fg_color=config["bg"],
            corner_radius=Sizes.CORNER_MD,
            border_width=1,
            border_color=config["border"],
        )

        # Content frame
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        # Icon
        icon_label = ctk.CTkLabel(
            content,
            text=config["icon"],
            font=Fonts.H2,
            text_color=config["color"],
            width=24,
        )
        icon_label.pack(side="left", padx=(0, Spacing.SM))

        # Message
        msg_label = ctk.CTkLabel(
            content,
            text=message,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        msg_label.pack(side="left", fill="x", expand=True)

        # Close button
        close_btn = ctk.CTkButton(
            content,
            text=Icons.CLOSE,
            width=Sizes.BTN_HEIGHT_SM,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color="transparent",
            hover_color=config["hover"],
            text_color=Colors.TEXT_MUTED,
            font=Fonts.LABEL,
            command=self.dismiss,
        )
        close_btn.pack(side="right", padx=(Spacing.SM, 0))

        # Auto-dismiss timer
        if duration_ms > 0:
            self._dismiss_after_id = self.after(duration_ms, self.dismiss)

    def _get_type_config(self, toast_type: str) -> dict:
        """Get visual configuration for toast type."""
        configs = {
            "success": {
                "icon": Icons.SUCCESS,
                "color": Colors.SUCCESS,
                "bg": Colors.SUCCESS_BG,
                "border": Colors.SUCCESS,
                "hover": Colors.SUCCESS_HOVER,
            },
            "warning": {
                "icon": Icons.WARNING,
                "color": Colors.WARNING,
                "bg": Colors.WARNING_BG,
                "border": Colors.WARNING,
                "hover": Colors.WARNING_HOVER,
            },
            "error": {
                "icon": Icons.ERROR,
                "color": Colors.ERROR,
                "bg": Colors.ERROR_BG,
                "border": Colors.ERROR,
                "hover": Colors.ERROR_HOVER,
            },
            "info": {
                "icon": Icons.INFO,
                "color": Colors.INFO,
                "bg": Colors.INFO_BG,
                "border": Colors.ACCENT,
                "hover": Colors.ACCENT_HOVER,
            },
        }
        return configs.get(toast_type, configs["info"])

    def dismiss(self):
        """Dismiss the toast with animation."""
        if self._dismiss_after_id:
            self.after_cancel(self._dismiss_after_id)
            self._dismiss_after_id = None

        # Animate out
        self._animate_out()

    def _animate_out(self, step: int = 0):
        """Fade out animation."""
        if step >= 10:
            if self.on_dismiss:
                self.on_dismiss()
            self.destroy()
            return

        # Simple fade by reducing opacity simulation (move off-screen)
        try:
            self.place_configure(relx=1.0 + (step * 0.03))
        except Exception:
            pass

        self._animation_after_id = self.after(15, lambda: self._animate_out(step + 1))

    def destroy(self):
        """Clean up timers before destruction."""
        if self._dismiss_after_id:
            try:
                self.after_cancel(self._dismiss_after_id)
            except Exception:
                pass
        if self._animation_after_id:
            try:
                self.after_cancel(self._animation_after_id)
            except Exception:
                pass
        super().destroy()


class ToastManager:
    """
    Manages toast notifications for a window.

    Handles positioning, stacking, and lifecycle of toasts.
    Usage:
        toast_manager = ToastManager(root_window)
        toast_manager.show_success("Download complete!")
        toast_manager.show_warning("Low disk space")
    """

    TOAST_WIDTH = 320
    TOAST_MARGIN = 16
    TOAST_SPACING = 8

    def __init__(self, parent: ctk.CTk):
        self.parent = parent
        self.active_toasts: List[Toast] = []

    def show_success(self, message: str, duration_ms: int = 3000) -> Toast:
        """Show success toast (green, default 3s)."""
        return self._show_toast(message, "success", duration_ms)

    def show_warning(self, message: str, duration_ms: int = 4000) -> Toast:
        """Show warning toast (amber, default 4s)."""
        return self._show_toast(message, "warning", duration_ms)

    def show_error(self, message: str, duration_ms: int = 5000) -> Toast:
        """Show error toast (red, default 5s)."""
        return self._show_toast(message, "error", duration_ms)

    def show_info(self, message: str, duration_ms: int = 3000) -> Toast:
        """Show info toast (kahverengi, default 3s)."""
        return self._show_toast(message, "info", duration_ms)

    def _show_toast(self, message: str, toast_type: str, duration_ms: int) -> Toast:
        """Create and position a new toast."""
        toast = Toast(
            self.parent,
            message=message,
            toast_type=toast_type,
            duration_ms=duration_ms,
            on_dismiss=lambda: self._on_toast_dismissed(toast),
        )

        self.active_toasts.append(toast)
        self._reposition_toasts()

        # Animate in
        self._animate_toast_in(toast)

        return toast

    def _animate_toast_in(self, toast: Toast, step: int = 0):
        """Slide toast in from right."""
        if step >= 10:
            return

        # Start off-screen, slide to position
        progress = step / 10.0
        # Ease-out cubic
        eased = 1 - (1 - progress) ** 3

        x_offset = 1.0 - (eased * 0.02)  # Slight overshoot effect
        try:
            toast.place_configure(relx=x_offset - 0.02)
        except Exception:
            return

        toast.after(16, lambda: self._animate_toast_in(toast, step + 1))

    def _on_toast_dismissed(self, toast: Toast):
        """Handle toast dismissal."""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            self._reposition_toasts()

    def _reposition_toasts(self):
        """Reposition all active toasts vertically."""
        y_offset = self.TOAST_MARGIN

        for toast in self.active_toasts:
            try:
                toast.place(
                    relx=1.0,
                    x=-self.TOAST_MARGIN - self.TOAST_WIDTH,
                    y=y_offset,
                    width=self.TOAST_WIDTH,
                )
                y_offset += toast.winfo_reqheight() + self.TOAST_SPACING
            except Exception:
                pass

    def dismiss_all(self):
        """Dismiss all active toasts."""
        for toast in self.active_toasts[:]:
            toast.dismiss()


class InlineErrorLabel(ctk.CTkFrame):
    """
    Inline error message below form fields.

    Shows red icon + error text with fade-in animation.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._after_id: Optional[str] = None
        self._visible = False

        # Icon
        self.icon_label = ctk.CTkLabel(
            self,
            text=Icons.ERROR_INDICATOR,
            font=Fonts.SMALL,
            text_color=Colors.ERROR,
            width=16,
        )
        self.icon_label.pack(side="left", padx=(0, 4))

        # Error message
        self.message_label = ctk.CTkLabel(
            self,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.ERROR,
            anchor="w",
        )
        self.message_label.pack(side="left", fill="x", expand=True)

        # Initially hidden
        self.pack_forget()

    def show(self, message: str, animate: bool = True):
        """Show error message with optional fade-in."""
        self.message_label.configure(text=message)
        self._visible = True

        if animate:
            # Start with low opacity simulation
            self.icon_label.configure(text_color=Colors.BG_PRIMARY)
            self.message_label.configure(text_color=Colors.BG_PRIMARY)
            self.pack(fill="x", pady=(4, 0))
            self._animate_fade_in(0)
        else:
            self.icon_label.configure(text_color=Colors.ERROR)
            self.message_label.configure(text_color=Colors.ERROR)
            self.pack(fill="x", pady=(4, 0))

    def _animate_fade_in(self, step: int):
        """Animate text color from bg to error color."""
        if step >= 10:
            self.icon_label.configure(text_color=Colors.ERROR)
            self.message_label.configure(text_color=Colors.ERROR)
            return

        progress = step / 10.0
        # Interpolate colors
        color = self._interpolate_color(Colors.BG_PRIMARY, Colors.ERROR, progress)

        self.icon_label.configure(text_color=color)
        self.message_label.configure(text_color=color)

        self._after_id = self.after(15, lambda: self._animate_fade_in(step + 1))

    def hide(self, animate: bool = True):
        """Hide error message."""
        self._visible = False

        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

        self.pack_forget()

    @staticmethod
    def _interpolate_color(start: str, end: str, progress: float) -> str:
        """Interpolate between two hex colors."""
        def hex_to_rgb(hex_color: str) -> tuple:
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(r: int, g: int, b: int) -> str:
            return f"#{r:02x}{g:02x}{b:02x}"

        sr, sg, sb = hex_to_rgb(start)
        er, eg, eb = hex_to_rgb(end)

        r = int(sr + (er - sr) * progress)
        g = int(sg + (eg - sg) * progress)
        b = int(sb + (eb - sb) * progress)

        return rgb_to_hex(r, g, b)

    def destroy(self):
        """Clean up timer."""
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()


class FormFieldWithError(ctk.CTkFrame):
    """
    Form field container with integrated error display.

    Includes left border indicator for error state (POL-19).
    """

    def __init__(
        self,
        parent,
        label_text: str = "",
        placeholder: str = "",
        validate_on_blur: bool = True,
        validator: Optional[Callable[[str], Optional[str]]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.validator = validator
        self._has_error = False

        # Left border indicator (initially hidden)
        self.error_border = ctk.CTkFrame(
            self,
            width=3,
            fg_color=Colors.ERROR,
            corner_radius=2,
        )

        # Content frame
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="left", fill="both", expand=True)

        # Label
        if label_text:
            self.label = ctk.CTkLabel(
                self.content,
                text=label_text,
                font=Fonts.LABEL,
                anchor="w",
            )
            self.label.pack(fill="x")

        # Entry
        self.entry = ctk.CTkEntry(
            self.content,
            placeholder_text=placeholder,
            height=Sizes.INPUT_HEIGHT,
            corner_radius=Sizes.CORNER_SM,
        )
        self.entry.pack(fill="x", pady=(4, 0))

        # Inline error
        self.error_label = InlineErrorLabel(self.content)

        # Bind validation on blur
        if validate_on_blur and validator:
            self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_focus_out(self, event=None):
        """Validate on focus out."""
        self.validate()

    def validate(self) -> bool:
        """
        Run validation and update error state.

        Returns True if valid, False if invalid.
        """
        if not self.validator:
            return True

        value = self.entry.get()
        error_message = self.validator(value)

        if error_message:
            self.show_error(error_message)
            return False
        else:
            self.clear_error()
            return True

    def show_error(self, message: str):
        """Show error state with border and message."""
        self._has_error = True

        # Show left border
        self.error_border.pack(side="left", fill="y", padx=(0, 8))

        # Update entry border
        self.entry.configure(border_color=Colors.ERROR)

        # Show error message
        self.error_label.show(message)

    def clear_error(self):
        """Clear error state."""
        self._has_error = False

        # Hide left border
        self.error_border.pack_forget()

        # Reset entry border
        self.entry.configure(border_color=Colors.BORDER)

        # Hide error message
        self.error_label.hide()

    def get(self) -> str:
        """Get entry value."""
        return self.entry.get()

    def set(self, value: str):
        """Set entry value."""
        self.entry.delete(0, "end")
        self.entry.insert(0, value)


class Tooltip:
    """
    Tooltip for UI elements (POL-34).

    Shows on hover after 300ms delay.
    """

    def __init__(
        self,
        widget,
        text: str,
        delay_ms: int = 300,
    ):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.tooltip_window = None
        self._after_id = None

        # Bind events
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        widget.bind("<ButtonPress>", self._on_leave)

    def _on_enter(self, event=None):
        """Start delay timer on hover."""
        self._cancel_timer()
        self._after_id = self.widget.after(self.delay_ms, self._show_tooltip)

    def _on_leave(self, event=None):
        """Hide tooltip and cancel timer."""
        self._cancel_timer()
        self._hide_tooltip()

    def _cancel_timer(self):
        """Cancel pending show timer."""
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show_tooltip(self):
        """Display tooltip window."""
        if self.tooltip_window:
            return

        # Get widget position
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4

        # Create tooltip window
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        # Tooltip content
        label = ctk.CTkLabel(
            self.tooltip_window,
            text=self.text,
            font=Fonts.SMALL,
            fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_SM,
            padx=Spacing.SM,
            pady=Spacing.XS,
        )
        label.pack()

        # Prevent tooltip from stealing focus
        self.tooltip_window.wm_attributes("-topmost", True)

    def _hide_tooltip(self):
        """Hide tooltip window."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

    def update_text(self, text: str):
        """Update tooltip text."""
        self.text = text


class EmptyStateWidget(ctk.CTkFrame):
    """
    Empty state placeholder with icon and message (POL-25).
    """

    def __init__(
        self,
        parent,
        icon: str = Icons.FILE,
        message: str = "Henüz içerik yok",
        action_text: str = "",
        on_action: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Center container
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.5, anchor="center")

        # Icon
        icon_label = ctk.CTkLabel(
            center,
            text=icon,
            font=ctk.CTkFont(size=48),
            text_color=Colors.TEXT_MUTED,
        )
        icon_label.pack(pady=(0, Spacing.MD))

        # Message
        msg_label = ctk.CTkLabel(
            center,
            text=message,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_SECONDARY,
        )
        msg_label.pack()

        # Action button (optional)
        if action_text and on_action:
            action_btn = ctk.CTkButton(
                center,
                text=action_text,
                command=on_action,
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_HOVER,
                font=Fonts.LABEL,
                height=Sizes.BTN_HEIGHT_MD,
            )
            action_btn.pack(pady=(Spacing.MD, 0))


class LoadingSkeleton(ctk.CTkFrame):
    """
    Loading skeleton placeholder with shimmer effect (POL-26).
    """

    def __init__(
        self,
        parent,
        height: int = 60,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.configure(
            fg_color=Colors.BG_CARD,
            corner_radius=Sizes.CORNER_MD,
            height=height,
        )
        self._shimmer_after_id = None
        self._shimmer_position = 0

        # Inner shimmer element
        self.shimmer = ctk.CTkFrame(
            self,
            fg_color=Colors.ACCENT_BEIGE,
            corner_radius=Sizes.CORNER_SM,
            width=80,
            height=height - 16,
        )
        self.shimmer.place(x=8, rely=0.5, anchor="w")

        # Start shimmer animation
        self._animate_shimmer()

    def _animate_shimmer(self):
        """Animate shimmer across the skeleton."""
        self._shimmer_position += 8

        width = self.winfo_width() or 200
        if self._shimmer_position > width:
            self._shimmer_position = -80

        try:
            self.shimmer.place(x=self._shimmer_position, rely=0.5, anchor="w")
        except Exception:
            return

        self._shimmer_after_id = self.after(50, self._animate_shimmer)

    def destroy(self):
        """Clean up animation."""
        if self._shimmer_after_id:
            try:
                self.after_cancel(self._shimmer_after_id)
            except Exception:
                pass
        super().destroy()


def style_combo(combo):
    """Apply standard RAVN styling to a CTkComboBox."""
    combo.configure(
        fg_color=Colors.BG_INPUT,
        button_color=Colors.ACCENT,
        button_hover_color=Colors.ACCENT_HOVER,
        dropdown_fg_color=Colors.BG_SURFACE,
        text_color=Colors.TEXT_PRIMARY,
        dropdown_text_color=Colors.TEXT_PRIMARY,
        border_color=Colors.BORDER,
    )


def style_entry(entry):
    """Apply standard RAVN styling to a CTkEntry."""
    entry.configure(
        fg_color=Colors.BG_INPUT,
        text_color=Colors.TEXT_PRIMARY,
        placeholder_text_color=Colors.TEXT_MUTED,
        border_color=Colors.BORDER,
    )


def bind_focus_ring(widget):
    """Bind focus-in/out events to animate the border color."""
    def on_focus_in(event=None):
        try:
            widget.configure(border_color=Colors.ACCENT)
        except Exception:
            pass

    def on_focus_out(event=None):
        try:
            widget.configure(border_color=Colors.BORDER)
        except Exception:
            pass

    widget.bind("<FocusIn>", on_focus_in)
    widget.bind("<FocusOut>", on_focus_out)


def set_button_loading_state(button, is_loading: bool, loading_text: str = None, original_text: str = None):
    """
    Set a button to loading or normal state.

    Args:
        button: CTkButton widget
        is_loading: True to show loading state, False to restore
        loading_text: Text to show during loading (optional, defaults to spinner + "...")
        original_text: Text to restore when not loading (required if is_loading=False)
    """
    if button is None:
        return
    try:
        if is_loading:
            button._original_text = button.cget("text") if not hasattr(button, '_original_text') else button._original_text
            button.configure(
                text=loading_text or f"{Icons.SPINNER} ...",
                state="disabled",
                fg_color=Colors.BTN_DISABLED,
                text_color=Colors.TEXT_MUTED,
            )
        else:
            text = original_text or getattr(button, '_original_text', button.cget("text"))
            button.configure(
                text=text,
                state="normal",
                fg_color=Colors.ACCENT,
                text_color=Colors.TEXT_PRIMARY,
            )
    except Exception:
        pass
