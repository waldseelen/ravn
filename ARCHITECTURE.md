# ARCHITECTURE

## Overview

RAVN is a layered **desktop + CLI** media application.

- The **desktop runtime** is built with CustomTkinter and now uses the Phase 8 workspace shell: a left sidebar, header, shell-level quick actions, a shared right-side Queue panel, and a lower-left utility area for theme/language toggles plus the Settings workspace entry.
- The **CLI runtime** is built with Click and routes automation-oriented commands into the same core services used by the desktop app.
- Primary external-tool execution is funneled through shared runner abstractions in `ravn_app/core/runners/`.
- Persistence is split between:
  - `ravn_history.db` for downloads / conversions / generic operations
  - `media_library.db` for the local Phase 7 media catalog
- Phase 5 build/distribution work remains open.

Current desktop shell reality:

- Primary workspaces: `Home`, `Download`, `Studio`, `Library`
- Global side panel: `Queue`
- Lower-left sidebar utility area: theme toggle, language toggle, `Settings`
- Shell quick-actions row: live
- Command palette: live (`Ctrl+K`)
- Workspace-level collapsed guidance panels: live
- Phase 8 shell model: complete

## Active Runtime Topology

```text
Desktop entry
ravn.py
  -> setup_logging()
  -> ensure_directories_exist()
  -> migrate_all_legacy_files()
  -> ravn_app.ui.main_window.YouTubeDownloaderApp
      -> sidebar shell
          -> HomeWorkspace
          -> DownloadWorkspace
              -> DownloadTab
              -> TorrentTab
          -> StudioWorkspace
              -> ConverterTab
              -> SubtitleTab
              -> FiltersTab
              -> MixerTab
              -> UtilitiesTab
          -> LibraryWorkspace
              -> LibraryTab
              -> HistoryTab
          -> Queue drawer shell
              -> QueueTab
                  -> QueuePanel
          -> Settings workspace
              -> history_settings_tab.SettingsTab
      -> TaskQueue callback pump
      -> UI callback queue
      -> shared core services / runners / persistence

CLI entry
setup.py console_script `ravn`
  or python -m ravn_app.cli
      -> Click command tree
      -> shared core services / runners / persistence
```

## Repository Skeleton

```text
ravn.py
setup.py
build.ps1
ravn.spec
docs/
  phase8_ux_navigation_overhaul.md
ravn_app/
  cli.py
  core/
    runners/              # shared ffmpeg / yt-dlp / aria2 + mixer helpers
    persistence/          # media library persistence + auto-sync helpers
    app_builder.py        # packaging/build helpers
    config_paths.py       # OS-aware config/data/cache paths + legacy migration helpers
    converter.py          # FFmpeg conversion operations
    database.py           # history DB + config persistence + schema migrations
    downloader.py         # yt-dlp-backed download orchestration
    error_handler.py      # user-friendly error parsing
    i18n.py               # translation lookup/runtime language selection
    logging_config.py     # logging bootstrap
    plugin_system.py      # extension surface (not central to current runtime)
    platform_support.py   # platform helpers
    subtitle_manager.py   # subtitle download/embed helpers
    task_manager.py       # shared async queue/callback model
    theme_catalog.py      # strict dark/light theme model
    torrent_downloader.py # aria2-backed torrent orchestration
    update_manager.py     # app update helpers
  ui/
    components/           # reusable widgets
    tabs/                 # workspace hosts + tab wrappers + feature tabs
    advanced_features.py  # tray / notifications / theme helpers
    converter_tab.py      # existing converter implementation
    history_settings_tab.py
    main_window.py        # main desktop shell
    queue_panel.py        # queue UI
    subtitle_tab.py       # existing subtitle implementation
    ui_components.py      # shared UI helpers/widgets
  translations/
    en.json
    tr.json
  utils/
    ffmpeg_checker.py
    metadata_handler.py
    system_utils.py
tests/
```

## Entry Surfaces

### 1. Desktop Entry

- `ravn.py` is the GUI launcher.
- Startup order is:
  1. `setup_logging()`
  2. `ensure_directories_exist()`
  3. `migrate_all_legacy_files()`
  4. delayed import of `YouTubeDownloaderApp`
- The delayed UI import reduces noisy traceback behavior during early Ctrl+C interrupts.

### 2. CLI Entry

- `ravn_app/cli.py` is the Click-based CLI surface.
- It is reachable through:
  - `python -m ravn_app.cli ...`
  - installed console script `ravn ...` via `setup.py`
