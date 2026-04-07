# CLAUDE.md

Use this as the compact session guide. For the full workflow rules, read [AGENTS.md](AGENTS.md).

## Read Order

1. `TASKS.md`
2. `PROGRESS.md`
3. `ARCHITECTURE.md`
4. `README.md`
5. `AGENTS.md`

## Current Scope

RAVN is a Windows-first desktop + CLI media pipeline with:

- desktop workspaces for `Home`, `Download`, `Studio`, and `Library`
- shared runner-based execution for FFmpeg, yt-dlp, and aria2 flows
- queue/history/media-library coverage across desktop and CLI
- Windows packaged releases as the current distribution focus
- an experimental `plugin_system.py` that is **not** part of the active packaged runtime

## Key Entry Points

- `ravn.py`
- `ravn_app/ui/main_window.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py`

## Guardrails

- Verify code before making status claims.
- Prefer shared runners for new external tool execution paths.
- Keep UI strings translation-key based.
- Update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `TASKS.md` together when repo reality changes.
- Keep settings compact, themes limited to `dark` / `light`, and torrent mode semantics stable.

## Verification

Primary checks:

- `pytest -q`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`

Latest full-suite verification: `644 passed, 1 skipped` on 2026-04-07.
