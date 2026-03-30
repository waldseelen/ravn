"""
Animation Manager - Centralized animation utilities for smooth UI transitions.

Provides easing functions, button state animations, spinners, and micro-interactions.
All animations use CustomTkinter's after() loop for 60fps smooth transitions.
Respects system reduced-motion preferences (POL-31).
"""

import math
import os
import sys
from typing import Any, Callable, Optional
import customtkinter as ctk


def detect_reduced_motion() -> bool:
    """
    Detect if user prefers reduced motion (POL-31).
    
    Checks platform-specific settings:
    - Windows: SystemParametersInfo for SPI_GETCLIENTAREAANIMATION
    - macOS: NSWorkspace accessibilityDisplayShouldReduceMotion
    - Linux: GTK/GNOME reduced-motion setting
    
    Returns True if reduced motion is preferred.
    """
    # Check environment variable override first
    env_val = os.environ.get("RAVN_REDUCED_MOTION", "").lower()
    if env_val in ("1", "true", "yes"):
        return True
    if env_val in ("0", "false", "no"):
        return False
    
    if sys.platform == "win32":
        try:
            import ctypes
            # SPI_GETCLIENTAREAANIMATION = 0x1042
            result = ctypes.c_bool()
            ctypes.windll.user32.SystemParametersInfoW(
                0x1042, 0, ctypes.byref(result), 0
            )
            # If animations are disabled, return True for reduced motion
            return not result.value
        except Exception:
            pass
    
    elif sys.platform == "darwin":
        try:
            # macOS: check accessibility setting
            from subprocess import run, PIPE
            result = run(
                ["defaults", "read", "-g", "reduceMotion"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() == "1"
        except Exception:
            pass
    
    else:
        # Linux: check GNOME/GTK setting
        try:
            from subprocess import run
            result = run(
                ["gsettings", "get", "org.gnome.desktop.interface", "enable-animations"],
                capture_output=True,
                text=True,
            )
            return result.stdout.strip().lower() == "false"
        except Exception:
            pass
    
    return False


class EasingFunction:
    """Cubic easing curves for smooth animations."""

    @staticmethod
    def ease_out(t: float) -> float:
        """
        Ease-out cubic: fast start, slow end.
        Used for entering animations and state changes.

        Args:
            t: Progress 0.0 → 1.0

        Returns:
            Eased progress value
        """
        t = min(1.0, max(0.0, t))
        return 1 - (1 - t) ** 3

    @staticmethod
    def ease_in(t: float) -> float:
        """
        Ease-in cubic: slow start, fast end.
        Used for exiting animations.

        Args:
            t: Progress 0.0 → 1.0

        Returns:
            Eased progress value
        """
        t = min(1.0, max(0.0, t))
        return t ** 3

    @staticmethod
    def ease_in_out(t: float) -> float:
        """
        Ease-in-out cubic: slow start and end, fast middle.
        Used for smooth transitions between states.

        Args:
            t: Progress 0.0 → 1.0

        Returns:
            Eased progress value
        """
        t = min(1.0, max(0.0, t))
        if t < 0.5:
            return 4 * t ** 3
        else:
            return 1 - (-2 * t + 2) ** 3 / 2


class AnimationManager:
    """
    Centralized animation controller for CustomTkinter UI.

    Manages smooth state transitions with consistent timing and easing.
    All animations use 60fps frame rate (16ms per frame).
    Respects reduced-motion preference (POL-31).
    """

    # Animation timing constants (milliseconds)
    DURATION_MICRO = 150      # Micro-interactions (button press, focus)
    DURATION_STANDARD = 200   # Standard transitions (fade, slide)
    DURATION_LONG = 300       # Long transitions (modal open, tab switch)
    FRAME_TIME = 16          # 60fps = 16ms per frame

    def __init__(self):
        self._active_animations = {}  # widget_id -> (widget, after_id)
        self._reduced_motion: Optional[bool] = None  # Cached preference

    @property
    def reduced_motion(self) -> bool:
        """Check if reduced motion is preferred (cached)."""
        if self._reduced_motion is None:
            self._reduced_motion = detect_reduced_motion()
        return self._reduced_motion

    def set_reduced_motion(self, enabled: bool) -> None:
        """Override reduced motion setting programmatically."""
        self._reduced_motion = enabled

    def should_animate(self) -> bool:
        """Return False if animations should be skipped."""
        return not self.reduced_motion

    def animate_button_disabled(
        self,
        button: ctk.CTkButton,
        duration: int = DURATION_MICRO,
        target_opacity: float = 0.5
    ) -> None:
        """
        Animate button to disabled state with opacity reduction.

        Reduces opacity (gray out) to indicate disabled state without jarring
        instant state change. Preserves button dimensions.
        Respects reduced-motion preference.

        Args:
            button: CTkButton to animate
            duration: Animation duration in milliseconds
            target_opacity: Final opacity (0.0-1.0), default 0.5 for 50% gray
        """
        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            button.configure(text_color="#4b5563")  # TEXT_DISABLED
            return

        widget_id = id(button)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_opacity = 1.0
        start_time = [None]
        original_text_color = getattr(button, "_text_color", "#f1f5f9") or "#f1f5f9"

        def animate_frame():
            if start_time[0] is None:
                start_time[0] = 0
            else:
                start_time[0] += self.FRAME_TIME

            progress = min(1.0, start_time[0] / duration)
            eased = EasingFunction.ease_out(progress)
            current_opacity = start_opacity - (start_opacity - target_opacity) * eased

            # Fade text color to gray
            if original_text_color:
                r, g, b = self._hex_to_rgb(original_text_color)
                gray = int(r * current_opacity + 128 * (1 - current_opacity))
                faded_color = self._rgb_to_hex(gray, gray, gray)
                button.configure(text_color=faded_color)

            if progress < 1.0:
                after_id = button.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (button, after_id)
            else:
                # Ensure final state
                button.configure(text_color="#4b5563")  # TEXT_DISABLED
                self._active_animations.pop(widget_id, None)

        animate_frame()

    def animate_button_enabled(
        self,
        button: ctk.CTkButton,
        duration: int = DURATION_MICRO,
        target_color: str = "#f1f5f9"  # TEXT_PRIMARY
    ) -> None:
        """
        Animate button back to enabled state with opacity increase.

        Restores opacity to indicate button is interactive again.
        Respects reduced-motion preference.

        Args:
            button: CTkButton to animate
            duration: Animation duration in milliseconds
            target_color: Final text color (hex)
        """
        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            button.configure(text_color=target_color)
            return

        widget_id = id(button)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_opacity = 0.5
        start_time = [None]

        def animate_frame():
            if start_time[0] is None:
                start_time[0] = 0
            else:
                start_time[0] += self.FRAME_TIME

            progress = min(1.0, start_time[0] / duration)
            eased = EasingFunction.ease_out(progress)
            current_opacity = start_opacity + (1.0 - start_opacity) * eased

            # Restore text color
            r, g, b = self._hex_to_rgb(target_color)
            brightened = int(r * current_opacity + 128 * (1 - current_opacity))
            updated_color = self._rgb_to_hex(brightened, brightened, brightened)
            button.configure(text_color=updated_color)

            if progress < 1.0:
                after_id = button.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (button, after_id)
            else:
                button.configure(text_color=target_color)
                self._active_animations.pop(widget_id, None)

        animate_frame()

    def create_spinner_animation(
        self,
        label: ctk.CTkLabel,
        duration: int = DURATION_STANDARD,
        fps: int = 3
    ) -> Callable[[], None]:
        """
        Create animated spinner for loading states.

        Returns a function that animates a spinner icon in the label.
        Call the returned function repeatedly or in a loop.

        Args:
            label: CTkLabel to show spinner
            duration: Total animation duration in milliseconds
            fps: Frames per second (rotations/second)

        Returns:
            Callable that updates spinner frame
        """
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_index = [0]

        def update_spinner():
            frame_index[0] = (frame_index[0] + 1) % len(spinner_frames)
            label.configure(text=spinner_frames[frame_index[0]])

        return update_spinner

    def start_spinner_loop(
        self,
        label: ctk.CTkLabel,
        duration: Optional[int] = None,
        fps: int = 3
    ) -> str:
        """
        Start animated spinner loop.

        Continuously rotates spinner icon. Store returned ID to stop animation.

        Args:
            label: CTkLabel to show spinner
            duration: Optional duration in milliseconds. If None, runs indefinitely.
            fps: Frames per second

        Returns:
            Animation ID for stopping via stop_animation()
        """
        spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        frame_index = [0]
        start_time = [None]
        widget_id = id(label)

        frame_interval = int(1000 / max(1, fps))

        def animate_spinner():
            if start_time[0] is None:
                start_time[0] = 0
            else:
                start_time[0] += frame_interval

            # Check if duration exceeded
            if duration and start_time[0] >= duration:
                label.configure(text="✓")  # Show success checkmark
                self._active_animations.pop(widget_id, None)
                return

            frame_index[0] = (frame_index[0] + 1) % len(spinner_frames)
            label.configure(text=spinner_frames[frame_index[0]])

            after_id = label.after(frame_interval, animate_spinner)
            self._active_animations[widget_id] = (label, after_id)

        animate_spinner()
        return str(widget_id)

    def stop_animation(self, animation_id: str) -> None:
        """
        Stop a running animation by ID.

        Args:
            animation_id: ID returned from start_spinner_loop() or similar
        """
        try:
            widget_id = int(animation_id)
            if widget_id in self._active_animations:
                self._cancel_animation(widget_id)
        except (ValueError, KeyError):
            pass

    def _cancel_animation(self, widget_id: int) -> None:
        """Internal helper to cancel animation by widget ID."""
        if widget_id in self._active_animations:
            data = self._active_animations.pop(widget_id)
            widget = None
            after_id = None

            if isinstance(data, tuple) and len(data) == 2:
                widget, after_id = data
            else:
                # Backward compatibility for old dict payloads
                after_id = data

            try:
                if widget is not None and after_id is not None:
                    widget.after_cancel(after_id)
            except Exception:
                pass

    @staticmethod
    def smooth_progress(current: float, target: float, max_step: float = 0.08) -> float:
        """
        Move progress value toward target smoothly.

        Args:
            current: Current progress in [0, 1]
            target: Target progress in [0, 1]
            max_step: Maximum change per update call

        Returns:
            Next progress value in [0, 1]
        """
        current = min(1.0, max(0.0, float(current)))
        target = min(1.0, max(0.0, float(target)))
        max_step = max(0.001, float(max_step))

        if math.isclose(current, target, abs_tol=0.001):
            return target

        if target > current:
            return min(target, current + max_step)

        return max(target, current - max_step)

    @staticmethod
    def format_processing_text(base_text: str, tick: int) -> str:
        """Build animated processing text with looping ellipsis."""
        dots = "." * ((int(tick) % 3) + 1)
        return f"{base_text}{dots}"

    def animate_focus_ring(
        self,
        widget: Any,
        focused: bool,
        duration: int = DURATION_MICRO,
        idle_color: str = "#2e2e2e",
        focus_color: str = "#A68A6E",
    ) -> None:
        """Animate entry-like border color on focus changes (POL-23)."""
        end_color = focus_color if focused else idle_color

        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            try:
                widget.configure(border_color=end_color)
            except Exception:
                pass
            return

        widget_id = id(widget)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_time = [0]
        start_color = focus_color if not focused else idle_color

        def animate_frame():
            progress = min(1.0, start_time[0] / max(1, duration))
            eased = EasingFunction.ease_out(progress)
            current = self._interpolate_hex(start_color, end_color, eased)
            try:
                widget.configure(border_color=current)
            except Exception:
                self._active_animations.pop(widget_id, None)
                return

            if progress < 1.0:
                start_time[0] += self.FRAME_TIME
                after_id = widget.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (widget, after_id)
            else:
                self._active_animations.pop(widget_id, None)

        animate_frame()

    def animate_success_flash(
        self,
        widget: Any,
        duration: int = DURATION_LONG,
        base_color: str = "#94a3b8",
        flash_color: str = "#22c55e",
    ) -> None:
        """Flash text color to success and back for brief completion feedback."""
        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            return

        widget_id = id(widget)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_time = [0]

        def animate_frame():
            progress = min(1.0, start_time[0] / max(1, duration))
            mirrored = progress * 2 if progress <= 0.5 else (1.0 - progress) * 2
            eased = EasingFunction.ease_in_out(mirrored)
            color = self._interpolate_hex(base_color, flash_color, eased)
            try:
                widget.configure(text_color=color)
            except Exception:
                self._active_animations.pop(widget_id, None)
                return

            if progress < 1.0:
                start_time[0] += self.FRAME_TIME
                after_id = widget.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (widget, after_id)
            else:
                try:
                    widget.configure(text_color=base_color)
                except Exception:
                    pass
                self._active_animations.pop(widget_id, None)

        animate_frame()

    def animate_queue_entrance(
        self,
        widget: Any,
        duration: int = DURATION_STANDARD,
        start_pad: int = 12,
        end_pad: int = 4,
    ) -> None:
        """Slide-like entrance animation by easing widget vertical padding."""
        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            try:
                widget.pack_configure(pady=end_pad)
            except Exception:
                pass
            return

        widget_id = id(widget)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_time = [0]

        def animate_frame():
            progress = min(1.0, start_time[0] / max(1, duration))
            eased = EasingFunction.ease_out(progress)
            current_pad = int(start_pad + (end_pad - start_pad) * eased)
            try:
                widget.pack_configure(pady=current_pad)
            except Exception:
                self._active_animations.pop(widget_id, None)
                return

            if progress < 1.0:
                start_time[0] += self.FRAME_TIME
                after_id = widget.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (widget, after_id)
            else:
                self._active_animations.pop(widget_id, None)

        animate_frame()

    def animate_color_transition(
        self,
        widget: Any,
        option_name: str,
        start_color: str,
        end_color: str,
        duration: int = DURATION_MICRO,
    ) -> None:
        """Animate any widget color option between two hex colors (POL-24)."""
        # POL-31: Skip animation if reduced motion preferred
        if self.reduced_motion:
            try:
                widget.configure(**{option_name: end_color})
            except Exception:
                pass
            return

        widget_id = id(widget)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_time = [0]

        def animate_frame():
            progress = min(1.0, start_time[0] / max(1, duration))
            eased = EasingFunction.ease_in_out(progress)
            color = self._interpolate_hex(start_color, end_color, eased)
            try:
                widget.configure(**{option_name: color})
            except Exception:
                self._active_animations.pop(widget_id, None)
                return

            if progress < 1.0:
                start_time[0] += self.FRAME_TIME
                after_id = widget.after(self.FRAME_TIME, animate_frame)
                self._active_animations[widget_id] = (widget, after_id)
            else:
                self._active_animations.pop(widget_id, None)

        animate_frame()

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255)

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB to hex color."""
        return f"#{r:02x}{g:02x}{b:02x}"

    def _interpolate_hex(self, start_color: str, end_color: str, progress: float) -> str:
        """Interpolate two hex colors by progress in [0, 1]."""
        progress = min(1.0, max(0.0, progress))
        sr, sg, sb = self._hex_to_rgb(start_color)
        er, eg, eb = self._hex_to_rgb(end_color)
        r = int(sr + (er - sr) * progress)
        g = int(sg + (eg - sg) * progress)
        b = int(sb + (eb - sb) * progress)
        return self._rgb_to_hex(r, g, b)


# Global animation manager instance
_animation_manager = None

def get_animation_manager() -> AnimationManager:
    """Get or create global animation manager instance."""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = AnimationManager()
    return _animation_manager
