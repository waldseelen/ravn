# RAVN

RAVN is a desktop + CLI media manager. The desktop app is built with CustomTkinter, while the CLI is built with Click and reuses the same core services. Core download, convert, subtitle, playlist, torrent, and Phase 7 media-management flows are complete, including shared queue/history persistence and automatic media-library indexing for generated outputs. Phase 8 UX/navigation work is also complete: the desktop shell now uses primary workspaces (`Home`, `Download`, `Studio`, `Library`), Queue is exposed from a global right-side panel, Settings live as an independent lower-left sidebar utility workspace, compact theme/language toggles sit directly above Settings, `Ctrl+K` opens a command palette, and the shell adapts more cleanly across compact and wide desktop widths. Phase 5 build/packaging/distribution still remains open.

## What RAVN Can Do

- Download videos and audio from supported platforms via URL.
- Fetch playlist metadata, sort/select items, and download only what you choose.
- Run batch downloads (up to 50 URLs) through the queue.
- Convert media formats with FFmpeg and track progress in real time.
- Download/process/embed subtitles.
- Mix audio tracks, concatenate media, overlay/PiP videos, and apply FFmpeg-based video filters from dedicated desktop tabs or the CLI.
- Run comprehensive media utility operations: quick helpers (remux, extract-audio, mute, trim, preview-clip, thumbnail), audio utilities (volume, fade, bitrate, channels, silence-detect, loudnorm), video utilities (scale, crop, pad, rotate, fps, brightness/contrast/saturation, blur/sharpen, deinterlace), and smart helpers (blackdetect, scene-preview, scene-thumbnail) from the Utilities desktop tab or CLI.
- Maintain a local SQLite media library with tags, collections, search filters, duplicate detection, and JSON/CSV export from the desktop UI or CLI.
- Automatically add supported download, conversion, mixer, and filter outputs into the local media library.
- Run mixer/filter/library jobs through the shared queue and review persisted download / conversion / Phase 7 operation history in the desktop UI.
- Work from a grouped desktop shell with `Home`, `Download`, `Studio`, and `Library` workspaces.
- Open Queue from a global shell panel, access Settings from an independent lower-left sidebar utility entry, and switch theme/language instantly from compact sidebar toggles.
- Use quick shell actions for paste URL, torrent, convert file, library access, and queue access.
- Trigger the global command palette with `Ctrl+K` for keyboard-first navigation and common actions.
- Download / Studio / Library workspaces keep workflow guidance collapsed by default for cleaner progressive disclosure.
- The shell adapts between compact and wide desktop widths with responsive sidebar/drawer sizing and shorter quick-action labels when space tightens.
- Workspace switching now keeps views mounted and raises them in place for smoother transitions with less visible redraw flicker.
- Theme switching now applies in place without a full shell rebuild; language switching refreshes shell/workspace text with lighter in-place updates.
- Use shell-level keyboard shortcuts such as `Ctrl+Enter`, `Escape`, `Ctrl+L`, `Ctrl+K`, and `Ctrl+,` for fast actions and settings access.
- Use CLI for automation (`download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, `utilities`).

## Torrent / Magnet Features

Torrent support is fully integrated (Phase 6 complete):

- Magnet links and `.torrent` files are auto-detected in download flow.
- Download modes:
  - `FULL` (standard complete download)
  - `SEQUENTIAL` (piece order optimized for early playback)
  - `STREAM` (local HTTP stream endpoint + quick play action)
- `.torrent` drag-and-drop to URL input is supported (with safe fallback when DnD backend is unavailable).
- Dedicated torrent tab now shows a manager-style status table with torrent/file name, progress, total size, downloaded, remaining, speed, ETA, peers, and seeders.
- Multiple torrents can be queued from the torrent tab, paused, resumed, auto-advanced one-by-one, and filtered by queued / paused / completed state.
- Completed/discovered torrent payload files are shown as child rows under each torrent session.
- aria2-backed progress and errors are surfaced to UI feedback/toasts.
- `Open in Player` now prefers the primary downloaded media file and falls back safely when a stream URL is unavailable.
- Torrent settings are available in UI (`aria2c path`, `seed time`, `max connections`).
- CLI command available once the package is installed (`ravn torrent`) or directly from a source checkout via `python -m ravn_app.cli torrent ...`.

## Status

- Main entry point: python ravn.py
- Primary desktop workspaces: home, download, studio, library
- Queue is now exposed from a global right-side panel instead of primary navigation
- Settings now open as an independent lower-left sidebar utility workspace instead of a floating drawer-triggered panel
- Theme and language selectors were removed from the Settings page in favor of shell-level sidebar toggles
- Download workspace supports single URL, playlist selection/sorting, batch queue (up to 50), and magnet/torrent flows
- Download workspace now groups the classic downloader and torrent manager under one segmented shell
- Studio workspace groups convert, subtitle, filters, and mixer tools
- Library workspace groups media library and history views
- Dedicated torrent surface still provides queueable session rows with live torrent name / progress / total size / downloaded / remaining / speed / ETA / peers / seeders tracking, per-file child rows, queued-paused-completed filtering, pause/resume controls, and improved player open fallback
- Main media execution uses shared runners from ravn_app/core/runners/
- Main window is a thin orchestrator for workspace composition, shell quick actions, command-palette routing, accessibility-aware utility panels, adaptive shell layout, tray integration, and main-thread callback pumping
- Reusable download UI components live in ravn_app/ui/components/
- Config and history use OS-aware directories (Windows: %APPDATA%/ravn, Linux: ~/.config/ravn)
- Theme system is strict 2-theme: dark and light (legacy names are normalized)
- Settings UI is compact one-page scroll layout
- Playlist fetch/sort dialog includes selected total-size summary and high-contrast visibility fixes
- Phase 7 desktop/media-management stack is active end-to-end (`AudioMixerRunner`, `VideoMixerRunner`, `MediaLibrary`, `MetadataHandler`, `mixer_tab.py`, `filters_tab.py`, `library_tab.py`, TaskQueue wiring, persisted operation history, automatic library indexing)
- Phases 1-4C, Phase 6, Phase 7, and Phase 8 are complete; Phase 5 remains open in TASKS.md

## Requirements

- Python 3.9+
- FFmpeg and FFprobe on PATH
- `aria2c` installed separately for torrent/magnet support (`winget install aria2`, `brew install aria2`, or `apt install aria2`)
- Packages from requirements.txt

```bash
pip install -r requirements.txt
```

## Run

Desktop app from a source checkout:

```bash
python ravn.py
```

Alternative module form:

```bash
python -m ravn_app.ui.main_window
```

Install the package locally if you want the `ravn` console command:

```bash
pip install -e .
```

CLI usage from a source checkout:

```bash
python -m ravn_app.cli download "https://example.com/video" --quality 1080p --format mp4
python -m ravn_app.cli convert input.mp4 --format mkv --quality high
python -m ravn_app.cli torrent "magnet:?xt=urn:btih:..." --sequential
```

CLI usage after `pip install -e .` / packaged install:

```bash
ravn mixer audio --input intro.mp3 --input main.mp3 --crossfade 1.5 --output merged.mp3
ravn mixer video clip1.mp4 clip2.mp4 --operation concat --output combined.mp4
ravn library add ./video.mp4 --title "My Video" --tags work,tutorial
ravn library search --query video --format mp4 --tags tutorial --json
ravn filters input.mp4 --brightness 20 --contrast 1.2 --blur 2 --output filtered.mp4
```

## Tests

Verified on 2026-04-01:

- Full baseline: `pytest -q` -> `538 passed, 1 skipped` (539 collected)
- Phase 7 / queue / library regression sweep: `191 passed`
- UI/config regression suites: `98 passed`
- Shell/navigation + config/database regression sweep: `153 passed`
- Torrent/UI follow-up suite: `153 passed`

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

- AGENTS.md - canonical shared agent context and workflow rules
- CLAUDE.md - Claude Code compatibility entrypoint/addendum
- ARCHITECTURE.md - system structure and design constraints
- PROGRESS.md - validated implementation snapshot
- TASKS.md - backlog and active workboard
- docs/phase8_ux_navigation_overhaul.md - approved Phase 8 UX/navigation shell plan

## Current Priorities

1. Finish Phase 5 packaging and distribution pipeline.
2. Validate bundled FFmpeg/runtime behavior in clean installer environments.
3. Continue migrating auxiliary direct `subprocess` paths toward shared runner coverage.
4. Maintain and harden the completed Phase 8 workspace shell as follow-up regressions or UX refinements appear.