- Current CLI surface includes:
  - `download`
  - `convert`
  - `info`
  - `subtitle`
  - `history`
  - `torrent`
  - `mixer ...`
  - `library ...`
  - `filters`
  - `utilities ...`
  - `serve` placeholder
- CLI commands support human-readable output plus `--json` where implemented.

## Layer Model

### 1. Shell / UI Orchestration Layer

Primary orchestrator: `ravn_app/ui/main_window.py`

`YouTubeDownloaderApp` is intentionally a thin shell that owns application-wide concerns and composes feature modules. It is responsible for:

- creating shared services:
  - `DatabaseManager`
  - `ConfigManager`
  - i18n runtime
  - `PlatformManager`
  - `YouTubeDownloader`
  - global `TaskQueue`
  - `MediaLibraryAutoAdder`
- applying the active theme
- composing the desktop shell:
  - left sidebar
  - header
  - header quick actions
  - main workspace host
  - shared drawer shell
  - footer status area
  - lower-left utility toggles for theme/language plus Settings access
- switching workspaces and drawers
- routing shell-level shortcuts and command-palette actions
- tray integration and close-to-tray behavior
- pumping task callbacks and deferred UI callbacks on the main thread
- rebuilding visible UI when language or theme changes at runtime, including tray/menu text refresh for live language switching

#### Current Shell Composition

- **Sidebar navigation**
  - `Home`
  - `Download`
  - `Studio`
  - `Library`
- **Header utility actions**
  - Command Palette button
  - Queue button with live pending/running count
- **Header quick actions**
  - Paste URL
  - Add Torrent
  - Convert File
  - Open Library
- **Shared drawer shell**
  - Queue drawer
- **Sidebar utility area**
  - Theme toggle
  - Language toggle
  - Settings opens as an independent workspace
- **Footer**
  - shell-level status text

#### Global Shortcuts

`main_window.py` currently binds shell-level shortcuts for the visible feature surface:

- `Ctrl+Enter`
- `Escape`
- `Ctrl+L`
- `Ctrl+K` -> open Command Palette
- `Ctrl+,` -> open Settings workspace

Shortcut routing is delegated to the currently visible feature widget where applicable, and drawer open/close now restores focus more predictably at the shell level.

#### Adaptive Layout Behavior

The shell currently applies lightweight adaptive behavior rather than a full responsive-layout subsystem:

- content paddings are bounded to keep the main stage from stretching too wide
- the shell targets compact / standard / wide max-content bands instead of one fixed width
- sidebar width adapts between compact and wide desktop sizes
- drawer width grows through multiple steps instead of staying fixed
- quick-action and command-palette button labels shorten in tighter widths to avoid unnecessary header crowding
- primary workspaces stay mounted in a shared host and switch via in-place raising rather than repeated unmount/remount cycles, reducing visible redraw flash during navigation
- theme changes now apply without a full shell rebuild, while runtime language changes use a lighter in-place refresh path for shell/workspace text

### 2. Workspace Layer

The top-level app experience is now grouped by user intent rather than exposing every feature as a first-class top navigation item.

#### `HomeWorkspace`

File: `ravn_app/ui/tabs/home_workspace.py`

Responsibilities:

- dashboard landing screen
- quick-start cards into major workflows
- summary cards backed by `DatabaseManager.get_statistics()` and `TaskQueue` counts
- recent activity list built from recent downloads and generic operations

#### `DownloadWorkspace`

File: `ravn_app/ui/tabs/download_workspace.py`

Responsibilities:

- grouped entry point for:
  - URL downloads
  - playlist workflows
  - batch downloads
  - torrent workflows
- segmented navigation switches between:
  - shared `DownloadTab` for URL / playlist / batch modes
  - dedicated `TorrentTab` for torrent manager behavior
- batch mode is toggled by synchronizing internal state on the reused `DownloadTab`

#### `StudioWorkspace`

File: `ravn_app/ui/tabs/studio_workspace.py`

Responsibilities:

- grouped media-processing workspace
- internal `CTkTabview` sub-navigation for:
  - Convert
  - Subtitle
  - Filters
  - Mixer
  - Utilities
- reuses existing feature modules instead of rewriting tool logic

Important nuance:

- `ConverterTab` and `SubtitleTab` are older standalone feature implementations reused inside the new workspace shell.
- `FiltersTab`, `MixerTab`, and `UtilitiesTab` are newer Phase 7+ queue-aware modules.

#### `LibraryWorkspace`

File: `ravn_app/ui/tabs/library_workspace.py`

Responsibilities:

- grouped library-oriented workspace
- internal `CTkTabview` sub-navigation for:
  - Library
  - History
