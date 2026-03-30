"""
Unit tests for AnimationManager easing functions and animation utilities.

Tests verify that easing functions produce correct curves for smooth transitions.
"""

import os
import unittest
from ravn_app.core.animation_manager import (
    EasingFunction, AnimationManager, detect_reduced_motion
)


class TestEasingFunction(unittest.TestCase):
    """Tests for easing curve correctness."""

    def test_ease_out_bounds(self):
        """Ease-out must start at 0 and end at 1."""
        self.assertAlmostEqual(EasingFunction.ease_out(0.0), 0.0)
        self.assertAlmostEqual(EasingFunction.ease_out(1.0), 1.0)

    def test_ease_out_acceleration(self):
        """Ease-out accelerates early (progress > input at midpoint)."""
        # At t=0.5, ease_out should be > 0.5 (already more than halfway)
        mid = EasingFunction.ease_out(0.5)
        self.assertGreater(mid, 0.5, "Ease-out should accelerate early")
        self.assertLess(mid, 1.0, "Ease-out must stay below 1.0")

    def test_ease_out_curve(self):
        """Ease-out curve should be smooth and monotonically increasing."""
        prev = 0.0
        for t in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
            current = EasingFunction.ease_out(t)
            self.assertGreater(current, prev, f"ease_out({t}) should be > ease_out({prev})")
            prev = current

    def test_ease_in_bounds(self):
        """Ease-in must start at 0 and end at 1."""
        self.assertAlmostEqual(EasingFunction.ease_in(0.0), 0.0)
        self.assertAlmostEqual(EasingFunction.ease_in(1.0), 1.0)

    def test_ease_in_deceleration(self):
        """Ease-in decelerates early (progress < input at midpoint)."""
        # At t=0.5, ease_in should be < 0.5 (still less than halfway)
        mid = EasingFunction.ease_in(0.5)
        self.assertLess(mid, 0.5, "Ease-in should decelerate early")
        self.assertGreater(mid, 0.0, "Ease-in must be > 0")

    def test_ease_in_out_bounds(self):
        """Ease-in-out must start at 0 and end at 1."""
        self.assertAlmostEqual(EasingFunction.ease_in_out(0.0), 0.0)
        self.assertAlmostEqual(EasingFunction.ease_in_out(1.0), 1.0)

    def test_ease_in_out_symmetry(self):
        """Ease-in-out should be roughly symmetric around t=0.5."""
        # ease_in_out(0.3) ≈ 1 - ease_in_out(0.7)
        left = EasingFunction.ease_in_out(0.3)
        right = EasingFunction.ease_in_out(0.7)
        # Should be roughly symmetric (within 5% tolerance)
        self.assertAlmostEqual(left, 1 - right, delta=0.05)

    def test_clamp_out_of_bounds(self):
        """Easing functions should clamp negative and > 1.0 values."""
        # Negative input should return 0
        self.assertAlmostEqual(EasingFunction.ease_out(-0.5), 0.0)
        # > 1.0 should return 1.0
        self.assertAlmostEqual(EasingFunction.ease_out(1.5), 1.0)

    def test_ease_out_vs_ease_in(self):
        """Ease-out should be faster at start than ease-in."""
        t = 0.3
        ease_out = EasingFunction.ease_out(t)
        ease_in = EasingFunction.ease_in(t)
        # At same t, ease_out should be further along
        self.assertGreater(ease_out, ease_in)


class TestReducedMotion(unittest.TestCase):
    """Tests for reduced motion detection (POL-31)."""

    def test_env_var_true(self):
        """RAVN_REDUCED_MOTION=1 should return True."""
        old_val = os.environ.get("RAVN_REDUCED_MOTION")
        try:
            os.environ["RAVN_REDUCED_MOTION"] = "1"
            self.assertTrue(detect_reduced_motion())
            os.environ["RAVN_REDUCED_MOTION"] = "true"
            self.assertTrue(detect_reduced_motion())
        finally:
            if old_val is None:
                os.environ.pop("RAVN_REDUCED_MOTION", None)
            else:
                os.environ["RAVN_REDUCED_MOTION"] = old_val

    def test_env_var_false(self):
        """RAVN_REDUCED_MOTION=0 should return False."""
        old_val = os.environ.get("RAVN_REDUCED_MOTION")
        try:
            os.environ["RAVN_REDUCED_MOTION"] = "0"
            self.assertFalse(detect_reduced_motion())
            os.environ["RAVN_REDUCED_MOTION"] = "false"
            self.assertFalse(detect_reduced_motion())
        finally:
            if old_val is None:
                os.environ.pop("RAVN_REDUCED_MOTION", None)
            else:
                os.environ["RAVN_REDUCED_MOTION"] = old_val


