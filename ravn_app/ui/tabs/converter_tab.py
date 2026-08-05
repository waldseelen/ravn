"""Canonical converter tab import surface.

The implementation currently lives in ``ravn_app.ui.converter_tab`` while the
workspace-oriented ``ravn_app.ui.tabs`` namespace remains the canonical import
surface for active desktop feature modules.
"""

from ravn_app.ui.converter_tab import ConverterTab

__all__ = ["ConverterTab"]
