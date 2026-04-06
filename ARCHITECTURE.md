# ARCHITECTURE

## 1. Purpose

RAVN is a layered **desktop + CLI media application**.

It combines four major product areas under one codebase:

1. **Acquisition** — download URLs, playlists, batches, torrents, and magnets
2. **Studio processing** — convert, subtitle, filter, mix, and utility workflows
3. **Organization** — history persistence and local media-library management
4. **Shell / automation** — adaptive desktop navigation plus shared-core CLI access

The architectural direction is intentionally:

- **shared-core first**
- **runner-driven external tool execution**
- **thin shell orchestration**
- **modular feature surfaces**
- **OS-aware persistence paths**
- **translation-key-based UI strings**

Phase 5 build/distribution remains open, but the functional runtime architecture for desktop, CLI, queue, history, and media-library flows is already in place.

---

## 2. High-Level Runtime Model

### Desktop runtime

- Entry point: `ravn.py`
- UI shell: `ravn_app/ui/main_window.py`
- Desktop toolkit: CustomTkinter
- Main interaction model:
  - workspace shell
  - feature tabs
  - queue drawer
  - settings workspace
  - command palette

### CLI runtime

- Entry point: `ravn_app/cli.py`
- CLI toolkit: Click
- CLI philosophy:
  - reuse shared services
  - reuse shared runners
  - expose product-level concepts, not raw upstream flag dumps
  - support text and JSON output

### External execution model

All primary media/tool processes are intended to run through shared runners in:

- `ravn_app/core/runners/ffmpeg.py`
- `ravn_app/core/runners/ytdlp.py`
- `ravn_app/core/runners/aria2.py`
- `ravn_app/core/runners/audio_mixer.py`
- `ravn_app/core/runners/video_mixer.py`

### Persistence model

Persistence is split into two SQLite domains plus config/data paths:

- **history/config persistence**
  - `ravn_app/core/database.py`
  - history rows for downloads / conversions / generic operations
- **media library persistence**
  - `ravn_app/core/persistence/media_library.py`
- **OS-aware directories**
  - `ravn_app/core/config_paths.py`

---

## 3. Active Runtime Topology

```text
Desktop
ravn.py
  -> setup_logging()
  -> ensure_directories_exist()
  -> migrate_all_legacy_files()
  -> check_tool_dependencies()
  -> YouTubeDownloaderApp
      -> shell composition
      -> shared services
      -> workspace host
      -> queue drawer
      -> settings workspace
      -> task callback pump
      -> deferred UI callback pump

CLI
python -m ravn_app.cli / console script `ravn`
  -> Click command tree
  -> shared core services
  -> shared runner-backed operations
  -> optional DB / library persistence
  -> text or JSON output
```

---

## 4. Repository Structure

```text
ravn.py
setup.py
build.ps1
ravn.spec

.github/
  workflows/
    tests.yml
    windows-package.yml
    windows-release.yml

assets/
  ffmpeg/
    win64/
      README.md

ravn_app/
  cli.py
  core/
    app_builder.py
    animation_manager.py
    audio_normalizer.py
    config_paths.py
    converter.py
    database.py
    download_metadata.py
    download_naming.py
    download_profiles.py
    downloader.py
    error_handler.py
    i18n.py
    logging_config.py
    media_helpers.py
    tool_health.py
    platform_support.py
    plugin_system.py
    subtitle_manager.py
    task_manager.py
    theme_catalog.py
    torrent_downloader.py
    update_manager.py
    persistence/
      _library_registration_batch.py
      _media_library_export.py
      _media_library_rows.py
      _media_library_stats.py
      library_sync.py
      media_library.py
    runners/
      base.py
      ffmpeg.py
      ytdlp.py
      aria2.py
      audio_mixer.py
      video_mixer.py
  ui/
    advanced_features.py
    converter_tab.py        # legacy-compatible implementation module
    design_tokens.py
    download_tab.py         # legacy-compatible alias to ui/tabs/download_tab.py
    history_settings_tab.py # shared legacy-compatible implementation module
    main_window.py
    queue_panel.py
    subtitle_tab.py         # legacy-compatible implementation module
    ui_components.py
    components/
      collapsible_panel.py
      command_palette.py
      error_panel.py
      playlist_item.py
      playlist_sort_dialog.py
      url_input.py
    tabs/                   # canonical desktop feature import surfaces
      _download_feedback.py
      _download_playlist.py
      converter_tab.py
      download_tab.py
      download_workspace.py
      filters_tab.py
      history_tab.py
      home_workspace.py
      library_tab.py
      library_workspace.py
      mixer_tab.py
      queue_tab.py
      settings_tab.py
      studio_workspace.py
      subtitle_tab.py
      torrent_tab.py
      utilities_tab.py
  translations/
    en.json
    tr.json
  utils/
    ffmpeg_checker.py
    file_utils.py
    metadata_handler.py
    system_utils.py

tests/
docs/
tools/
  phase5e_benchmarks.py
```

