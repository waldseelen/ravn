# Release Status

Verified on 2026-08-30 (`876 passed, 1 skipped`, Windows 11 — Python 3.14 / 3.13).

RAVN is an actively maintained **cross-platform desktop + CLI media product**, verified to run on Windows, Linux, and macOS via a CI test matrix (`.github/workflows/tests.yml`). The core experience is already in place: download, processing, organization, and automation workflows all run through the current shared runtime. Packaged/downloadable releases remain Windows-only for now; the main remaining release work there is final packaged-app validation and trust/signing polish.

> **Active work:** RAVN is currently undergoing a major GUI migration — replacing the existing CustomTkinter desktop UI with a modern **Tauri v2 + Vue 3** frontend. The Python core (downloader, converter, library, CLI) is the single source of truth and will not be rewritten. See the migration plan in `TASKS.md` and `CLAUDE.md`.

---

## Tauri Migration — Phase Status (2026-08-30)

### Phase 0: Cleanup & Design System Tokens ✅ COMPLETE
- Extended `frontend/src/style.css` with full CustomTkinter Nordic Brass tokens (`--bg-*`, `--text-*`, `--accent-*`, `--border-*`, `--status-*`, `--*-bg`, light theme `:root[data-theme="light"]`).
- Converted all legacy prototype and wrong-palette components to canonical Nordic Brass tokens: `ConverterTab.vue`, `SubtitleTab.vue`, `FiltersTab.vue`, `MixerTab.vue`, `UtilitiesTab.vue`, `QueuePanel.vue`.
- Removed dead prototype `Dashboard.vue`.
- Zero forbidden color utility classes (`slate`, `purple`, `rose`, `cyan`, `teal`, `indigo`, `amber`) across all frontend files.
- Removed all `alert()` and mock `setTimeout` stubs.

### Phase 1: App Shell Architecture ✅ COMPLETE
- Rebuilt top header navigation with Brand Logo, `◐` Dark/Light theme toggle, `TR`/`EN` language switcher, and `🔍 Ctrl+K` command palette trigger.
- Added Quick Action Bar (`Paste URL`, `Add Torrent`, `Convert File`, `Open Library`).
- Implemented 380px right-side slide-out Task Queue Drawer with live counters, badges, progress bar, cancel, and clear completed actions.
- Created `frontend/src/components/CommandPalette.vue` with keyboard navigation (`↑`/`↓`/`↵`/`ESC`), fuzzy live search, and categorized action items.
- Built global `ToastManager.vue` and `useToastStore` (`success`, `warning`, `error`, `info`).
- Built expandable `ErrorPanel.vue` with technical details accordion and retry callback.
- Registered global hotkeys (`Ctrl+K`, `Escape`, `Ctrl+,` / `Ctrl+P`).

### Phase 2: Home Workspace Matching ✅ COMPLETE
- Integrated `ToolHealthChecker` banner (`GET /api/v1/health` & `GET /health`): displays degraded/critical warnings, lists missing tools and affected features, and includes "Fix in Settings" action. Banner hides automatically when tools are healthy.
- Replaced 2 static links with 6 interactive Quick Action cards (`Paste URL & Download`, `Playlist Downloader`, `Torrent / Magnet`, `Convert Format`, `Apply Filters & EQ`, `Media Library`).
- Built 4 live summary overview cards (`Downloads`, `Conversions`, `Operations`, `Task Queue`) wired directly to `GET /api/v1/history/stats` and Pinia download store.
- Added Recent Activity list powered by `GET /api/v1/history/recent` displaying the last 6 operations with formatted timestamps and status badges.
- Added backend endpoints: `GET /api/v1/health`, `GET /api/v1/history/stats`, `GET /api/v1/history/recent`, `GET /api/v1/history/operations`.
- Test suite updated: **867 passed, 1 skipped**.

