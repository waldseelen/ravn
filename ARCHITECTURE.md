# ARCHITECTURE

## Overview

RAVN is a layered desktop media application with a modular UI shell and shared process runners.
The current architecture is feature-complete for download/convert/subtitle core flows, while build and distribution work remains in backlog.

```text
ravn.py
  -> ravn_app.ui.main_window.YouTubeDownloaderApp
      -> ravn_app.ui.tabs.*
          -> ravn_app.ui.components.*
      -> ravn_app.core.* services
      -> task queue + async workers
```

## Current UI Skeleton

```text
ravn_app/ui/
  main_window.py            # Window + TabView orchestration (thin shell)
  tabs/
    download_tab.py         # Download flow and playlist/batch logic
    queue_tab.py            # Queue panel host
    converter_tab.py        # Compatibility wrapper
    subtitle_tab.py         # Compatibility wrapper
    history_tab.py          # Compatibility wrapper
    settings_tab.py         # Compatibility wrapper
  components/
    error_panel.py          # Reusable error box + technical details toggle
    playlist_item.py        # Playlist row widget
    url_input.py            # URL entry row + validation/status labels
  queue_panel.py            # Queue widgets
  converter_tab.py          # Existing converter implementation
  subtitle_tab.py           # Existing subtitle implementation
  history_settings_tab.py   # Existing history/settings implementation
```

## Layers

### 1. Entry Layer

- `ravn.py` initializes logging and OS-aware directories, runs legacy migration, then starts UI.
- `ravn_app/ui/main_window.py` is responsible for top-level window lifecycle, tray integration, and tab composition.

### 2. UI Layer

- `tabs/download_tab.py` owns download-specific state and behaviors (single, playlist, batch).
- `components/error_panel.py` encapsulates reusable error presentation with expandable technical details.
- `ui_components.py` provides reusable widgets (`ToastManager`, `Tooltip`, inline form feedback components).
- Queue, converter, subtitle, history, settings remain separated into dedicated tab modules/components.

Threading model:

- Long-running operations run in background threads.
- All UI mutation is marshaled via `after(...)` back to main thread.

### 3. Core Layer

- `runners/`: shared process abstraction package (`FFmpegRunner`, `YtDlpRunner`, `Aria2Runner`).
  - `runners/aria2.py`: `Aria2Runner` — magnet/torrent downloads via aria2c with progress callbacks.
- `downloader.py`: yt-dlp-backed download API used by `DownloadTab`.
- `torrent_downloader.py`: `TorrentDownloader` wraps `Aria2Runner`; supports FULL, SEQUENTIAL, STREAM modes.
- `converter.py`: FFmpeg-backed conversion and media utility operations.
- `task_manager.py`: queueing and cancellation for async jobs.
- `error_handler.py`: end-user error parsing and normalization.
- `database.py`: download/conversion history and settings persistence adapters.
- `config_paths.py`: OS-specific data/config directory strategy.

### 4. Utility Layer

- `ravn_app/utils/*` contains environment and filesystem support helpers.

## Execution Model

### Shared Runner Path

Primary media execution paths are routed through `ravn_app/core/runners/`:

- `converter.py` -> `FFmpegRunner`
- `downloader.py` -> `YtDlpRunner`
- `audio_normalizer.py` -> `FFmpegRunner`
- `subtitle_manager.py` -> `FFmpegRunner` + `YtDlpRunner`
- `torrent_downloader.py` -> `Aria2Runner`

### Remaining Direct `subprocess` Usage

Some auxiliary/packaging paths still call `subprocess` directly (for example `platform_support.py`, some utilities, and packaging helpers).
This is an intentional cleanup target, but not on the critical media path.

## Main Runtime Flows

### Download Flow

1. User enters URL in `DownloadTab`.
2. Metadata fetch distinguishes single-video vs playlist.
3. Selected quality/format map to downloader enums.
4. Download runs in background thread(s).
5. Progress/error/success updates are applied on UI thread.
6. Batch mode enqueues tasks through `TaskQueue`.

### Conversion Flow

1. UI builds conversion settings.
2. `VideoConverter` composes FFmpeg args.
3. `FFmpegRunner` executes conversion.
4. Progress callbacks update converter tab state.

### Torrent / Magnet Akışı

URL → _detect_url_protocol() → TorrentDownloader → Aria2Runner → aria2c
Modes: FULL | SEQUENTIAL | STREAM (local HTTP server on random port)

1. `DownloadTab` detects magnet: URI or .torrent file (URL or drag-drop).
2. Torrent mode selector appears (Tam İndir / Sıralı / Akışla İzle).
3. `TorrentDownloader` delegates to `Aria2Runner` which spawns aria2c subprocess.
4. Progress callbacks update UI on main thread via `after(...)`.
5. STREAM mode starts a local HTTP server; "Oynatıcıda Aç" button opens media player.

### Persistence Flow

- Download/conversion history and user config are managed via `DatabaseManager` and `ConfigManager`.
- Paths are OS-aware via `config_paths.py` and startup migration in `ravn.py`.

## Testing Snapshot

- Last known full-suite baseline: `417 passed, 1 skipped` (`418` collected).
- UI modularization session validation: targeted UI suites executed successfully.

## Architectural Debt

- Some legacy tab implementations are still in root `ui/` with compatibility wrappers in `ui/tabs/`.
- Auxiliary modules still contain direct `subprocess` calls outside runner abstraction.
- Build/distribution pipeline (Phase 5) remains open.

## Guidance

- Keep `main_window.py` thin; place feature logic in `tabs/` and reusable pieces in `components/`.
- Prefer shared runners for all new external tool execution.
- Keep UI thread boundaries explicit (`threading` + `after`).
- Treat `TASKS.md` as backlog of record and sync architecture docs when module boundaries change.