---

## 5. Entry Surfaces

## 5.1 Desktop entry

File: `ravn.py`

Startup order:

1. `setup_logging()`
2. `ensure_directories_exist()`
3. `migrate_all_legacy_files()`
4. `check_tool_dependencies()`
5. delayed import of `YouTubeDownloaderApp`

Why this matters:

- logging is initialized before most runtime actions
- config/data/cache directories exist before service startup
- old config/history files can migrate before normal persistence begins
- dependency-health warnings are emitted before feature surfaces load
- delayed UI import reduces noisy early-interrupt behavior

## 5.2 CLI entry

File: `ravn_app/cli.py`

Current CLI surface:

- `download`
- `convert`
- `info`
- `subtitle`
- `history`
- `torrent`
- `mixer`
- `library`
- `filters`
- `utilities`
- `serve` placeholder

CLI design rule:

- the CLI should map to the same product concepts used by the desktop app
- especially for acquisition, the CLI should prefer:
  - profiles
  - naming presets/templates
  - subtitle preferences
  - post-process controls
  - robustness controls
  - auth/tuning controls
- and avoid becoming a raw yt-dlp passthrough surface

---

## 6. Layer Model

## 6.1 Shell / orchestration layer

Primary file: `ravn_app/ui/main_window.py`

`YouTubeDownloaderApp` acts as a **thin application shell**.

Responsibilities:

- create shared services
- apply theme + i18n state
- compose the workspace shell
- wire shell-level quick actions
- expose queue drawer access
- expose settings workspace access
- route shell-level shortcuts
- manage tray integration and close-to-tray behavior
- pump task callbacks on the main thread
- refresh visible UI for theme/language changes

Shared services created here typically include:

- `DatabaseManager`
- `ConfigManager`
- i18n runtime
- `PlatformManager`
- `YouTubeDownloader`
- `TaskQueue`
- `MediaLibraryAutoAdder`

## 6.2 Workspace layer

The Phase 8 shell groups features by user intent.

Canonical desktop feature imports should come from `ravn_app.ui.tabs.*`.
Legacy `ravn_app.ui.*` feature modules remain only as compatibility surfaces or
shared implementation modules where broader file moves are not yet justified.

### Home workspace

File: `ravn_app/ui/tabs/home_workspace.py`

Responsibilities:

- landing/dashboard surface
- orientation for first-run / return usage
- recent activity / summary cards
- quick access into major flows

### Download workspace

Files:

- `ravn_app/ui/tabs/download_workspace.py`
- `ravn_app/ui/tabs/download_tab.py`
- `ravn_app/ui/tabs/torrent_tab.py`
- `ravn_app/ui/tabs/_download_feedback.py`
- `ravn_app/ui/tabs/_download_playlist.py`

Responsibilities:

- unified source-bar orchestration for URLs / playlists / batches / torrents
- auto-detected media-vs-torrent workspace routing with manual override support
- URL download flow
- playlist acquisition flow
- batch acquisition flow
- torrent manager flow
- shared media output-type switching (`Video` / `Audio`)
- compact profile selector
- UI feedback and progress handling
- playlist fetch / selection / filtering / summary logic

### Studio workspace

Files:

- `ravn_app/ui/tabs/converter_tab.py`
- `ravn_app/ui/tabs/subtitle_tab.py`
- `ravn_app/ui/tabs/filters_tab.py`
- `ravn_app/ui/tabs/mixer_tab.py`
- `ravn_app/ui/tabs/utilities_tab.py`
- `ravn_app/ui/tabs/studio_workspace.py`

Responsibilities:

- conversion workflows
- subtitle workflows
- filter workflows
- mixer workflows
- broad utility-helper workflows

### Library workspace

Files:

- `ravn_app/ui/tabs/library_tab.py`
- `ravn_app/ui/tabs/history_tab.py`
- `ravn_app/ui/tabs/library_workspace.py`

Responsibilities:

- local media library browsing and management
- history review
- search / export / collections-oriented flows

### Queue + settings surfaces

Files:

- `ravn_app/ui/queue_panel.py`
- `ravn_app/ui/tabs/queue_tab.py`
- `ravn_app/ui/tabs/settings_tab.py`

Responsibilities:

- global queue visibility
- queued/running/completed task display
- cancel/open-folder actions
- compact settings page with scroll-based organization

## 6.3 Core service layer

Core services contain product logic and orchestration.

### `downloader.py`

The acquisition orchestrator.

Responsibilities:

- map product-level acquisition intent to yt-dlp behavior
- resolve format/quality selections
- apply naming presets/templates
- apply auto-sort output routing
- apply subtitle-download preferences
- apply post-download automation pipeline
- attach normalized/enriched metadata for downstream consumers
- apply robustness controls
- apply collapsed advanced acquisition settings
- return final outputs suitable for history/library flows

Important supporting structures inside the acquisition stack:

- `download_profiles.py`
  - reusable acquisition presets
  - profile-to-settings override resolution
  - output-subdir resolution
- `download_naming.py`
  - naming presets
  - token expansion
  - sanitization
  - post-download rename behavior
- `download_metadata.py`
  - title/uploader normalization
  - source/platform detection
  - library-tag derivation
  - structured acquisition payload generation

### `converter.py`

Responsibilities:

- FFmpeg-backed conversion settings + orchestration
- codec/quality mapping
- shared conversion behavior used by UI and CLI

### `subtitle_manager.py`

Responsibilities:

- downloader-side subtitle argument construction
- subtitle embedding helpers
- subtitle-related post-processing support

### `torrent_downloader.py`

Responsibilities:

- aria2-backed torrent orchestration
- torrent mode routing (`FULL`, `SEQUENTIAL`, `STREAM`)
- stream URL handling
- payload discovery

### `media_helpers.py`

Responsibilities:

- FFmpeg-backed utility operations
- reusable helper functions for media workflows
- utility command implementation for desktop + CLI

### `database.py`

Responsibilities:

- config persistence
- history persistence
- schema migration support
- download/conversion/operation queries
- app statistics used by shell surfaces
- history/top-N index management for common downloads / conversions / operations reads

### `task_manager.py`

Responsibilities:

- async queue model
- task status/result handling
- callback scheduling/pumping support
- bounded retention for completed/failed/cancelled in-memory tasks
- stable task snapshots for low-cost UI dirty checks
- generic operation compatibility across multiple feature surfaces

## 6.4 Runner layer

The runner layer centralizes subprocess execution and parsing.
On Windows, the main runner/tool-health subprocess paths also apply no-console launch flags so packaged GUI usage does not spawn stray child terminals for normal tool invocations.

### `runners/base.py`

- base process-runner abstraction
- result normalization

### `runners/ffmpeg.py`

- FFmpeg / FFprobe execution
- real-time progress parsing via `-progress pipe:1`

### `runners/ytdlp.py`

- yt-dlp command construction
- retry behavior
- deterministic downloaded-file discovery
- archive-skip detection metadata

### `runners/aria2.py`

- aria2c process execution for torrent/magnet flows

### `runners/audio_mixer.py`

- audio mixing/concat helpers

### `runners/video_mixer.py`

- video composition/concat/filter-adjacent helpers

## 6.5 Persistence + library layer

### `persistence/media_library.py`

- local media library database
- add/search/tag/collection/export behavior
- bulk tag preloading for hot list/search/query paths
- cached aggregate statistics with explicit invalidation
- bounded search-history retention
- batched export iteration for large JSON/CSV exports
- delegates row-mapping / stats / export details to explicit private helper modules for clearer ownership