### Phase 3: Download Workspace Matching ✅ COMPLETE
- Built Source Classifier Card with live URL/Magnet/Torrent auto-detection, platform badges, and drag-and-drop (`@dragover`, `@drop`, visual glow).
- Integrated `Video` / `Audio` segmented media mode switcher.
- Added Platform Profile selector (YouTube, Twitter, Instagram, TikTok, Vimeo, Twitch, SoundCloud) and preset configurations (Music, Podcast, Archive, Social Clip) with auto-fill.
- Added live URL validation (`✓` / `⚠`) and dynamic size estimator (`~MB`).
- Implemented 2-Column layout: Video acquisition column (Quality, Format, Subtitles) & Audio extraction column (Format, Bitrate, ID3/Cover tags).
- Created `PlaylistSortDialog.vue` (P3-T7) with 7-column sortable table, Title/Duration/Popularity filtering, select-all/invert controls, and batch download confirmation.
- Full Torrent & Magnet acquisition workflow (P3-T9) with FULL/SEQUENTIAL/STREAM modes and aria2c health status.
- Batch URL processing panel (P3-T10) for multi-line link queuing.
- Integrated `ErrorPanel.vue` (P3-T11) with retry handling.
- Added backend endpoints: `POST /api/v1/downloads/playlist/info`, `POST /api/v1/downloads/batch/start`, `POST /api/v1/downloads/torrent/start`.
- Test suite updated: **869 passed, 1 skipped**.

### Phase 4: Studio Workspace Matching ✅ COMPLETE
- Built 5-Card Launcher Grid (`StudioWorkspace.vue`) with subtab switcher and `‹ Back to Launcher` button.
- Rebuilt `ConverterTab.vue` matching CustomTkinter: DND input, video codecs (h264/hevc/vp9/av1/copy), audio codecs (aac/mp3/opus/flac/copy), CRF qualities (Lossless to Very Low), speed presets (ultrafast to veryslow), HW Accel (NVENC/QSV/AMF), bitrate, real file dialogs, progress bar, live log console, and `ErrorPanel`.
- Rebuilt `SubtitleTab.vue`: Dual-panel layout (Left: Video URL downloader with tr/en/de/fr/es + auto-subs; Right: format converter SRT/VTT/ASS/SSA, ±10s precision time shifter, Soft Mux / Hard Burn-in embedding, console log, and `ErrorPanel`). Zero `alert()` calls.
- Rebuilt `FiltersTab.vue`: Brightness, Contrast, Saturation, Blur, Sharpen, Rotate (0/90/180/270), 6 Effect toggles (Flip H/V, Grayscale, Sepia, Invert, Deinterlace), 5-level Denoise, 3D LUT loader, dynamic filter parameter summary, progress bar, and `ErrorPanel`.
- Rebuilt `MixerTab.vue`: Audio / Video mode switcher, 6 audio operations (`concat`, `mix`, `crossfade`, `normalize`, `trim`, `fade`), 7 video operations (`concat`, `overlay`, `pip`, `side-by-side`, `watermark`, `transition`, `replace-audio`), multi-input DND list, dynamic parameter panel, and `ErrorPanel`.
- Rebuilt `UtilitiesTab.vue`: 4-section Accordion panel with 23 operational helpers (6 Quick, 6 Audio, 8 Video, 3 Smart), asynchronous loading states, and live output log.
- Added backend studio router (`ravn_app/api/routers/studio.py`) with 6 FastAPI endpoints (`/convert/start`, `/subtitle/download`, `/subtitle/process`, `/filters/apply`, `/mixer/run`, `/utilities/run`).
- Zero forbidden Tailwind color classes, zero `alert()` calls, full Nordic Brass design tokens.
- Frontend build: `vue-tsc --noEmit && vite build` -> **0 errors**.
- Test suite updated: **874 passed, 1 skipped** (16 API tests passing).

### Phase 5: Library Workspace Matching ✅ COMPLETE
- Rebuilt `Library.vue` into a unified tabbed workspace matching `LibraryWorkspace` in CustomTkinter (`Media Library` | `History` segmented tabs) with collapsible quick usage guide.
- Implemented `frontend/src/components/LibraryTab.vue`:
  - DND File Import Card with `@tauri-apps/plugin-dialog` file picker, Title & Tag inputs, Add to Library action.
  - Search & Filter bar: Query, comma-separated tags, format combobox (`All`, `mp4`, `mp3`, `mkv`, `webm`, `wav`, `flac`, `aac`, `mov`), Search & Reset triggers.
  - Export actions: JSON and CSV catalog export.
  - Results card: item thumbnail/format badge, Title, Duration, Size, Resolution/Sample Rate, Tags, File Path, `Open File`, `Open Folder`, `Add to Collection`, and `Delete` actions.
  - Sidebar: Live Stats card (Items, Total size, Collections count, Duplicates count), Collections manager (New collection creator, target collection selector, collection items filter & delete), Recent Searches clickable history.
  - `ErrorPanel.vue` integration.
