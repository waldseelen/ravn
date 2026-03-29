"""
Unit tests for AnimationManager easing functions and animation utilities.

Tests verify that easing functions produce correct curves for smooth transitions.
"""

import unittest
from ravn_app.core.animation_manager import EasingFunction, AnimationManager


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


if __name__ == "__main__":
    unittest.main()