- `LibraryTab` handles media-library management
- `HistoryTab` is a compatibility wrapper around `history_settings_tab.HistoryTab`

### 3. Feature UI Layer

Feature logic lives below the shell/workspace level.

#### Download / Torrent

- `tabs/download_tab.py`
  - classic downloader logic
  - URL metadata fetch
  - playlist selection/sorting integration
  - batch mode handling
  - queue integration for batch work
- `tabs/torrent_tab.py`
  - dedicated torrent manager UI
  - session rows with progress / speed / ETA / peers / seeders
  - queued / paused / completed session handling
  - pause / resume / open behavior
  - child rows for discovered payload files

#### Media Processing

- `ui/converter_tab.py`
  - main converter implementation
  - wrapped by `ui/tabs/converter_tab.py`
- `ui/subtitle_tab.py`
  - main subtitle implementation
  - wrapped by `ui/tabs/subtitle_tab.py`
- `tabs/filters_tab.py`
  - FFmpeg-based filter workflows
  - queue-aware Phase 7 operations UI
- `tabs/mixer_tab.py`
  - audio/video mixing workflows
  - queue-aware Phase 7 operations UI
- `tabs/utilities_tab.py`
  - comprehensive media utility helpers (24 operations across 4 categories)
  - quick helpers: remux, extract-audio, mute, trim, preview-clip, thumbnail
  - audio utilities: volume, fade, bitrate, channels, silence-detect, loudnorm
  - video utilities: scale, crop, pad, rotate, fps, color, blur/sharpen, deinterlace
  - smart helpers: blackdetect, scene-preview, scene-thumbnail
  - queue-aware Phase 7+ operations UI
  - auto-library registration support

#### Library / History / Settings

- `tabs/library_tab.py`
  - local media catalog browsing
  - import/search/filter/export
  - collection-aware library operations
- `ui/history_settings_tab.py`
  - compact one-page settings implementation
  - history implementation reused through wrappers
- `tabs/history_tab.py`
  - wrapper around `history_settings_tab.HistoryTab`
- `tabs/settings_tab.py`
  - wrapper around `history_settings_tab.SettingsTab`
- `tabs/queue_tab.py`
  - wrapper that hosts `QueuePanel`
- `ui/queue_panel.py`
  - queue visualization widgets
  - polls `TaskQueue` state and renders item cards

#### Shared UI Components

- `ui/components/error_panel.py`
  - inline user-friendly error box with details toggle
- `ui/components/playlist_sort_dialog.py`
  - sortable playlist picker with selected-count / selected-size summary
- `ui/components/playlist_item.py`
  - playlist row widget
- `ui/components/url_input.py`
  - URL input row helpers
- `ui/ui_components.py`
  - shared helpers and primitives such as `ToastManager`, `Tooltip`, `style_combo`, `style_entry`, `bind_focus_ring`, `set_button_loading_state`

### 4. Core Services Layer

#### Process Runners

Directory: `ravn_app/core/runners/`

- `base.py`
  - `BaseRunner`
  - shared availability lookup, process lifecycle, cancel behavior, timeout handling, and normalized `RunnerResult`
- `ffmpeg.py`
  - `FFmpegRunner`
- `ytdlp.py`
  - `YtDlpRunner`
- `aria2.py`
  - `Aria2Runner`
  - torrent progress parsing via `TorrentProgressSnapshot`
- `audio_mixer.py`
  - `AudioMixerRunner`
- `video_mixer.py`
  - `VideoMixerRunner`

#### Domain Services

- `downloader.py`
  - yt-dlp-backed media download orchestration for the download UI and CLI
- `converter.py`
  - FFmpeg-backed conversion/domain logic
- `subtitle_manager.py`
  - subtitle download/embed helpers using FFmpeg + yt-dlp
- `torrent_downloader.py`
  - high-level torrent orchestration built on `Aria2Runner`
  - mode semantics:
    - `FULL`
    - `SEQUENTIAL`
    - `STREAM`
- `task_manager.py`
  - global thread-safe task queue
  - worker threads
  - queued callback dispatch back to the UI thread
  - cancellation hooks
  - Phase 7 task types:
    - `mixer_audio`
    - `mixer_video`
    - `apply_filters`
    - `library_scan`
    - `utilities_operation`
- `media_helpers.py`
   - comprehensive FFmpeg-backed media utility operations
   - 24 operations across 4 categories:
     - quick helpers: remux, extract-audio, mute, trim, preview-clip, thumbnail
     - audio utilities: volume, fade, bitrate, channels, silence-detect, loudnorm
     - video utilities: scale, crop, pad, rotate, fps, brightness/contrast/saturation, blur/sharpen, deinterlace
     - smart helpers: blackdetect, scene-preview, scene-thumbnail
   - uses `FFmpegRunner` for consistent process execution
   - returns `RunnerResult` with metadata and summaries
