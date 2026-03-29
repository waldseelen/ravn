# AGENT.md

## Purpose

This repository contains a desktop media manager named RAVN. It uses CustomTkinter for the UI, FFmpeg/FFprobe for media processing, and yt-dlp for remote media extraction.

## Start Here

- `TASKS.md`
- `ravn.py`
- `ravn_app/ui/main_window.py`
- `ravn_app/core/runners.py`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py` — CLI entry point (click)

## Verified Facts

- Main media execution paths use shared runners from `ravn_app/core/runners.py`.
- Some auxiliary modules still use direct `subprocess` calls.
- Download tab is wired: `_download_video()` in `ravn_app/ui/main_window.py` calls `YouTubeDownloader` in a background thread with thread-safe UI callbacks.
- Startup migration (`ensure_directories_exist`, `migrate_all_legacy_files`) runs in `ravn.py` before app init.
- Config and history now resolve via OS-specific paths in `ravn_app/core/config_paths.py`.
- CLI is available via `ravn_app/cli.py` (commands: download, convert, info, subtitle, history, serve).
- Drag & drop is implemented in converter and subtitle tabs (tkinterdnd2, with graceful fallback).
- `TASKS.md` Phase 1, Phase 2, Phase 3, Phase 4A, and Phase 4B are complete. Phase 5 remains open.
- Real-time FFmpeg progress is implemented via `-progress pipe:1` parsing in `FFmpegRunner._run_with_realtime_progress()`.
- Queue panel (`ravn_app/ui/queue_panel.py`) provides live visualization of tasks with cancel/open-folder actions.
- Batch download mode allows up to 50 URLs via multi-line text input in download tab.
- Main window has dedicated queue tab showing real-time task status.
- Design system (`design_tokens.py`) includes Icons class with Unicode symbols, extended Colors palette with WCAG AA contrast, and standardized Spacing/Sizes.
- All UI components use semantic color tokens, consistent icon set, and 8px spacing grid.
- Verified 2026-03-29 (Phase 4B session):
  - `pytest --collect-only -q` → `368` collected
  - `pytest -q` → `367 passed, 1 skipped`

## Working Rules

- Prefer shared runners for new FFmpeg, FFprobe, and yt-dlp execution paths.
- Do not describe the repo as fully complete or production-ready unless the code and backlog actually support that claim.
- If you change repository status, update `README.md`, `PROGRESS.md`, and `CHANGELOG.md` together.
- If you touch download flow, inspect both `ravn_app/ui/main_window.py` and `ravn_app/core/downloader.py`.
- If you touch persistence, account for the OS-aware path migration in `ravn_app/core/config_paths.py`.
- If you touch CLI, update `setup.py` entry points accordingly.
