# UI Wrapper and Extension-Boundary Notes

Verified on 2026-04-05.

This document records the cleanup work that clarifies the active desktop UI surface and the current status of RAVN's experimental extension scaffolding.

---

## Goal

Reduce maintenance ambiguity after the workspace-shell migration by making the canonical desktop import surfaces explicit and by documenting which older modules are compatibility-only.

---

## Canonical Desktop Feature Imports

For active desktop feature wiring, use the `ravn_app.ui.tabs` namespace.

Canonical surfaces:

- `ravn_app.ui.tabs.download_workspace.DownloadWorkspace`
- `ravn_app.ui.tabs.download_tab.DownloadTab`
- `ravn_app.ui.tabs.torrent_tab.TorrentTab`
- `ravn_app.ui.tabs.converter_tab.ConverterTab`
- `ravn_app.ui.tabs.subtitle_tab.SubtitleTab`
- `ravn_app.ui.tabs.filters_tab.FiltersTab`
- `ravn_app.ui.tabs.mixer_tab.MixerTab`
- `ravn_app.ui.tabs.utilities_tab.UtilitiesTab`
- `ravn_app.ui.tabs.library_tab.LibraryTab`
- `ravn_app.ui.tabs.history_tab.HistoryTab`
- `ravn_app.ui.tabs.settings_tab.SettingsTab`
- `ravn_app.ui.tabs.queue_tab.QueueTab`
- `ravn_app.ui.tabs.home_workspace.HomeWorkspace`
- `ravn_app.ui.tabs.library_workspace.LibraryWorkspace`
- `ravn_app.ui.tabs.studio_workspace.StudioWorkspace`

`ravn_app.ui.main_window.YouTubeDownloaderApp` remains the desktop shell entry surface.

---

## Compatibility Inventory

### Legacy-compatible modules still under `ravn_app/ui/`

These modules remain in the repository so older imports continue to resolve, but they are no longer the preferred import surfaces for active desktop feature work:

- `ravn_app/ui/download_tab.py`
  - legacy alias to `ravn_app.ui.tabs.download_tab.DownloadTab`
- `ravn_app/ui/converter_tab.py`
  - legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.converter_tab`
- `ravn_app/ui/subtitle_tab.py`
  - legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.subtitle_tab`
- `ravn_app/ui/history_settings_tab.py`
  - shared legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.history_tab` and `ravn_app.ui.tabs.settings_tab`

### Canonical wrappers retained under `ravn_app/ui/tabs/`

Some canonical `ui/tabs/` modules still forward to older implementation modules. This is intentional for now because it keeps behavior stable while release hardening and packaging work finishes.

Retained canonical wrappers:

- `ravn_app/ui/tabs/converter_tab.py`
- `ravn_app/ui/tabs/subtitle_tab.py`
- `ravn_app/ui/tabs/history_tab.py`
- `ravn_app/ui/tabs/settings_tab.py`

These wrappers are now explicitly documented as canonical import surfaces rather than ambiguous parallel entry points.

---

## Wrapper Cleanup Outcome

This cleanup focused on reducing ambiguity, not performing a risky UI-file migration.

Completed cleanup actions:

- standardized wrapper docstrings so canonical vs legacy intent is explicit
- updated tests to use canonical `ravn_app.ui.tabs.*` imports for active feature modules
- added regression coverage for canonical/legacy import equivalence

Deferred intentionally:

- moving all legacy implementation bodies into `ravn_app/ui/tabs/`
- splitting `history_settings_tab.py` into separate implementation files

Those larger file moves are better handled later if they provide enough value to justify churn.

---

## `plugin_system.py` Decision

Current decision: **experimental only / future extension surface**.

`ravn_app/core/plugin_system.py` is:

- **not** auto-loaded by the desktop shell
- **not** auto-loaded by the CLI
- **not** part of a supported packaged-plugin runtime story
- retained only as an experimental scaffold for possible future extension work

Additional clarity applied:

- the module now declares explicit status metadata (`experimental`, runtime-integrated = `False`)
- repository docs now describe it as an experimental scaffold rather than an active runtime feature
- `ravn_app/core/database.py` plugin hook placeholders are also treated as internal hooks, not as a public plugin API

---

## Verification

Key verification commands used for this work:

- `pytest -q tests/test_import_surfaces.py`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
- `pytest -q`

Validated baseline at the time of this document:

- full suite: `617 passed, 1 skipped`

---

## Outcome

This cleanup is complete.

The repository now makes these points explicit:

- active desktop feature imports should come from `ravn_app.ui.tabs`
- legacy `ravn_app.ui.*` modules are compatibility surfaces, not equal peers
- `plugin_system.py` does not imply supported runtime plugin loading today

Follow-up work moved into optimization and release packaging polish.