Supporting private helpers:

- `persistence/_media_library_rows.py`
- `persistence/_media_library_stats.py`
- `persistence/_media_library_export.py`

### `persistence/library_sync.py`

- auto-add / registration helpers for successful outputs
- library synchronization support across feature flows
- shared batch registration path that reuses one library session / metadata handler per batch
- delegates per-batch registration mechanics to `persistence/_library_registration_batch.py`

## 6.6 UI component layer

Reusable UI components live under `ravn_app/ui/components/`.

Examples:

- `error_panel.py`
- `playlist_sort_dialog.py`
- `playlist_item.py`
- `url_input.py`
- `collapsible_panel.py`
- `command_palette.py`

Shared styling helpers live in:

- `ravn_app/ui/ui_components.py`

Design tokens live in:

- `ravn_app/ui/design_tokens.py`

## 6.7 Infrastructure / support layer

### `config_paths.py`

- OS-aware config/data/cache paths
- default config generation
- schema validation
- legacy-file migration helpers

### `i18n.py`

- runtime translation lookup
- language switching
- app-wide translation interface

### `theme_catalog.py`

- strict canonical theme IDs
- legacy-name normalization to `dark` / `light`

### `logging_config.py`

- structured logging bootstrap

### `tool_health.py`

- shared external-tool health/status model
- startup dependency checks
- feature-to-tool impact mapping
- user-facing missing-tool summaries for desktop + CLI

### `error_handler.py`

- user-friendly external-tool error parsing

### `platform_support.py`

- platform helpers and environment-specific behavior

### `update_manager.py`

- app update helpers

### `plugin_system.py`

- experimental plugin/extension boundary scaffold
- not auto-loaded by the active desktop or CLI runtime
- retained as a future-facing extension surface, not a supported packaged-plugin system

---

## 7. Desktop Shell Composition

Current shell reality:

- primary workspaces:
  - `Home`
  - `Download`
  - `Studio`
  - `Library`
- global queue side panel
- lower-left theme toggle
- lower-left language toggle
- lower-left Settings workspace entry
- shell quick actions
- command palette (`Ctrl+K`)
- settings shortcut (`Ctrl+,`)

Shell-level shortcuts currently active:

- `Ctrl+Enter`
- `Escape`
- `Ctrl+L`
- `Ctrl+K`
- `Ctrl+,`

Adaptive shell behaviors:

- bounded content widths
- adaptive sidebar width
- adaptive queue drawer width
- shorter quick-action labels on tighter widths
- mounted workspace switching to reduce redraw flicker
- taskbar-aware, active-monitor-aware initial window centering on desktop launch
- in-place theme/language refresh behavior where possible
- dependency-health warning summary in `Home` plus detailed status in `Settings`
- compact-height download-workspace profile to reduce clipped/broken impressions on shorter desktop heights
- chunked rendering on selected list-heavy surfaces where Phase 5C measurement justified it
- task-snapshot-driven Home / Queue refreshes where practical instead of fixed high-frequency polling
- in-place Home summary-card updates instead of destroy/recreate refreshes
- unified download-source classification with contextual media / torrent panel switching

---

## 8. Configuration Model

Primary config/persistence path logic lives in `ravn_app/core/config_paths.py`.

### OS-aware directory model

- Windows:
  - config: `%APPDATA%/ravn/`
  - data: `%APPDATA%/ravn/data/`
  - cache: `%LOCALAPPDATA%/ravn/cache/`
- macOS:
  - config/data under `~/Library/Application Support/ravn/`
  - cache under `~/Library/Caches/ravn/`
- Linux:
  - config under `~/.config/ravn/`
  - data under `~/.local/share/ravn/`
  - cache under `~/.cache/ravn/`

### Important config domains

Flat/high-level keys include items such as:

- `default_download_path`
- `default_format`
- `default_quality`
- `theme`
- `language`
- `ffmpeg_path`
- subtitle defaults
- auto-sort / metadata toggles

Nested config sections include:

- `download_postprocess`
  - extract audio / convert / subtitle-embed automation