- `database.py`
  - download / conversion / operation history persistence
  - config JSON persistence via `ConfigManager`
  - schema versioning + migrations for the history database
- `persistence/media_library.py`
  - separate SQLite media catalog
  - tags, collections, search history, stats, export
- `persistence/library_sync.py`
  - `MediaLibraryAutoAdder`
  - config-gated auto-registration of generated outputs
- `error_handler.py`
  - user-facing FFmpeg / yt-dlp / aria2 error normalization
- `config_paths.py`
  - OS-aware config/data/cache paths
  - legacy file discovery + migration helpers
- `theme_catalog.py`
  - strict `dark` / `light` theme model with alias normalization
- `i18n.py`
  - runtime translation lookup and language switching
- `logging_config.py`
  - logging bootstrap
- `plugin_system.py`
  - plugin/discovery scaffolding exists as an extension boundary, but it is not central to the current runtime shell

### 5. Utility Layer

- `utils/metadata_handler.py`
  - metadata extraction via FFprobe
  - lightweight tag/thumbnail helpers
  - used by media-library flows and auto-registration
- `utils/ffmpeg_checker.py`
  - FFmpeg availability helpers
- `utils/system_utils.py`
  - miscellaneous OS/system helpers

## Process Execution Model

### Shared Runner Path

Primary media execution paths are intentionally consolidated around `ravn_app/core/runners/`:

- `converter.py` -> `FFmpegRunner`
- `downloader.py` -> `YtDlpRunner`
- `audio_normalizer.py` -> `FFmpegRunner`
- `subtitle_manager.py` -> `FFmpegRunner` + `YtDlpRunner`
- `torrent_downloader.py` -> `Aria2Runner`
- `runners/audio_mixer.py` -> `FFmpegRunner`
- `runners/video_mixer.py` -> `FFmpegRunner`

### Queue-Backed vs Direct Feature Execution

The current system mixes older direct feature implementations with newer queue-backed flows:

- **Queue-backed**
  - batch downloads
  - filters
  - mixer
  - library scan/import style operations
- **Direct / legacy-style feature execution**
  - converter tab flow
  - subtitle tab flow
  - some UI-triggered OS-open helpers

This is an intentional transitional architecture: new shell composition reuses working feature modules rather than rewriting all execution paths at once.

### Remaining Direct `subprocess` Usage

Outside the shared runner package, direct `subprocess` usage still exists in a few auxiliary or OS-integration paths, including examples such as:

- shell/file-open helpers in:
  - `ui/main_window.py`
  - `ui/tabs/library_tab.py`
  - `ui/tabs/download_tab.py`
  - `ui/tabs/torrent_tab.py`
- utility/build/platform modules such as:
  - `utils/system_utils.py`
  - `utils/ffmpeg_checker.py`
  - `core/app_builder.py`
  - `core/platform_support.py`
  - `core/update_manager.py`
  - parts of `core/animation_manager.py`

This cleanup is tracked in `TASKS.md` as `[MNT-01]`.
It is real architectural debt, but it is mostly outside the critical shared media runner path.

## Persistence Model

### 1. Config + History Persistence

Managed through `config_paths.py` and `database.py`.

- config file path: OS-aware JSON config
- history DB path: OS-aware SQLite database
- startup ensures directories exist before app init
- legacy root-level files are migrated on startup

`DatabaseManager` currently owns:

- `downloads` table
- `conversions` table
- `favorites` table
- `playlists` table
- `operations` table for generic Phase 7 work
- `schema_version` + `migration_history`

Current history DB schema version is managed in code through `LATEST_SCHEMA_VERSION = 3`.

### 2. Media Library Persistence

Managed through `ravn_app/core/persistence/media_library.py`.

Separate DB concerns from the history DB:

- media items
- tags
- collections
- collection items
- search history
- export helpers
- library statistics

This keeps the local searchable media catalog independent from download/conversion history.

### 3. Auto-Library Registration

`MediaLibraryAutoAdder` acts as the bridge between generated outputs and the media catalog.

Flow:

1. desktop feature completes work
2. shell schedules background auto-registration thread
3. `MediaLibraryAutoAdder` normalizes source type and checks config flags
4. `MetadataHandler` enriches media record data
5. successful registration schedules UI refresh callbacks for:
   - `LibraryTab`
   - `HomeWorkspace`