- Implemented `frontend/src/components/HistoryTab.vue`:
  - Header actions: Detailed statistics dialog modal, Clear history confirmation dialog modal, Refresh.
  - Live search input & dual filtering (Format: `All`/`MP4`/`MP3`/`MKV`/`AVI`; Status: `All`/`completed`/`failed`/`cancelled`).
  - Scrollable history cards: Format, Quality, Size, Date, colored status badge (`completed`=green, `failed`=red, `cancelled`=amber), `Open File`, and individual delete actions.
  - `ErrorPanel.vue` integration.
- Added FastAPI Library router (`ravn_app/api/routers/library.py`):
  - `GET /api/v1/library/` (search & filter)
  - `POST /api/v1/library/add` (import media)
  - `DELETE /api/v1/library/{media_id}`
  - `GET /api/v1/library/stats`
  - `POST /api/v1/library/export` (JSON / CSV export)
  - `GET /api/v1/library/collections` & `POST /api/v1/library/collections` & `DELETE /api/v1/library/collections/{id}`
  - `GET /api/v1/library/collections/{id}/items` & `POST /api/v1/library/collections/{id}/items`
  - `GET /api/v1/library/recent-searches`
  - `POST /api/v1/library/open-file` & `POST /api/v1/library/open-folder`
- Zero `alert()` calls, zero forbidden color classes, full Nordic Brass design tokens.
- Frontend build: `vue-tsc --noEmit && vite build` -> **0 errors**.
- Full test suite: **875 passed, 1 skipped** (17 API tests passing).

### Phase 6: Settings Workspace Matching ✅ COMPLETE
- Rebuilt `frontend/src/components/Settings.vue` matching the full CustomTkinter `SettingsTab`:
  - **Tool Health Diagnostics**: Live dependency checker card (`GET /api/v1/health`) for `ffmpeg`, `ffprobe`, `yt-dlp`, and `aria2c` with real versions, paths, operational status, and affected features; background `Install Missing Tools` auto-installer.
  - **General Settings**: Theme switcher (`Nordic Dark` / `Nordic Light` live `data-theme` updates), Language dropdown (`TR`/`EN`), Close Behavior (`Close to System Tray` vs `Close Application Fully`), and notification/update/crash toggles.
  - **Update Manager**: GitHub Releases integration (`GET /api/v1/settings/updates/check`) with live status badge and manual update check.
  - **Download & Storage**: Output directory picker (Tauri `dialog.open`), Default format (MP4/MP3/MKV), Default quality (Best/1080p/720p/480p), Concurrent downloads slider (1-5), and History limit.
  - **Subtitle Preferences**: Preferred language, Fallback language, Auto-generated inclusion, Auto-download, and Auto-embed toggles.
  - **Metadata & Naming**: Embed metadata/ID3, Auto-sort by channel, Naming presets (`Standard`, `Clean`, `Playlist`), and custom filename template.
  - **Post-Process & Reliability**: Extract audio (format/bitrate), Convert video, Archive download registry, Duplicate detection, Resume partial, Fallback format, and Rate limit (KB/s).
  - **Advanced Network & Cookies (Collapsible)**: Cookies mode (`None`, `Browser`, `File`), browser profiles, cookie file picker, concurrent fragments, fragment retries, and socket timeouts.
  - **Engine & Torrent**: aria2c path, seed time, max connections, ffmpeg path, and auto-cleanup.
  - **Actions & Persistence**: Save settings (`PATCH /api/v1/settings/`), Reset to defaults modal (`POST /api/v1/settings/reset`), JSON Export (`POST /api/v1/settings/export`), and JSON Import (`POST /api/v1/settings/import`).
- Extended FastAPI Settings router (`ravn_app/api/routers/settings.py`):
  - `GET /api/v1/settings/updates/check` (GitHub release check via UpdateManager)
  - `POST /api/v1/settings/tools/install` (Winget / package manager auto-installer)
  - `POST /api/v1/settings/export` (JSON config file exporter)
  - `POST /api/v1/settings/import` (JSON config file / payload importer)
- Zero `alert()` calls, zero forbidden color classes, full Nordic Brass design tokens.
- Frontend build: `vue-tsc --noEmit && vite build` -> **0 errors** (1.80s).
- Full test suite: **876 passed, 1 skipped** (18 API tests passing).