- `download_robustness`
  - archive / duplicate / partial / fallback / rate-limit settings
- `download_advanced`
  - cookie/auth handoff and fragment/network tuning
- `mixer`
- `library`
- `filters`

The download archive path is also managed centrally through `config_paths.py`.

---

## 9. Core Runtime Flows

## 9.1 URL acquisition flow

1. User starts a desktop or CLI download.
2. Product-level choices resolve into format/quality/profile settings.
3. `YouTubeDownloader` optionally prefetches source metadata when needed.
4. Naming, subtitle, robustness, and advanced settings are resolved.
5. `YtDlpRunner` executes the yt-dlp command.
6. Downloaded artifacts are discovered deterministically.
7. Post-download renaming runs.
8. Supporting subtitle/thumbnail artifacts are split from primary media outputs.
9. Optional post-download automation pipeline runs:
   - extract audio
   - convert
   - subtitle embed
10. Metadata enrichment attaches normalized/acquisition/library metadata.
11. Result returns to UI/CLI.
12. Success may persist history and may auto-register outputs into `MediaLibrary`.

## 9.2 Playlist acquisition flow

1. User fetches playlist metadata.
2. `YtDlpRunner.extract_playlist_entries()` collects playlist items.
3. Playlist UI builds selection rows and summary state.
4. User filters/sorts/selects/range-selects entries.
5. Selected entries are downloaded with the same shared acquisition settings stack.

## 9.3 Torrent flow

1. Source is detected as magnet / `.torrent`.
2. `TorrentDownloader` routes the request to aria2.
3. Mode semantics remain stable:
   - `FULL`
   - `SEQUENTIAL`
   - `STREAM`
4. Progress snapshots update UI rows and metrics.
5. Payload discovery surfaces child rows/files.
6. Success may expose a player-open action or discovered target file.

## 9.4 Studio processing flow

1. User starts convert/subtitle/filter/mixer/utility work.
2. Feature surface builds normalized settings.
3. Work is submitted through shared runner/core helpers.
4. Progress and completion flow through `TaskQueue` and main-thread callback pumping.
5. Results are persisted to history where supported.
6. Successful outputs may auto-register into `MediaLibrary`.

## 9.5 Library registration flow

1. A feature finishes with a successful media output.
2. Auto-add callback or sync helper prepares metadata.
3. `MediaLibrary` receives output path + tags + metadata.
4. Library views and related shell summaries refresh as needed.

## 9.6 CLI flow

1. Click parses arguments.
2. Command handlers normalize product-level settings.
3. Shared core modules/runners execute the work.
4. Optional DB/library persistence runs where supported.
5. Output is emitted in text or JSON.
6. For `download`, JSON output may include effective acquisition-profile summaries.

---

## 10. Acquisition Engine Detail

The acquisition engine is one of the most important architectural areas in the repo.

### Intent-driven acquisition features now implemented

- reusable acquisition profiles
- naming presets and template tokens
- playlist intelligence and partial selection
- subtitle automation
- post-download automation pipeline
- normalized metadata enrichment
- robustness controls
- collapsed advanced power-user settings
- CLI parity for the same concepts

### Why this matters architecturally

Instead of scattering yt-dlp flags through UI callbacks, RAVN now centralizes acquisition behavior in core orchestration:

- product-level UI/CLI inputs are translated into shared core settings
- the runner layer stays focused on process execution
- history/library integration sees normalized outputs/metadata
- desktop and CLI stay aligned around the same concepts

---

## 11. History, Queue, and Background Execution

### Queue model

`ravn_app/core/task_manager.py` provides the shared async task model.

Capabilities include:

- queued / running / completed states
- callback pumping
- cancellation hooks
- heterogeneous result support
- bounded terminal-task retention to prevent unbounded in-memory growth
- stable queue snapshots for shell/queue dirty checks

### History model

`ravn_app/core/database.py` persists:

- downloads
- conversions
- generic operations

History is surfaced in the desktop Library workspace and is also reachable via CLI.

Common history reads now have dedicated secondary SQLite indexes so downloads / conversions / operations top-N queries do not rely on repeated full scans and temp-sort plans for the covered paths.

