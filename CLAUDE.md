# CLAUDE.md

## Mission

Work on RAVN as an in-progress desktop media application. Keep implementation, tests, and documentation synchronized with repository reality.

## Source Of Truth Order

Use these files in order before substantial changes:

1. `TASKS.md` (active backlog and status)
2. `PROGRESS.md` (validated state snapshot)
3. `ARCHITECTURE.md` (module boundaries and runtime flows)
4. `README.md` (user-facing capabilities and operation)
5. This file (`CLAUDE.md`) for workflow rules

## Start Here (Code)

- `ravn.py`
- `ravn_app/ui/main_window.py`
- `ravn_app/ui/tabs/download_tab.py`
- `ravn_app/ui/components/error_panel.py`
- `ravn_app/ui/components/playlist_sort_dialog.py`
- `ravn_app/core/runners/`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py`

## Quick Context

- Entry point: `ravn.py` runs `setup_logging`, `ensure_directories_exist`, and `migrate_all_legacy_files` before app init.
- UI shell: `ravn_app/ui/main_window.py` is a thin orchestrator.
- Feature UI modules live in `ravn_app/ui/tabs/`; reusable widgets live in `ravn_app/ui/components/`.
- Shared external tool execution lives in `ravn_app/core/runners/`.
- OS-aware persistence paths live in `ravn_app/core/config_paths.py`.
- Theme policy lives in `ravn_app/core/theme_catalog.py`.
- Localization pipeline lives in `ravn_app/core/i18n.py` and `ravn_app/translations/`.

## Current Reality

- Phases 1-4C and Phase 6 are complete.
- Phase 5 (build/packaging/distribution) remains open.
- Primary media flows run through shared runners (`FFmpegRunner`, `YtDlpRunner`, `Aria2Runner`).
- Some auxiliary modules still call `subprocess` directly.
- Download flow supports single URL, playlist, batch (up to 50 URLs), and torrent/magnet.
- Torrent flow supports `FULL`, `SEQUENTIAL`, and `STREAM` modes.
- Settings UI is compact single-page and scrollable (not nested sub-tabs).
- Theme system is strict two-theme: `dark` and `light` (legacy aliases normalized).
- Playlist fetch/sort dialog includes selected count, selected total size, high-contrast table headers, and stable action bar.

## Verified Facts

- Config and history paths are OS-aware via `ravn_app/core/config_paths.py`.
- CLI supports: `download`, `convert`, `info`, `subtitle`, `history`, `torrent` (plus `--json`).
- Drag-and-drop uses `tkinterdnd2` when available and degrades safely.
- FFmpeg realtime progress parsing is active.
- Queue panel supports queued/running/completed states and cancel/open-folder actions.
- Last full-suite baseline (2026-03-30): 417 passed, 1 skipped.
- Latest targeted regression checks during refactor sessions: 85 passed.

## Working Rules

1. Verify code before making status claims.
2. Prefer integration over unnecessary new surface area.
3. Use shared runners for any new external process execution paths.
4. Keep docs synchronized whenever repository reality changes.
5. If status/architecture changes, update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `TASKS.md` together.
6. If download flow changes, inspect `ravn_app/ui/tabs/download_tab.py`, `ravn_app/core/downloader.py`, and `ravn_app/ui/main_window.py` together.
7. If persistence behavior changes, inspect `ravn_app/core/database.py`, `ravn_app/core/config_paths.py`, and startup migration in `ravn.py`.
8. If CLI changes, update `ravn_app/cli.py`, command help text, and README examples.

## Design And UX Constraints

- Keep UI composition modular: thin shell + focused tabs + reusable components.
- Keep settings compact and information-dense without nested complexity.
- Keep user-facing strings i18n-based; avoid hardcoded TR/EN text in UI logic.
- Maintain clear contrast and accessibility for table/list controls.
- Respect reduced-motion behavior and avoid disruptive animations.

## Theme And I18N Constraints

- Theme IDs must normalize to `dark` or `light`.
- Legacy theme names should map to canonical IDs, not expand theme count.
- New UI labels, errors, tooltips, and button text must be translation-key based.
- Translation keys must be added in both `ravn_app/translations/tr.json` and `ravn_app/translations/en.json`.

## Torrent Constraints

- Detect both magnet URI and `.torrent` links/files in download workflow.
- Keep mode semantics stable:
  - `FULL`: complete download
  - `SEQUENTIAL`: playback-friendly piece ordering
  - `STREAM`: local HTTP streaming path with quick play action
- Surface aria2 progress and failures with user-readable feedback.

## Verification Commands

Use these before claiming completion on behavior changes:

- `pytest -q`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`

Prefer targeted subsets for quick iteration, then run broader verification where impact is wider.

## Documentation Sync Policy

If repository behavior or status changes:

1. Update `README.md` for end-user behavior and usage.
2. Update `ARCHITECTURE.md` for module/runtime structure.
3. Update `PROGRESS.md` for validated state and test evidence.
4. Update `TASKS.md` for open/closed work status.
5. Update this file only for workflow, constraints, and engineering guidance.
