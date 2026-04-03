# CLAUDE.md

## Mission

Work on RAVN as an in-progress desktop media application. Keep implementation, tests, and documentation synchronized with repository reality.

## Source Of Truth Order

Use these files in order before substantial changes:

1. `TASKS.md` — active backlog and task status
2. `PROGRESS.md` — validated implementation snapshot
3. `ARCHITECTURE.md` — module boundaries and runtime flows
4. `README.md` — user/project overview and operation
5. `CLAUDE.md` — compact engineering guidance for agent sessions

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

- Entry point: `ravn.py` runs `setup_logging`, `ensure_directories_exist`, and `migrate_all_legacy_files` before UI startup.
- Main shell: `ravn_app/ui/main_window.py` is a thin orchestrator.
- Feature UI modules live under `ravn_app/ui/tabs/`; reusable widgets live under `ravn_app/ui/components/`.
- Shared external process execution should prefer `ravn_app/core/runners/`.
- OS-aware persistence paths live in `ravn_app/core/config_paths.py`.
- Theme normalization lives in `ravn_app/core/theme_catalog.py`.
- i18n lives in `ravn_app/core/i18n.py` and `ravn_app/translations/`.

## Current Reality

- Phases 1–4C, Phase 6, Phase 7, and Phase 8 are complete.
- Phase 5 build/packaging/distribution remains open.
- Desktop shell uses grouped workspaces: `Home`, `Download`, `Studio`, `Library`.
- Queue is exposed through a global right-side panel/drawer.
- Settings are exposed as an independent lower-left utility/workspace entry.
- Primary media flows run through shared runners (`FFmpegRunner`, `YtDlpRunner`, `Aria2Runner`).
- Download flow supports single URL, playlist, batch, torrent/magnet, reusable profiles, naming templates, subtitle automation, post-download automation, metadata enrichment, robustness controls, advanced auth/tuning controls, and CLI parity for those acquisition concepts.
- Phase 7 media-management features are active in both desktop and CLI runtimes, including queue/history persistence and automatic media-library indexing.
- Utilities workflow is active in both desktop UI and CLI.

## Verified Facts

- Config and history paths are OS-aware via `ravn_app/core/config_paths.py`.
- CLI supports: `download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, `utilities` (plus `--json`).
- History UI aggregates downloads, conversions, and generic operation records.
- Drag-and-drop uses `tkinterdnd2` when available and degrades safely.
- FFmpeg real-time progress parsing is active.
- Queue panel supports queued/running/completed states and cancel/open-folder actions.
- Last full-suite baseline (2026-04-03): `578 passed, 1 skipped`.
- Shared UI helpers in `ui_components.py`: `style_combo`, `style_entry`, `bind_focus_ring`, `set_button_loading_state`.
- Keyboard shortcuts include `Ctrl+Enter`, `Escape`, `Ctrl+L`, plus shell-level `Ctrl+K` and `Ctrl+,`.

## Working Rules

1. Verify code before making status claims.
2. Prefer integration over unnecessary new surface area.
3. Use shared runners for new external process paths whenever practical.
4. Keep docs synchronized whenever repository reality changes.
5. If status/architecture changes, update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `TASKS.md` together.
6. If download flow changes, inspect `ravn_app/ui/tabs/download_tab.py`, `ravn_app/core/downloader.py`, and `ravn_app/ui/main_window.py` together.
7. If persistence behavior changes, inspect `ravn_app/core/database.py`, `ravn_app/core/config_paths.py`, and startup migration in `ravn.py`.
8. If CLI changes, update `ravn_app/cli.py`, command help text, and README examples.

## Design / UX Constraints

- Keep UI composition modular: thin shell + focused tabs + reusable components.
- Keep settings compact and information-dense without nested complexity.
- Keep user-facing strings translation-key based.
- Maintain clear contrast/accessibility for tables and lists.
- Respect reduced-motion behavior and avoid disruptive animation.

## Theme / I18N Constraints

- Theme IDs must normalize to `dark` or `light`.
- Legacy theme names should map to canonical IDs, not expand theme count.
- New UI labels, errors, tooltips, and button text must be translation-key based.
- Translation keys must be added in both `ravn_app/translations/tr.json` and `ravn_app/translations/en.json`.

## Torrent Constraints

- Detect both magnet URIs and `.torrent` links/files in download workflow.
- Keep mode semantics stable:
  - `FULL`
  - `SEQUENTIAL`
  - `STREAM`
- Surface aria2 progress/failures with user-readable feedback.

## Verification Commands

Use these before claiming completion on behavior changes:

- `pytest -q`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`

Prefer targeted subsets during iteration, then rerun broader coverage when impact is wider.

## Documentation Sync Policy

If repository behavior or status changes:

1. Update `README.md` for user/project-facing behavior.
2. Update `ARCHITECTURE.md` for module/runtime structure.
3. Update `PROGRESS.md` for validated state and test evidence.
4. Update `TASKS.md` for open/closed task state.
5. Update `CLAUDE.md` only for workflow/context guidance.