class TestAnimationManager(unittest.TestCase):
    """Tests for AnimationManager utility methods."""

    def setUp(self):
        self.manager = AnimationManager()

    def test_hex_to_rgb_white(self):
        """Convert white hex to RGB."""
        r, g, b = self.manager._hex_to_rgb("#ffffff")
        self.assertEqual((r, g, b), (255, 255, 255))

    def test_hex_to_rgb_black(self):
        """Convert black hex to RGB."""
        r, g, b = self.manager._hex_to_rgb("#000000")
        self.assertEqual((r, g, b), (0, 0, 0))

    def test_hex_to_rgb_kahrvengi(self):
        """Convert kahverengi hex to RGB."""
        r, g, b = self.manager._hex_to_rgb("#8B6F47")
        self.assertEqual((r, g, b), (139, 111, 71))

    def test_hex_to_rgb_no_hash(self):
        """Hex conversion should handle missing #."""
        r1, g1, b1 = self.manager._hex_to_rgb("#ffffff")
        r2, g2, b2 = self.manager._hex_to_rgb("ffffff")
        self.assertEqual((r1, g1, b1), (r2, g2, b2))

    def test_rgb_to_hex(self):
        """Convert RGB to hex."""
        hex_color = self.manager._rgb_to_hex(139, 111, 71)
        self.assertEqual(hex_color.lower(), "#8b6f47")

    def test_rgb_to_hex_round_trip(self):
        """RGB → Hex → RGB should preserve values."""
        original = (139, 111, 71)
        hex_color = self.manager._rgb_to_hex(*original)
        restored = self.manager._hex_to_rgb(hex_color)
        self.assertEqual(original, restored)

    def test_animation_manager_constants(self):
        """Animation constants should be reasonable."""
        self.assertGreater(AnimationManager.DURATION_MICRO, 0)
        self.assertGreater(AnimationManager.DURATION_STANDARD, AnimationManager.DURATION_MICRO)
        self.assertGreater(AnimationManager.DURATION_LONG, AnimationManager.DURATION_STANDARD)
        self.assertLess(AnimationManager.FRAME_TIME, 20)  # 60fps = 16ms

    def test_easing_extremes(self):
        """Test easing functions at extremes (0, 0.5, 1)."""
        for ease_func in [EasingFunction.ease_out, EasingFunction.ease_in, EasingFunction.ease_in_out]:
            self.assertAlmostEqual(ease_func(0.0), 0.0)
            self.assertAlmostEqual(ease_func(1.0), 1.0)
            mid = ease_func(0.5)
            self.assertGreater(mid, 0.0)
            self.assertLess(mid, 1.0)

    def test_smooth_progress_moves_towards_target(self):
        """Smooth progress should advance gradually without overshooting target."""
        self.assertAlmostEqual(self.manager.smooth_progress(0.0, 1.0, max_step=0.2), 0.2)
        self.assertAlmostEqual(self.manager.smooth_progress(0.85, 1.0, max_step=0.2), 1.0)

    def test_smooth_progress_clamps_inputs(self):
        """Out-of-range current/target values should be clamped to [0, 1]."""
        value = self.manager.smooth_progress(-0.5, 1.5, max_step=0.25)
        self.assertGreaterEqual(value, 0.0)
        self.assertLessEqual(value, 1.0)

    def test_format_processing_text_cycles_ellipsis(self):
        """Processing text should cycle through one to three dots."""
        expected = [
            "İndiriliyor.",
            "İndiriliyor..",
            "İndiriliyor...",
            "İndiriliyor.",
        ]
        actual = [self.manager.format_processing_text("İndiriliyor", tick) for tick in range(4)]
        self.assertEqual(actual, expected)

    def test_reduced_motion_property(self):
        """Reduced motion property should return a boolean."""
        result = self.manager.reduced_motion
        self.assertIsInstance(result, bool)

    def test_set_reduced_motion(self):
        """set_reduced_motion should override detection."""
        self.manager.set_reduced_motion(True)
        self.assertTrue(self.manager.reduced_motion)
        self.assertFalse(self.manager.should_animate())

        self.manager.set_reduced_motion(False)
        self.assertFalse(self.manager.reduced_motion)
        self.assertTrue(self.manager.should_animate())


if __name__ == "__main__":
    unittest.main()
