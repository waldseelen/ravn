# AGENTS.md

## Mission

Maintain RAVN as a **Windows-first desktop + CLI media product**. Keep implementation, tests, and documentation synchronized with repository reality.

## Read Order Before Substantial Changes

1. `TASKS.md` — public roadmap and near-term priorities
2. `PROGRESS.md` — current release status and verified snapshot
3. `ARCHITECTURE.md` — module boundaries and runtime flows
4. `README.md` — product overview and user-facing operation
5. `AGENTS.md` — workflow rules and engineering guardrails

Keep `CLAUDE.md` lightweight as a compact compatibility entry point, not a duplicate of this file.

## Start Here (Code)

- `ravn.py`
- `ravn_app/ui/main_window.py`
- `ravn_app/ui/tabs/download_tab.py`
- `ravn_app/ui/tabs/mixer_tab.py`
- `ravn_app/ui/tabs/library_tab.py`
- `ravn_app/ui/tabs/filters_tab.py`
- `ravn_app/ui/components/error_panel.py`
- `ravn_app/ui/components/playlist_sort_dialog.py`
- `ravn_app/core/runners/`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py`

## Quick Context

- Entry point: `ravn.py` runs logging setup, directory creation, legacy migration, and dependency checks before app init.
- UI shell: `ravn_app/ui/main_window.py` is a thin orchestrator.
- Canonical desktop feature modules live in `ravn_app/ui/tabs/`; reusable widgets live in `ravn_app/ui/components/`.
- Shared external-tool execution lives in `ravn_app/core/runners/`.
- OS-aware persistence paths live in `ravn_app/core/config_paths.py`.
- Theme policy lives in `ravn_app/core/theme_catalog.py`.
- Localization lives in `ravn_app/core/i18n.py` and `ravn_app/translations/`.

## Current Product Scope

- Desktop workspaces: `Home`, `Download`, `Studio`, `Library`
- Shared queue panel plus integrated settings/theme/language utilities
- Download support for single URLs, playlists, batch links, magnets, and `.torrent` files
- Processing support for convert, subtitle, filters, mixer, and utility flows
- Local media library with history, search, tags, collections, and export
- CLI support for `download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, and `utilities`
- Windows packaged releases are the active distribution target; current release work is final clean-machine validation and signing/trust polish
- `plugin_system.py` is experimental only and not part of the active packaged runtime

## Working Rules

1. Verify code before making status claims.
2. Prefer integration over unnecessary new surface area.
3. Use shared runners for new external-process execution paths whenever practical.
4. Keep docs synchronized whenever repository reality changes.
5. If status or architecture changes, update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `TASKS.md` together.
6. If download behavior changes, inspect `ravn_app/ui/tabs/download_tab.py`, `ravn_app/core/downloader.py`, and `ravn_app/ui/main_window.py` together.
7. If persistence behavior changes, inspect `ravn_app/core/database.py`, `ravn_app/core/config_paths.py`, and startup migration in `ravn.py`.
8. If CLI behavior changes, update `ravn_app/cli.py`, command help text, and README examples.

## Design and UX Constraints

- Keep UI composition modular: thin shell + focused tabs + reusable components.
- Keep settings compact and information-dense without nested complexity.
- Keep user-facing strings i18n-based; avoid hardcoded language strings in UI logic.
- Maintain strong contrast and accessibility for table/list controls.
- Respect reduced-motion behavior and avoid disruptive animations.

## Theme and I18N Constraints

- Theme IDs must normalize to `dark` or `light`.
- Legacy theme names should map to canonical IDs, not expand theme count.
- New UI labels, errors, tooltips, and button text must be translation-key based.
- Translation keys must be added in both `ravn_app/translations/tr.json` and `ravn_app/translations/en.json`.

## Torrent Constraints

- Detect both magnet URIs and `.torrent` links/files in the download workflow.
- Keep mode semantics stable:
  - `FULL`: complete download
  - `SEQUENTIAL`: playback-friendly piece ordering
  - `STREAM`: local HTTP streaming path with quick play action
- Surface aria2 progress and failures with user-readable feedback.
- Preserve torrent queue semantics, pause/resume behavior, filter states, peer/seeder/size metrics, and per-file child rows when iterating on torrent UX.

## Verification Commands

Use these before claiming completion on behavior changes:

- `pytest -q`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`

Latest full-suite verification: `644 passed, 1 skipped` on 2026-04-07.

## Documentation Sync Policy

If repository behavior or status changes:

1. Update `README.md` for end-user behavior and usage.
2. Update `ARCHITECTURE.md` for module/runtime structure.
3. Update `PROGRESS.md` for validated state and test evidence.
4. Update `TASKS.md` for roadmap/status wording.
5. Update this file only for workflow, constraints, and engineering guidance.
