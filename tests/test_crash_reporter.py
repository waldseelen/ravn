"""
Crash Reporter Tests
"""

import sys
from unittest.mock import MagicMock, patch

from ravn_app.core.crash_reporter import (
    _handle_unhandled_exception,
    install_crash_handler,
)


class TestCrashReporter:
    """Tests for crash report capturing and handling."""

    def test_install_crash_handler_sets_excepthook(self):
        """install_crash_handler should update sys.excepthook."""
        original_hook = sys.excepthook
        try:
            install_crash_handler()
            assert sys.excepthook == _handle_unhandled_exception
        finally:
            sys.excepthook = original_hook

    def test_crash_handler_writes_report_when_enabled(self, tmp_path):
        """When crash reporting is enabled, an unhandled exception writes a crash report."""
        fake_log_dir = tmp_path / "logs"
        fake_log_dir.mkdir(parents=True, exist_ok=True)

        mock_config = MagicMock()
        mock_config.get.return_value = True

        try:
            raise ValueError("Test crash message")
        except ValueError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        with patch("ravn_app.core.crash_reporter.get_log_directory", return_value=fake_log_dir), \
             patch("ravn_app.core.crash_reporter.ConfigManager", return_value=mock_config), \
             patch("ravn_app.core.crash_reporter._original_excepthook"):

            _handle_unhandled_exception(exc_type, exc_value, exc_tb)

        crashes_dir = tmp_path / "crashes"
        assert crashes_dir.exists()
        crash_files = list(crashes_dir.glob("crash_*.txt"))
        assert len(crash_files) == 1

        content = crash_files[0].read_text(encoding="utf-8")
        assert "RAVN Version:" in content
        assert "ValueError: Test crash message" in content

    def test_crash_handler_skips_when_disabled(self, tmp_path):
        """When crash reporting is disabled, no crash report file is written."""
        fake_log_dir = tmp_path / "logs"
        fake_log_dir.mkdir(parents=True, exist_ok=True)

        mock_config = MagicMock()
        mock_config.get.return_value = False

        try:
            raise RuntimeError("Disabled crash test")
        except RuntimeError:
            exc_type, exc_value, exc_tb = sys.exc_info()

        with patch("ravn_app.core.crash_reporter.get_log_directory", return_value=fake_log_dir), \
             patch("ravn_app.core.crash_reporter.ConfigManager", return_value=mock_config), \
             patch("ravn_app.core.crash_reporter._original_excepthook"):

            _handle_unhandled_exception(exc_type, exc_value, exc_tb)

        crashes_dir = tmp_path / "crashes"
        assert not crashes_dir.exists() or len(list(crashes_dir.glob("crash_*.txt"))) == 0
