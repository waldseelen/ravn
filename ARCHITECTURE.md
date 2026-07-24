# Architecture

## 1. What RAVN is

RAVN is a **cross-platform desktop + CLI media application** built around one shared core.

It combines four product areas:

1. **Download** — URLs, playlists, batches, magnets, and `.torrent` sources
2. **Processing** — conversion, subtitles, filters, mixer, and utility workflows
3. **Organization** — queue, history, and local media-library management
4. **Automation** — CLI access to the same core media flows

The design goal is straightforward:

- shared-core logic first
- runner-based external tool execution
- thin desktop shell orchestration
- focused feature modules
- OS-aware persistence paths
- translation-key-based UI strings

Current release work is centered on final Windows packaging validation and release polish, not on core product capability gaps.

---

## 2. Runtime surfaces

### Desktop

- Entry point: `ravn.py`
- Shell: `ravn_app/ui/main_window.py`
- UI toolkit: CustomTkinter

Startup order:

1. `setup_logging()`
2. `ensure_directories_exist()`
3. `migrate_all_legacy_files()`
4. `check_tool_dependencies()`
5. launch `YouTubeDownloaderApp`

### CLI

- Entry point: `ravn_app/cli.py`
- CLI toolkit: Click
- Console command: `ravn`

The CLI reuses shared services and shared runners instead of duplicating media logic.

---

## 3. Layer model

### 3.1 Shell and UI layer

Primary files:

- `ravn_app/ui/main_window.py`
- `ravn_app/ui/tabs/`
- `ravn_app/ui/components/`

Responsibilities:

- build the workspace shell
- wire shared services into UI surfaces
- host `Home`, `Download`, `Studio`, and `Library`
- expose queue and settings surfaces
- route shell shortcuts and command palette actions
- refresh visible UI for theme/language changes

Canonical desktop feature imports should come from `ravn_app.ui.tabs.*`.

### 3.2 Core service layer

Primary files:

- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/subtitle_manager.py`
- `ravn_app/core/torrent_downloader.py`
- `ravn_app/core/media_helpers.py`
- `ravn_app/core/database.py`
- `ravn_app/core/task_manager.py`

Responsibilities:

- map product-level user intent into executable media work
- keep desktop and CLI behavior aligned
- persist history/config state
- handle queueing, callbacks, and result shaping
- prepare outputs for library registration

### 3.3 Runner layer

Primary files:

- `ravn_app/core/runners/base.py`
- `ravn_app/core/runners/ffmpeg.py`
- `ravn_app/core/runners/ytdlp.py`
- `ravn_app/core/runners/aria2.py`
- `ravn_app/core/runners/audio_mixer.py`
- `ravn_app/core/runners/video_mixer.py`

Responsibilities:

- centralize external process execution
- normalize results and error handling
- support progress reporting and cancellation
- keep FFmpeg, yt-dlp, and aria2 behavior consistent across features

#### yt-dlp: two deliberate engines

`ytdlp.py` intentionally uses **two** yt-dlp engines for two different jobs:

- **Downloads and single-video info** go through the yt-dlp **binary** (subprocess). On the
  packaged Windows build this binary self-updates from GitHub (`YtDlpRunner.update()`), which
  keeps site compatibility fresh without shipping a new app release.
- **Playlist preview** uses the yt-dlp **Python library** (`extract_playlist_entries_progressive`)
  so it can stream results progressively — the shallow (fast) entry list arrives first (each row
  immediately gets a duration-based size estimate so nothing renders blank), then each video's real
  size/quality/resolution resolves on a bounded thread pool (`max_workers`, default 6) instead of
  one video at a time — since each resolve is a separate network round-trip, this is an I/O-bound
  workload that parallelizes well. Every worker thread owns its own `YoutubeDL` instance (a single
  instance is not safe to share across threads); resolved entries stream back and overwrite their
  row's estimate as soon as they land, in whatever order they finish.

The library is imported lazily (first preview only) so it never taxes startup, and if it is
unavailable the preview transparently falls back to the subprocess path. Preview numbers are
estimates, so any version skew between the two engines is low-stakes; downloads always use the
freshest (self-updating) binary.

### 3.4 Persistence and library layer

Primary files:

- `ravn_app/core/database.py`
- `ravn_app/core/persistence/media_library.py`
- `ravn_app/core/persistence/library_sync.py`
- `ravn_app/core/config_paths.py`

Responsibilities:

- config and history persistence
- media-library indexing, search, tags, collections, and export
- auto-registration of successful outputs
- OS-aware config/data/cache directories

### 3.5 Support systems

Primary files:

- `ravn_app/core/i18n.py`
- `ravn_app/core/theme_catalog.py`
- `ravn_app/core/tool_health.py`
- `ravn_app/core/logging_config.py`
- `ravn_app/core/error_handler.py`
- `ravn_app/utils/ffmpeg_checker.py`

Responsibilities:

- language switching and translation lookup
- strict `dark` / `light` theme normalization
- dependency health reporting
- logging bootstrap
- user-readable tool/process error shaping
- packaged/runtime FFmpeg discovery

### 3.6 Platform contract

RAVN runs on **Windows, Linux, and macOS**, verified by a CI test matrix across all three
(`.github/workflows/tests.yml`) on every push/PR:

- OS-specific calls are branched per-platform: `os.startfile` on Windows (`os.name == "nt"`),
  `open` on macOS (`sys.platform == "darwin"`), `xdg-open` elsewhere on Linux (argument-list
  `subprocess`, never a shell). The `yt-dlp` self-update path likewise selects the correct
  release asset and binary name per OS (`.exe` on Windows, `yt-dlp_macos` on macOS, extension-less
  `yt-dlp` on Linux) and marks the binary executable on POSIX.
- Windows-only integrations degrade gracefully when unavailable: the system tray (`pystray`)
  and drag-and-drop (`tkinterdnd2`) are optional imports gated behind availability flags, the
  registry PATH refresh (`winreg`) early-returns on non-Windows, and the winget-based tool
  installer (`core/tool_installer.py`) reports a clean "not available" result on non-Windows
  rather than crashing (a native package-manager backend for Linux/macOS is a tracked
  follow-up, see [TASKS.md](TASKS.md)).
- Paths resolve per-OS through `core/config_paths.py`; hidden-subprocess flags are Windows-gated
  in `core/runners/base.py`. **Packaging/signing is still the Windows distribution focus** —
  Linux/macOS packaged artifacts (AppImage/tar.gz, `.app`/`.dmg`) are not shipped yet.

---

## 4. Key desktop surfaces

### Home
- launch point for the app
- recent activity and summary cards
- quick actions and dependency health summary

### Download
- one smart source bar for URLs, playlists, batch links, magnets, and `.torrent` files
- video/audio output switching
- playlist selection and filtering
- torrent management with pause/resume and progress metrics

### Studio
- conversion
- subtitle workflows
- filters
- mixer
- utility helpers

### Library
- local media library browsing
- aggregated history
- search, tags, collections, statistics, and export

### Queue and settings
- queue visibility through a shared side panel
- compact settings surface
- theme/language utilities in the shell

---

## 5. Core runtime flows

### Download flow

1. A desktop or CLI request enters the acquisition layer.
2. Product-level settings resolve into format, quality, naming, subtitle, and post-process options.
3. `YtDlpRunner` executes the media acquisition step.
4. Output discovery, rename/post-process, and metadata enrichment run.
5. History and optional library registration are applied.

### Playlist flow

1. Playlist metadata is fetched.
2. The UI builds a selectable item list.
3. Users filter, sort, and select ranges.
4. Selected items run through the same shared download pipeline.

### Torrent flow

1. Magnet or `.torrent` input is detected.
2. `TorrentDownloader` routes execution through aria2.
3. Progress snapshots update UI rows and task state.
4. Resulting files can flow into history and library handling like other outputs.

### Studio flow

1. A feature tab or CLI command builds normalized settings.
2. Shared runner/core helpers execute the work.
3. `TaskQueue` and UI-safe callbacks handle progress/completion.
4. Supported outputs may be persisted and auto-added to the media library.

### CLI flow

1. Click parses the command.
2. Command handlers normalize product-level arguments.
3. Shared core services/runners execute the work.
4. Text or JSON output is emitted.

---

## 6. Repository map

```text
ravn.py
build.ps1
ravn.spec
ravn_app/
  cli.py
  core/
    runners/
    persistence/
  ui/
    components/
    tabs/
  translations/
  utils/
docs/
tests/
tools/
```

Useful starting points:

- desktop entry: `ravn.py`
- desktop shell: `ravn_app/ui/main_window.py`
- download logic: `ravn_app/core/downloader.py`
- queue: `ravn_app/core/task_manager.py`
- history/config DB: `ravn_app/core/database.py`
- CLI: `ravn_app/cli.py`

---

## 7. Operational notes

- **Windows-only packaging (for now):** the app itself runs cross-platform (§3.6), but packaged/downloadable releases are currently Windows-only; Linux/macOS packaging is a tracked follow-up.
- **Dependencies:** `ffmpeg`, `ffprobe`, and `yt-dlp` are core tools; `aria2c` is optional and enables torrent workflows.
- **i18n:** user-facing UI strings should remain translation-key based in `ravn_app/translations/en.json` and `ravn_app/translations/tr.json`.
- **Themes:** theme IDs normalize to `dark` or `light`.
- **Plugin surface:** `ravn_app/core/plugin_system.py` is experimental and is not part of the active packaged runtime.
- **Verification:** the latest validated quality snapshot lives in [PROGRESS.md](PROGRESS.md).

---

## 8. Related documents

- [README.md](README.md) — product overview and quick start
- [PROGRESS.md](PROGRESS.md) — release status and verification snapshot
- [TASKS.md](TASKS.md) — public roadmap
- [DEPENDENCIES.md](DEPENDENCIES.md) — required/optional tools and troubleshooting
- [docs/phase5f_windows_packaging.md](docs/phase5f_windows_packaging.md) — Windows packaging and release guide
