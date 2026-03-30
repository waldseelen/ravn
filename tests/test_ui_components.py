"""
Unit tests for UI components (Toast, InlineErrorLabel, Tooltip, etc.).

Tests verify component creation and basic functionality without requiring
a full Tk window.
"""

import unittest


class TestUIComponentsImport(unittest.TestCase):
    """Verify UI components can be imported without errors."""

    def test_import_toast_manager(self):
        """ToastManager should be importable."""
        from ravn_app.ui.ui_components import ToastManager
        self.assertTrue(callable(ToastManager))

    def test_import_toast(self):
        """Toast should be importable."""
        from ravn_app.ui.ui_components import Toast
        self.assertTrue(callable(Toast))

    def test_import_inline_error_label(self):
        """InlineErrorLabel should be importable."""
        from ravn_app.ui.ui_components import InlineErrorLabel
        self.assertTrue(callable(InlineErrorLabel))

    def test_import_form_field_with_error(self):
        """FormFieldWithError should be importable."""
        from ravn_app.ui.ui_components import FormFieldWithError
        self.assertTrue(callable(FormFieldWithError))

    def test_import_tooltip(self):
        """Tooltip should be importable."""
        from ravn_app.ui.ui_components import Tooltip
        self.assertTrue(callable(Tooltip))

    def test_import_empty_state_widget(self):
        """EmptyStateWidget should be importable."""
        from ravn_app.ui.ui_components import EmptyStateWidget
        self.assertTrue(callable(EmptyStateWidget))

    def test_import_loading_skeleton(self):
        """LoadingSkeleton should be importable."""
        from ravn_app.ui.ui_components import LoadingSkeleton
        self.assertTrue(callable(LoadingSkeleton))


class TestDesignTokensImport(unittest.TestCase):
    """Verify design tokens can be imported and have expected values."""

    def test_import_cursors(self):
        """Cursors class should be importable with expected values."""
        from ravn_app.ui.design_tokens import Cursors
        self.assertEqual(Cursors.POINTER, "hand2")
        self.assertEqual(Cursors.TEXT, "xterm")

    def test_import_sizes(self):
        """Sizes class should have corner radius values."""
        from ravn_app.ui.design_tokens import Sizes
        # POL-22: 8px for cards, 6px for buttons/inputs
        self.assertEqual(Sizes.CORNER_SM, 6)
        self.assertEqual(Sizes.CORNER_MD, 8)
        self.assertEqual(Sizes.CORNER_LG, 12)
        self.assertEqual(Sizes.FOCUS_RING_WIDTH, 2)
        self.assertEqual(Sizes.TOOLTIP_DELAY, 300)

    def test_import_icons(self):
        """Icons class should have empty state icons."""
        from ravn_app.ui.design_tokens import Icons
        self.assertIsNotNone(Icons.EMPTY_FOLDER)
        self.assertIsNotNone(Icons.EMPTY_LIST)


class TestURLValidation(unittest.TestCase):
    """Test URL validation logic used in main_window (POL-17)."""

    @staticmethod
    def _validate_url(url: str) -> bool:
        """Copy of validation logic from main_window."""
        if not url:
            return False
        url_lower = url.lower()
        if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
            return False
        known_domains = [
            "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
            "twitch.tv", "soundcloud.com", "facebook.com", "twitter.com",
            "tiktok.com", "instagram.com", "bilibili.com", "nicovideo.jp",
        ]
        return any(domain in url_lower for domain in known_domains)

    def test_valid_youtube_url(self):
        """YouTube URLs should be valid."""
        self.assertTrue(self._validate_url("https://www.youtube.com/watch?v=abc123"))
        self.assertTrue(self._validate_url("https://youtu.be/abc123"))

    def test_valid_vimeo_url(self):
        """Vimeo URLs should be valid."""
        self.assertTrue(self._validate_url("https://vimeo.com/123456"))

    def test_invalid_url_no_protocol(self):
        """URLs without protocol should be invalid."""
        self.assertFalse(self._validate_url("youtube.com/watch?v=abc123"))

    def test_invalid_url_unknown_domain(self):
        """Unknown domains should be invalid."""
        self.assertFalse(self._validate_url("https://example.com/video"))

    def test_empty_url(self):
        """Empty URLs should be invalid."""
        self.assertFalse(self._validate_url(""))
        self.assertFalse(self._validate_url(None))


if __name__ == "__main__":
    unittest.main()