### Phase 7: Queue Panel Workspace Matching — NEXT
- QueueItemWidget redraw with status color indicator line.
- Progress bar, speed/ETA/size metrics, active item actions.
- Animated state icons (running spinner, success check, failed cross).


---

## Recent quality pass (2026-07)

- Playlist fetch reworked to progressive yt-dlp **library** extraction and now carries real **cover
  thumbnails** into the preview. Detail resolution (size/quality/resolution per video) runs on a
  bounded thread pool instead of one video at a time, and every row gets an instant duration-based
  size estimate the moment the shallow list arrives, so nothing renders blank while real values
  stream in.
- CI hardened: broken workflow files removed, `ruff` gate (blocking, clean), `mypy` core gate
  (informational), Python 3.13 in the matrix, coverage floor, and a pip-compiled dependency lock.
- Real fixes: a command-injection in `open_file` (now argument-list `subprocess`), 182 lines of dead code
  carrying a latent `NameError`, a lowercase-`any` annotation bug, and swallowed queue-worker failures.
- See [ROADMAP.md](ROADMAP.md) for the ongoing 20-category quality push.

---

## Product snapshot

### Download and acquisition
- Single URL, playlist, batch, magnet, and `.torrent` flows are available.
- Playlist review supports filtering, selection, and range-based download.
- Download profiles, naming presets/templates, subtitle preferences, metadata enrichment, and post-download automation are active.
- Tool-health checks explain which features are affected when dependencies are missing.

### Processing and studio tools
- Conversion, subtitle embed, filters, mixer, and utility workflows are available in the desktop app.
- The CLI exposes matching media-processing surfaces for scripting.
- FFmpeg real-time progress parsing is active.
- Inline error presentation is in place for the most failure-prone studio surfaces.

### Library, history, and queue
- Queue infrastructure is active through `ravn_app/core/task_manager.py`.
- History persists downloads, conversions, and other media operations.
- The local media library supports search, tags, collections, statistics, and export.
- Successful supported outputs can auto-register into the media library.

### Desktop and CLI runtime
- Desktop workspaces are grouped into `Home`, `Download`, `Studio`, and `Library`.
- Queue is exposed as a shared panel instead of a top-level workspace.
- Settings, theme, and language controls are integrated directly into the shell.
- The CLI supports `download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, and `utilities`.

### Platform and packaging
- RAVN runs on Windows, Linux, and macOS — CI runs the full test suite on all three on every push/PR.
- Windows packaged builds are the only pre-built distribution target today.
- Packaged Windows builds support bundled FFmpeg/FFprobe lookup.
- GitHub Actions packaging and tagged-release workflows are in place (Windows-only).
- Linux and macOS packaged artifacts (AppImage/tar.gz, `.app`/`.dmg`) are not shipped yet — tracked as a follow-up in [TASKS.md](TASKS.md).

---

## Quality snapshot

Latest automated verification run:

- `pytest -q`
- `858 passed, 1 skipped`

Observed on 2026-08-05 (Windows, Python 3.13.14).

---

## Current release focus

- **Tauri migration (active):** Phase 1 and Phase 2 complete; Phase 3 (Tauri shell scaffold) is next.
- Validate packaged behavior on a clean Windows machine / VM.
- Tighten signing and release-trust guidance for Windows distribution.
- Keep docs, screenshots, and onboarding material aligned with repository reality.

---

## Explicit scope notes

- `ffmpeg`, `ffprobe`, and `yt-dlp` are core dependencies.
- `aria2c` is optional and only required for torrent and magnet workflows.
- `plugin_system.py` is experimental and is not part of the active packaged runtime.
- `ravn_app/api/` is the new FastAPI transport layer for the Tauri frontend; it is not yet wired into the packaged build.
- `customtkinter`, `tkinterdnd2`, and `pystray` are legacy Tkinter UI dependencies — they will be removed in Phase 5 of the Tauri migration.

---

## Documentation map

- [README.md](README.md) — product overview and quick start
- [TASKS.md](TASKS.md) — public roadmap and near-term priorities
- [ARCHITECTURE.md](ARCHITECTURE.md) — system structure and runtime boundaries
- [DEPENDENCIES.md](DEPENDENCIES.md) — setup and troubleshooting
- [docs/phase5f_windows_packaging.md](docs/phase5f_windows_packaging.md) — Windows packaging and release guide
