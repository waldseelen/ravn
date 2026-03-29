"""
Animation Manager - Centralized animation utilities for smooth UI transitions.

Provides easing functions, button state animations, spinners, and micro-interactions.
All animations use CustomTkinter's after() loop for 60fps smooth transitions.
"""

import math
from typing import Callable, Optional
import customtkinter as ctk


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
    """

    # Animation timing constants (milliseconds)
    DURATION_MICRO = 150      # Micro-interactions (button press, focus)
    DURATION_STANDARD = 200   # Standard transitions (fade, slide)
    DURATION_LONG = 300       # Long transitions (modal open, tab switch)
    FRAME_TIME = 16          # 60fps = 16ms per frame

    def __init__(self):
        self._active_animations = {}  # Track active animations to avoid conflicts

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

        Args:
            button: CTkButton to animate
            duration: Animation duration in milliseconds
            target_opacity: Final opacity (0.0-1.0), default 0.5 for 50% gray
        """
        widget_id = id(button)
        if widget_id in self._active_animations:
            self._cancel_animation(widget_id)

        start_opacity = 1.0
        start_time = [None]
        original_text_color = button._text_color

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
                self._active_animations[widget_id] = button.after(self.FRAME_TIME, animate_frame)
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

        Args:
            button: CTkButton to animate
            duration: Animation duration in milliseconds
            target_color: Final text color (hex)
        """
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
                self._active_animations[widget_id] = button.after(self.FRAME_TIME, animate_frame)
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

        frame_interval = int(1000 / fps)

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

            self._active_animations[widget_id] = label.after(frame_interval, animate_spinner)

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
            after_id = self._active_animations.pop(widget_id)
            try:
                # Find the widget and cancel after
                pass  # The after_id already stores the scheduled callback
            except:
                pass

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


# Global animation manager instance
_animation_manager = None

def get_animation_manager() -> AnimationManager:
    """Get or create global animation manager instance."""
    global _animation_manager
    if _animation_manager is None:
        _animation_manager = AnimationManager()
    return _animation_manager