---

## 12. i18n and Theme Constraints

### i18n

All user-facing UI strings should be translation-key based.

Current locale files:

- `ravn_app/translations/en.json`
- `ravn_app/translations/tr.json`

### Theme

Theme policy is intentionally strict:

- only canonical theme IDs: `dark`, `light`
- legacy aliases normalize back to those canonical IDs
- no uncontrolled theme proliferation

---

## 13. Validation Snapshot

Verified on 2026-04-05:

- full-suite baseline:
  - `pytest -q`
  - `644 passed, 1 skipped` (`645` collected)
- required UI logic sweep:
  - `pytest -q tests/test_ui_logic.py`
  - `90 passed`
- required UI components + builder sweep:
  - `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
  - `37 passed`
- required config/database sweep:
  - `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
  - `58 passed`
- targeted Phase 5E optimization sweep:
  - `pytest -q tests/test_media_library.py tests/test_library_sync.py tests/test_task_manager.py tests/test_database_manager.py tests/test_ui_logic.py`
  - `145 passed`
- Phase 5E benchmark harness:
  - `python tools/phase5e_benchmarks.py --output docs/phase5e_benchmark_results.json`
  - benchmark artifact refreshed successfully

Treat these as the current validated documentation snapshot.

---

## 14. Architectural Strengths

Current strengths of the codebase:

- strong shared-runner model for major external processes
- runtime media-path subprocess debt reduced through Phase 5B shared-runner convergence
- Windows GUI/runtime behavior is cleaner because runner/tool-health child process launches now suppress transient console windows on the main tool paths
- acquisition logic moved toward reusable core orchestration
- thin desktop shell with grouped workspaces
- canonical desktop feature imports are now clearer under `ravn_app.ui.tabs.*`
- queue/history/library integration across more workflows than before
- unified download-source UX now reduces tab-hopping between media and torrent entry paths
- MediaLibrary hot paths now avoid per-row tag query fan-out
- MediaLibrary now has clearer private helper boundaries for row loading, stats, and export behavior
- auto-add library batches reuse one session/metadata handler instead of recreating them per file
- playlist fetch now stages detail enrichment behind an initial flat pass so the first UI-visible step is cheaper
- OS-aware persistence paths
- strict i18n/theme policies
- explicit documentation that `plugin_system.py` is experimental-only rather than an implied runtime feature
- clear separation between feature UIs and lower-level media execution paths

---

## 15. Architectural Debt / Open Areas

Known or acknowledged open areas:

- Phase 5 release-readiness work is still incomplete
- direct `subprocess` usage now remains primarily in the runner layer, platform/open-file helpers, tool-health probing, and build/update helpers (see `docs/phase5b_subprocess_audit.md`)
- list-heavy surfaces now have targeted chunking/measurement, but broader virtualization is intentionally deferred until future measurement justifies it (see `docs/phase5c_ux_scalability.md`)
- packaging/build scripts/spec files now form a Windows-first release pipeline, with hyphenated release tags publishing as prereleases, but clean-machine packaged-app validation is still the final open release gate
- canonical desktop feature imports are now documented under `ui/tabs/`, but some legacy-compatible implementation modules remain in `ui/` to avoid risky churn before packaging (see `docs/phase5d_wrapper_boundary_clarity.md`)
- `plugin_system.py` is explicitly experimental-only and does not imply supported runtime plugin loading today (see `docs/phase5d_wrapper_boundary_clarity.md`)
- Phase 5E closeout evidence now spans `docs/phase5e_optimization_baseline.md`, `docs/phase5e_dead_code_audit.md`, and `docs/phase5e_benchmark_closeout.md`
- Phase 5F packaging implementation details and release procedure now live in `docs/phase5f_windows_packaging.md`

---

## 16. Source-of-Truth Relationship

When substantial implementation changes occur, the docs should stay aligned in this order:

1. `TASKS.md`
2. `PROGRESS.md`
3. `ARCHITECTURE.md`
4. `README.md`
5. `CLAUDE.md` / `AGENTS.md` guidance where applicable

This file should remain the main **system-structure document**: module map, runtime topology, layering, persistence, and flow-level design.
