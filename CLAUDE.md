# CLAUDE.md

Use this as the compact session guide. For the full workflow rules, read [AGENTS.md](AGENTS.md).

## Read Order

1. `TASKS.md`
2. `PROGRESS.md`
3. `ARCHITECTURE.md`
4. `README.md`
5. `AGENTS.md`

## Current Scope

RAVN is a cross-platform desktop + CLI media pipeline with:

- desktop workspaces for `Home`, `Download`, `Studio`, and `Library`
- shared runner-based execution for FFmpeg, yt-dlp, and aria2 flows
- queue/history/media-library coverage across desktop and CLI
- Windows, Linux, and macOS support verified by a CI test matrix (`tests.yml`)
- external tools (ffmpeg/ffprobe, yt-dlp, aria2c) **bundled into packaged builds** under
  `assets/<tool>/<platform>/` and resolved by `ravn_app/utils/bundled_tools.py`; the Settings
  "install missing tools" action is the fallback, not the primary path
- packaging: Windows is the signed release; Linux is `workflow_dispatch`-only
  (`linux-package.yml`) until verified on a real runner; macOS is tracked in `TASKS.md`
- an experimental `plugin_system.py` that is **not** part of the active packaged runtime

## Key Entry Points

- `ravn.py` (desktop GUI), `ravn_cli_entry.py` (packaged CLI entry point)
- `ravn_app/ui/main_window.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py`
- `ravn_app/utils/bundled_tools.py` (external tool resolution)

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

Latest full-suite verification: `854 passed, 1 skipped` on 2026-07-26.

Quality gates (both blocking in CI): `ruff check ravn_app tests` (clean) and
`mypy ravn_app/core ravn_app/utils` (0 errors). UI-layer mypy is still being tightened — see `ROADMAP.md`.
