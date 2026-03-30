# AGENT.md

## Purpose

This repository contains a desktop media manager named RAVN. It uses CustomTkinter for the UI, FFmpeg/FFprobe for media processing, and yt-dlp for remote media extraction.

## Start Here

- `TASKS.md`
- `ravn.py`
- `ravn_app/ui/main_window.py`
- `ravn_app/ui/tabs/download_tab.py`
- `ravn_app/ui/components/error_panel.py`
- `ravn_app/core/runners.py`
- `ravn_app/core/task_manager.py`
- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/database.py`
- `ravn_app/cli.py` — CLI entry point (click)

## Verified Facts

- Main media execution paths use shared runners from `ravn_app/core/runners.py`.
- Some auxiliary modules still use direct `subprocess` calls.
- `ravn_app/ui/main_window.py` is a thin orchestration shell (window lifecycle + tab composition).
- Download tab is wired in `ravn_app/ui/tabs/download_tab.py`, including background-thread execution and thread-safe UI callbacks.
- Reusable download UI pieces are extracted under `ravn_app/ui/components/` (`error_panel.py`, `playlist_item.py`, `url_input.py`).
- Compatibility import wrapper exists at `ravn_app/ui/download_tab.py`.
- Startup migration (`ensure_directories_exist`, `migrate_all_legacy_files`) runs in `ravn.py` before app init.
- Config and history now resolve via OS-specific paths in `ravn_app/core/config_paths.py`.
- CLI is available via `ravn_app/cli.py` (commands: download, convert, info, subtitle, history, serve).
- Drag & drop is implemented in converter and subtitle tabs (tkinterdnd2, with graceful fallback).
- `TASKS.md` Phase 1, Phase 2, Phase 3, Phase 4A, Phase 4B, and Phase 4C are complete. Phase 5 remains open.
- Real-time FFmpeg progress is implemented via `-progress pipe:1` parsing in `FFmpegRunner._run_with_realtime_progress()`.
- Queue panel (`ravn_app/ui/queue_panel.py`) provides live visualization of tasks with cancel/open-folder actions.
- Batch download mode allows up to 50 URLs via multi-line text input in download tab.
- Main window has dedicated queue tab showing real-time task status.
- Design system (`design_tokens.py`) includes Icons class with Unicode symbols, extended Colors palette with WCAG AA contrast, and standardized Spacing/Sizes.
- All UI components use semantic color tokens, consistent icon set, and 8px spacing grid.
- Phase 4C.1 (brand palette), Phase 4C.2 (icon placement), Phase 4C.3 (smooth transitions), Phase 4C.4 (loading/operational feedback), Phase 4C.5 (error/form feedback), Phase 4C.6 (visual polish), and Phase 4C.7 (accessibility) are complete.
- Toast notifications (ToastManager) provide success/warning/error feedback.
- Reduced-motion detection respects system preferences and RAVN_REDUCED_MOTION env var.
- Tooltip component provides 300ms hover tooltips for action buttons.
- URL validation on blur shows success/error indicator.
- Playlist metadata fetch now includes per-video selected-quality size/resolution and selected-total size summary.
- Single video info fetch also computes `size_by_quality_mb` / `resolution_by_quality` maps (via `YtDlpRunner.compute_size_by_quality`), so the size estimate label updates correctly when quality changes.
- ID3 auto-tagging: when `embed_metadata=True` and format is MP3/M4A, yt-dlp embeds album art (`--embed-thumbnail --convert-thumbnails jpg`) and metadata (`--add-metadata`).
- Auto-sort: when `auto_sort=True`, yt-dlp output template is `%(uploader,channel,creator)s/%(title)s.%(ext)s`, grouping files under channel/artist subdirectories.
- Both options exposed as checkboxes in the download tab options row and as persistent settings in the "İndirme" settings sub-tab.
- Download tab playlist panel is expanded for long-list usability (wider, denser rows, easier scrolling).
- Settings tab consolidated from 4 sub-tabs to 3: "Gelişmiş" removed and merged into "İndirme".
- System tray close behavior is user-configurable via `close_to_tray` bool in config (set by `close_behavior_combo` in General settings).
- Responsive layout: `_on_window_resize` centers tabview with ~1200px max width on large displays.
- Playlist panel has an in-panel "Approve and Download" button (`playlist_approve_btn`); `expand=True` visibility bug fixed.
- File size estimate label displayed next to URL input; updates after video info fetch and on quality change.
- All color tokens in `design_tokens.py` converted to `(light, dark)` tuples for full Light/Dark theme parity (14 attributes).
- Converter tab video_codec, audio_codec, quality, and output_path selectors have educational Tooltip descriptions.
- Last known full-suite baseline (2026-03-30):
  - `pytest --collect-only -q` → `418` collected
  - `pytest -q` → `417 passed, 1 skipped`
- UI modularization regression checks:
  - `pytest -q tests/test_ui_logic.py` → `27 passed`
  - `pytest -q tests/test_ui_components.py tests/test_app_builder.py` → `37 passed`

## Working Rules

- Prefer shared runners for new FFmpeg, FFprobe, and yt-dlp execution paths.
- Do not describe the repo as fully complete or production-ready unless the code and backlog actually support that claim.
- If you change repository status, update `README.md`, `PROGRESS.md`, and `ARCHITECTURE.md` together.
- If you touch download flow, inspect `ravn_app/ui/tabs/download_tab.py`, `ravn_app/core/downloader.py`, and orchestration edges in `ravn_app/ui/main_window.py`.
- If you touch persistence, account for the OS-aware path migration in `ravn_app/core/config_paths.py`.
- If you touch CLI, update `setup.py` entry points accordingly.
