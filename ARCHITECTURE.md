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

### Desktop (Tauri v2 + Vue 3 Migration)

- Entry point: Tauri application shell / `src-tauri` & `ravn.py` (legacy CustomTkinter runtime)
- Frontend: Vue 3 + TypeScript + Vite (`frontend/src/`)
- Backend API Transport: FastAPI + Uvicorn (`ravn_app/api/`)
- State Management: Pinia stores (`useDownloadStore`, `useToastStore`, `useHistoryStore`)
- Design System: Nordic Brass theme CSS tokens (`frontend/src/style.css`)
- Real-time Events: WebSocket at `/ws/events`

Startup order:

1. `setup_logging()`
2. `ensure_directories_exist()`
3. `migrate_all_legacy_files()`
4. `check_tool_dependencies()`
5. Launch FastAPI backend service & Tauri / desktop shell

### CLI

- Entry point: `ravn_app/cli.py`
- CLI toolkit: Click
- Console command: `ravn`

The CLI reuses shared services and shared runners instead of duplicating media logic.

---

## 3. Layer model

### 3.1 Frontend & UI Layer (Vue 3 + Tauri)

Primary files:

- `frontend/src/App.vue`
- `frontend/src/components/HeaderNav.vue`
- `frontend/src/components/QueuePanel.vue`
- `frontend/src/components/CommandPalette.vue`
- `frontend/src/components/ToastManager.vue`
- `frontend/src/components/ErrorPanel.vue`
- `frontend/src/components/PlaylistSortDialog.vue`
- `frontend/src/components/Home.vue`
- `frontend/src/components/DownloadTab.vue`
- `frontend/src/components/StudioWorkspace.vue` (ConverterTab, SubtitleTab, FiltersTab, MixerTab, UtilitiesTab)
- `frontend/src/components/Library.vue` (Tabbed workspace: LibraryTab, HistoryTab)
- `frontend/src/components/LibraryTab.vue`
- `frontend/src/components/HistoryTab.vue`
- `frontend/src/components/Settings.vue`

Responsibilities:

- modular workspace composition (thin shell + focused feature tabs + reusable components)
- strict Nordic Brass design token enforcement (zero arbitrary hardcoded colors)
- zero `alert()` or mock stubs; real OS dialog integrations (`@tauri-apps/plugin-dialog`)
- WebSocket event subscription for real-time progress, speed, and status metrics
- dynamic Command Palette (`Ctrl+K`) and keyboard shortcuts

### 3.2 API Transport Layer (FastAPI)

Primary files:

- `ravn_app/api/main.py`
- `ravn_app/api/routers/downloads.py`
- `ravn_app/api/routers/history.py`
- `ravn_app/api/routers/library.py`
- `ravn_app/api/routers/queue.py`
- `ravn_app/api/routers/settings.py`
- `ravn_app/api/routers/studio.py`
- `ravn_app/api/ws.py`

Responsibilities:

- lightweight async HTTP endpoints for commands and queries
- unified task queue dispatching to core service runners
- WebSocket event broadcaster (`/ws/events`) for background task updates
- dependency injection for database, downloader, library, and task manager instances

### 3.3 Core service layer

Primary files:

- `ravn_app/core/downloader.py`
- `ravn_app/core/converter.py`
- `ravn_app/core/subtitle_manager.py`
- `ravn_app/core/torrent_downloader.py`
- `ravn_app/core/media_helpers.py`
- `ravn_app/core/database.py`
- `ravn_app/core/persistence/media_library.py`
- `ravn_app/core/task_manager.py`

Responsibilities:

- map product-level user intent into executable media work
- keep desktop and CLI behavior aligned
- persist history/config state
- handle queueing, callbacks, and result shaping
- prepare outputs for library registration

### 3.4 Runner layer

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

### 3.5 Persistence and library layer

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

### 3.6 Support systems

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

### 3.7 Platform contract

RAVN runs on **Windows, Linux, and macOS**, verified by a CI test matrix across all three
(`.github/workflows/tests.yml`) on every push/PR:

- OS-specific calls are branched per-platform: `os.startfile` on Windows (`os.name == "nt"`),
  `open` on macOS (`sys.platform == "darwin"`), `xdg-open` elsewhere on Linux (argument-list
  `subprocess`, never a shell). The `yt-dlp` self-update path likewise selects the correct
  release asset and binary name per OS (`.exe` on Windows, `yt-dlp_macos` on macOS, extension-less
  `yt-dlp` on Linux) and marks the binary executable on POSIX.
- Windows-only integrations degrade gracefully when unavailable: the system tray (`pystray`)
  and drag-and-drop (`tkinterdnd2`) are optional imports gated behind availability flags, and
  the registry PATH refresh (`winreg`) early-returns on non-Windows.
- Paths resolve per-OS through `core/config_paths.py`; hidden-subprocess flags are Windows-gated
  in `core/runners/base.py`.
- **Packaging:** Windows produces the signed release (`build.ps1` → `windows-release.yml`).
  Linux packaging exists as a `workflow_dispatch`-only job (`linux-package.yml`, PyInstaller
  onedir + `tar.gz`) that is deliberately **not** wired into the tagged release until it has
  been run green on a real runner. macOS packaging is a tracked follow-up ([TASKS.md](TASKS.md)).

#### External tool resolution

The four external binaries (`ffmpeg`, `ffprobe`, `yt-dlp`, `aria2c`) resolve through
`utils/bundled_tools.py`, which searches `assets/<tool>/<platform>/` across the PyInstaller
extraction dir (`sys._MEIPASS`), the executable's own directory, and the project root —
falling back to `PATH` only when nothing is bundled.

**Bundling is the primary path, not an optimization.** A packaged release ships its tools, so
a freshly unzipped build reports every tool as available with no install step and no first-run
network fetch. Two consequences follow:

- `core/tool_health.py` checks the bundled tree *before* `PATH`, otherwise Settings would report
  bundled tools as missing (it previously consulted `shutil.which` alone).
- Startup calls `configure_bundled_tools_path()` so the bundled directories also land on `PATH`
  for **child** processes — yt-dlp shells out to ffmpeg for muxing and only sees `PATH`.

`yt-dlp` additionally self-updates into the per-user data directory; that copy outranks the
bundled one, since shipping a binary is what makes a fresh install work offline, not a ceiling.
Resolution order: explicit configured path → self-updated binary → bundled copy → `PATH`.

Installing missing tools (`core/tool_installer.py`) is the **fallback**. On Windows it drives
winget directly and refreshes the process PATH so new binaries are visible without a restart.
On Linux it detects `apt`/`dnf`/`pacman` and returns the exact command for the user to run —
it deliberately does not shell out to `sudo`, because a GUI app has no TTY to prompt on and the
call would hang. macOS (`brew`) is a tracked follow-up.

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

- **Packaging:** Windows is the signed, released artifact; Linux packaging is `workflow_dispatch`-only pending real-runner verification; macOS is a tracked follow-up (§3.7).
- **Dependencies:** `ffmpeg`, `ffprobe`, and `yt-dlp` are core tools; `aria2c` is optional and enables torrent workflows. Packaged builds bundle them under `assets/<tool>/<platform>/` and resolve them via `utils/bundled_tools.py` before falling back to `PATH` (§3.7).
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
