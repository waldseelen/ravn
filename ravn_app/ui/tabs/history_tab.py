"""Canonical history tab import surface.

``HistoryTab`` currently reuses the shared implementation module in
``ravn_app.ui.history_settings_tab`` while ``ravn_app.ui.tabs`` remains the
canonical namespace for active desktop feature imports.
"""

from ravn_app.ui.history_settings_tab import HistoryTab

__all__ = ["HistoryTab"]
