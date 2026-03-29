# ARCHITECTURE

## Overview

RAVN is a layered desktop application. The repository has substantial core functionality, but end-to-end product behavior is still incomplete.

```text
ravn.py
  -> ravn_app.ui.main_window.YouTubeDownloaderApp
      -> UI tabs
      -> core services
      -> SQLite and JSON files in repo root
```

## Layers

### 1. Entry

- `ravn.py` starts the application.
- `ravn_app/ui/main_window.py` creates the main window and tab layout.

### 2. UI

Files under `ravn_app/ui/` provide the desktop interface.

- `main_window.py`: top-level window and tab wiring
- `converter_tab.py`: conversion UI
- `subtitle_tab.py`: subtitle UI
- `history_settings_tab.py`: history and settings UI
- `advanced_features.py`: optional helpers such as tray, notifications, shortcuts, and theme helpers

The UI layer is still the weakest integration point. The download tab exists, but `_download_video()` is still stubbed.

### 3. Core

Files under `ravn_app/core/` contain the main domain logic.

- `runners.py`: shared `FFmpegRunner` and `YtDlpRunner`
- `task_manager.py`: queue and callback plumbing for long-running tasks
- `error_handler.py`: user-facing parsing for FFmpeg and yt-dlp errors
- `logging_config.py`: structured logging setup
- `downloader.py`: yt-dlp-backed download logic
- `converter.py`: conversion, analysis, and editing helpers
- `audio_normalizer.py`: normalization and merge helpers
- `subtitle_manager.py`: subtitle download, conversion, editing, and embedding
- `platform_support.py`: platform adapters and registry
- `plugin_system.py`: hook-based plugin model
- `database.py`: SQLite history/config plus a legacy lightweight plugin abstraction
- `update_manager.py`: release lookup, download, and install flow
- `app_builder.py`: packaging/build automation helpers

### 4. Utilities

Files under `ravn_app/utils/` provide helper functionality.

- `ffmpeg_checker.py`
- `file_utils.py`
- `system_utils.py`

## Execution Model

### Shared runners

The main media execution paths have been consolidated around `ravn_app/core/runners.py`.

- `converter.py` uses `FFmpegRunner`
- `downloader.py` uses `YtDlpRunner`
- `audio_normalizer.py` uses `FFmpegRunner`
- `subtitle_manager.py` uses `FFmpegRunner` and `YtDlpRunner`

### Remaining direct subprocess usage

Some auxiliary or packaging-oriented modules still invoke `subprocess` directly, including:

- `ravn_app/core/platform_support.py`
- `ravn_app/utils/ffmpeg_checker.py`
- `ravn_app/utils/system_utils.py`
- parts of packaging/update helpers

That means runner consolidation is strong in the main media path, but not universal across the entire repository.

## Main Flows

### Download flow

Intended:

1. User enters a URL in the Download tab.
2. UI delegates to downloader and platform logic.
3. yt-dlp extracts metadata and downloads media.
4. History/config updates are persisted.
5. UI receives progress and completion state.

Current:

- Step 1 exists.
- Step 2 is not fully wired in `main_window.py`.
- Core download behavior exists separately in `downloader.py`.

### Conversion flow

1. UI builds `ConversionSettings`.
2. `VideoConverter` prepares codec args and extra args.
3. `FFmpegRunner` executes the operation.
4. Callbacks update status/progress.

This is one of the more complete runtime areas.

### Persistence flow

- `DatabaseManager` stores downloads, conversions, favorites, and playlists.
- `ConfigManager` stores user settings in JSON.
- Both still default to repo-root files, which conflicts with planned Phase 2 relocation work.

## Tests

Verified in this session:

- `pytest --collect-only -q` -> `283` collected
- `pytest -q` -> `282 passed, 1 skipped`

## Architectural Debt

- Download UI is still not wired end to end.
- Runtime data still lives in the repository root.
- Plugin behavior is represented in two places: `database.py` and `plugin_system.py`.
- Some auxiliary modules still bypass the shared runners.

## Guidance

- Prefer integration work over new standalone modules.
- Use shared runners for new FFmpeg, FFprobe, and yt-dlp execution paths.
- Keep UI thread boundaries explicit for long-running work.
- Treat `TASKS.md` as the backlog of record.
