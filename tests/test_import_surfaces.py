"""Import-surface and extension-boundary regression tests."""

from ravn_app.core import plugin_system
from ravn_app.ui import download_tab as legacy_download_tab
from ravn_app.ui.converter_tab import ConverterTab as LegacyConverterTab
from ravn_app.ui.history_settings_tab import HistoryTab as LegacyHistoryTab
from ravn_app.ui.history_settings_tab import SettingsTab as LegacySettingsTab
from ravn_app.ui.subtitle_tab import SubtitleTab as LegacySubtitleTab
from ravn_app.ui.tabs.converter_tab import ConverterTab
from ravn_app.ui.tabs.download_tab import DownloadTab
from ravn_app.ui.tabs.history_tab import HistoryTab
from ravn_app.ui.tabs.settings_tab import SettingsTab
from ravn_app.ui.tabs.subtitle_tab import SubtitleTab


def test_canonical_tab_imports_match_legacy_implementation_modules():
    assert ConverterTab is LegacyConverterTab
    assert SubtitleTab is LegacySubtitleTab
    assert HistoryTab is LegacyHistoryTab
    assert SettingsTab is LegacySettingsTab


def test_legacy_download_alias_points_to_canonical_download_tab():
    assert legacy_download_tab.DownloadTab is DownloadTab


def test_plugin_system_is_explicitly_experimental_and_not_runtime_integrated():
    assert plugin_system.PLUGIN_SYSTEM_STATUS == "experimental"
    assert plugin_system.PLUGIN_RUNTIME_INTEGRATED is False
