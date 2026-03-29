# CLAUDE.md

## Mission

Work on RAVN as an in-progress desktop media application. Keep implementation and documentation aligned with the current repository state.

## Quick Context

- Entry point: `ravn.py` (calls setup_logging, ensure_directories_exist, migrate_all_legacy_files before app init)
- Main window: `ravn_app/ui/main_window.py`
- Shared runners: `ravn_app/core/runners.py`
- Task queue: `ravn_app/core/task_manager.py`
- Error parsing: `ravn_app/core/error_handler.py`
- Logging: `ravn_app/core/logging_config.py`
- Config paths (OS-aware): `ravn_app/core/config_paths.py`
- Download logic: `ravn_app/core/downloader.py`
- Conversion logic: `ravn_app/core/converter.py`
- Persistence: `ravn_app/core/database.py`
- CLI: `ravn_app/cli.py`

## Current Reality

- Phase 1 (stabilization), Phase 2 (high-priority features), Phase 3 (medium-priority features), Phase 4A (core GUI completeness), and Phase 4B (UI/UX enhancements) are complete.
- Download UI is fully wired: `_download_video()` uses `YouTubeDownloader` + background thread + `self.after()` callbacks.
- Config/history now live in OS-specific directories (Windows: `%APPDATA%\ravn\`, Linux: `~/.config/ravn/`).
- CLI available via `ravn download/convert/info/subtitle/history` with `--json` flag.
- Drag & drop works on converter and subtitle tabs (tkinterdnd2, fallback-safe).
- Real-time FFmpeg progress parsing via `-progress pipe:1` is active in `VideoConverter`.
- Queue panel widget shows live tasks (queued/running/completed) with cancel and open-folder buttons.
- Batch download mode supports up to 50 URLs via multi-line text input.
- Design system enhanced: Icons class replaces emojis, extended Colors with WCAG AA contrast, consistent 8px spacing grid.
- All UI tabs use semantic icons, proper visual feedback, and accessibility-compliant color contrast.
- Some auxiliary modules still use direct `subprocess` calls.
- Phase 1–4 complete in `TASKS.md`; Phase 5 (build/packaging) remains open.
- Verified 2026-03-29 (Phase 4B):
  - `367 passed, 1 skipped` (368 collected)

## Preferred Approach

1. Verify code before making status claims.
2. Prefer integration work over adding more surface area.
3. Use shared runners for new external process execution.
4. Keep docs synchronized when repository reality changes.