## Configuration / Theme / I18N Model

### Configuration

`ConfigManager` persists a JSON configuration file and validates loaded values against the schema in `config_paths.py`.

Notable config properties:

- legacy flat settings still supported
- nested sections now exist for:
  - `mixer`
  - `library`
  - `filters`
- torrent settings remain flat today (`aria2c_path`, seed/max connection values)

### Theme

- theme IDs normalize to `dark` or `light`
- legacy aliases are accepted but canonicalized
- shell and feature surfaces rely on `design_tokens.py` + `ThemeManager`

### Internationalization

- all new user-facing strings should resolve through translation keys
- supported language packs:
  - `ravn_app/translations/tr.json`
  - `ravn_app/translations/en.json`
- `main_window.refresh_i18n()` rebuilds the visible shell so language changes apply at runtime

## Main Runtime Flows

### Desktop Startup Flow

1. `ravn.py` initializes logging and storage directories.
2. Legacy config/history files are migrated if needed.
3. `YouTubeDownloaderApp` creates shared managers/services.
4. The shell composes workspaces and drawers.
5. A recurring `after(...)` pump processes:
   - `TaskQueue` callbacks
   - deferred UI callbacks
   - header queue-count refresh
   - periodic Home dashboard refresh

### Navigation Flow

1. Sidebar switches primary workspaces.
2. Queue button opens the shared drawer shell with `QueueTab`.
3. Lower-left Settings entry or `Ctrl+,` opens the dedicated Settings workspace.
4. `Escape` closes the active queue drawer before delegating to feature-level cancel behavior.

### Download Flow

1. User lands in `DownloadWorkspace`.
2. Workspace mode selects `url`, `playlist`, `batch`, or `torrent`.
3. Non-torrent modes reuse `DownloadTab`.
4. Torrent mode mounts `TorrentTab`.
5. Media work flows to `YouTubeDownloader` or `TorrentDownloader`.
6. Progress/error/success updates return through callbacks to the UI.
7. Successful outputs may be auto-added into `MediaLibrary`.

### Studio Flow

1. User opens `StudioWorkspace`.
2. Internal tabview routes to Convert / Subtitle / Filters / Mixer / Utilities.
3. Convert/subtitle reuse existing feature implementations.
4. Filters/mixer/utilities use Phase 7+ runner helpers and queue-backed workflows.
5. Completed outputs may be persisted into generic operation history and optionally auto-added to the media library.

### Library Flow

1. User opens `LibraryWorkspace`.
2. `LibraryTab` interacts with `MediaLibrary` for import/search/collections/export.
3. History subview reads persisted rows from `DatabaseManager`.
4. Home dashboard and library views refresh when new outputs are auto-registered.

### CLI Flow

1. Click parses command-line arguments.
2. CLI command calls shared core modules/runners.
3. Optional DB/library persistence is applied where the command supports it.
4. Output is emitted as text or JSON.

## Testing Snapshot

Last documented validated baseline remains:

- full-suite baseline: `528 passed, 1 skipped` (`529` collected)
- targeted Phase 7 / queue / library regression sweep: `191 passed`
- targeted UI/config sweep: `87 passed`
- targeted torrent/UI sweep: `153 passed`

Treat these as the last recorded validation snapshot, not a guarantee about unverified working-tree changes.

## Architectural Debt

- Some feature implementations still live in root `ui/` while `ui/tabs/` provides compatibility wrappers around them.
- `history_settings_tab.py` still contains two concerns (history + settings) that are now surfaced separately through wrappers/drawers.
- Direct `subprocess` usage outside shared runners is still present and tracked as `[MNT-01]`.
- Plugin surface area is split between `core/plugin_system.py` and legacy plugin stubs in `database.py`; this is not yet a clean single extension boundary.
- Phase 8 shell work is complete; future changes should be treated as follow-up refinements rather than unfinished shell migration.
- Build/distribution automation (Phase 5) remains open.

## Guidance

- Keep `main_window.py` thin; compose features there, but keep feature logic in `ui/tabs/` and reusable pieces in `ui/components/`.
- Prefer shared runners for new external-tool execution paths.
- Reuse existing feature modules when evolving shell/navigation structure instead of cloning logic.
- Keep UI thread boundaries explicit: worker threads should report back through queued callbacks, not mutate widgets directly.
- Keep user-facing strings translation-key based in both TR and EN packs.
- Keep theme behavior constrained to canonical `dark` / `light` IDs.
- When architecture boundaries move, keep `README.md`, `PROGRESS.md`, `TASKS.md`, and `AGENTS.md` synchronized with this file.
