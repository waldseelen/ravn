# RAVN

RAVN is a desktop media manager built with CustomTkinter. Core download, convert, subtitle, playlist, and torrent flows are complete. Current roadmap focus is Phase 5 build/packaging/distribution.

## What RAVN Can Do

- Download videos and audio from supported platforms via URL.
- Fetch playlist metadata, sort/select items, and download only what you choose.
- Run batch downloads (up to 50 URLs) through the queue.
- Convert media formats with FFmpeg and track progress in real time.
- Download/process/embed subtitles.
- Manage queue, history, and settings in a modular desktop UI.
- Use CLI for automation (`download`, `convert`, `info`, `subtitle`, `history`, `torrent`).

## Torrent / Magnet Features

Torrent support is fully integrated (Phase 6 complete):

- Magnet links and `.torrent` files are auto-detected in download flow.
- Download modes:
  - `FULL` (standard complete download)
  - `SEQUENTIAL` (piece order optimized for early playback)
  - `STREAM` (local HTTP stream endpoint + quick play action)
- `.torrent` drag-and-drop to URL input is supported (with safe fallback when DnD backend is unavailable).
- aria2-backed progress and errors are surfaced to UI feedback/toasts.
- Torrent settings are available in UI (`aria2c path`, `seed time`, `max connections`).
- CLI command available: `ravn torrent`.

## Status

- Main entry point: python ravn.py
- UI tabs: download, convert, subtitle, queue, history, settings
- Download tab supports single URL, playlist selection/sorting, batch queue (up to 50), and magnet/torrent flows
- Main media execution uses shared runners from ravn_app/core/runners/
- Main window is a thin orchestrator for tab composition and lifecycle
- Reusable download UI components live in ravn_app/ui/components/
- Config and history use OS-aware directories (Windows: %APPDATA%/ravn, Linux: ~/.config/ravn)
- Theme system is strict 2-theme: dark and light (legacy names are normalized)
- Settings UI is compact one-page scroll layout
- Playlist fetch/sort dialog includes selected total-size summary and high-contrast visibility fixes
- Phases 1-4C and Phase 6 complete; Phase 5 remains open in TASKS.md

## Requirements

- Python 3.9+
- FFmpeg and FFprobe on PATH
- Packages from requirements.txt

```bash
pip install -r requirements.txt
```

## Run

```bash
python ravn.py
```

Alternative:

```bash
python -m ravn_app.ui.main_window
```

CLI examples:

```bash
ravn download "https://example.com/video" --quality 1080p --format mp4
ravn convert input.mp4 --format mkv --quality high
ravn torrent "magnet:?xt=urn:btih:..." --mode stream
```

## Tests

Verified on 2026-03-30:

- Full baseline: pytest -q -> 417 passed, 1 skipped (418 collected)
- Recent targeted regression suites for UI/config updates: passing (including 85-test targeted run)

Useful commands:

```bash
pytest
pytest -q --tb=no
pytest --collect-only -q
pytest tests/test_ui_logic.py -q
```

## Build

```powershell
./build.ps1 check
./build.ps1 test
./build.ps1 run
```

PyInstaller-related files already exist in ravn.spec and ravn_app/core/app_builder.py.

## Repository Layout

```text
ravn_app/
  core/    media logic, runners, persistence, update, packaging
  ui/      CustomTkinter shell, tabs, components, tokens
  utils/   ffmpeg/file/system helpers
tests/     unit and integration-style tests
```

## Documentation

- CLAUDE.md - unified agent context and working rules
- ARCHITECTURE.md - system structure and design constraints
- PROGRESS.md - validated implementation snapshot
- TASKS.md - backlog and active workboard

## Current Priorities

1. Complete Phase 1 UI consistency tasks listed in TASKS.md.
2. Reduce remaining direct subprocess usage in auxiliary modules.
3. Finish Phase 5 packaging and distribution pipeline.
