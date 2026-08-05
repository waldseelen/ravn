# Release Status

Verified on 2026-08-05 (`858 passed, 1 skipped`, Windows — Python 3.13.14).

RAVN is an actively maintained **cross-platform desktop + CLI media product**, verified to run on Windows, Linux, and macOS via a CI test matrix (`.github/workflows/tests.yml`). The core experience is already in place: download, processing, organization, and automation workflows all run through the current shared runtime. Packaged/downloadable releases remain Windows-only for now; the main remaining release work there is final packaged-app validation and trust/signing polish.

> **Active work:** RAVN is currently undergoing a major GUI migration — replacing the existing CustomTkinter desktop UI with a modern **Tauri v2 + Vue 3** frontend. The Python core (downloader, converter, library, CLI) is the single source of truth and will not be rewritten. See the migration plan in `RAVN PROJECT TO DO.txt`.

---

## Tauri Migration — Phase Status (2026-08-05)

### Phase 1: Backend Isolation ✅ COMPLETE

**Goal:** Ensure the Python core (`ravn_app/core/`) is completely UI-agnostic.

- `animation_manager.py` relocated from `ravn_app/core/` → `ravn_app/ui/` — this module is a presentation concern (CustomTkinter animations) and does not belong in the shared core.
- `ravn_app/core/animation_manager.py` converted to a **backward-compatibility shim** that re-exports from the new location. Existing code continues to work unchanged during the incremental migration. Marked `TODO(tauri-migration)` for removal in Phase 5.
- All 4 direct `ravn_app.core.animation_manager` imports in `ravn_app/ui/` updated to the canonical `ravn_app.ui.animation_manager` path (`converter_tab.py`, `main_window.py`, `queue_panel.py`, `subtitle_tab.py`).
- `ravn_app/core/app_builder.py` — `customtkinter` removed from `check_requirements()` and `build_executable()` hidden imports. Marked with `NOTE(tauri-migration)` comments.
- `tests/test_animation_manager.py` — import path and all `@patch` targets updated to the canonical `ravn_app.ui.animation_manager` module.
- **Test result: 858 passed, 1 skipped (no regressions).**

### Phase 2: API Transport Layer ✅ COMPLETE

**Goal:** Create a lightweight FastAPI server that exposes the Python core to the Tauri frontend over HTTP and WebSocket. The backend must remain completely UI-agnostic — this layer only translates requests and serializes responses.

**New package: `ravn_app/api/`**

| File | Responsibility |
|---|---|
| `ravn_app/api/__init__.py` | Package declaration and architectural docstring |
| `ravn_app/api/deps.py` | FastAPI dependency providers (singleton service factories via `lru_cache`) |
| `ravn_app/api/main.py` | FastAPI application factory, uvicorn entry point, Tauri sidecar `serve()` |
| `ravn_app/api/ws.py` | `EventBus` singleton, `/ws/events` WebSocket endpoint, `make_task_callbacks()` bridge |
| `ravn_app/api/routers/downloads.py` | `POST /api/v1/downloads/info` and `POST /api/v1/downloads/start` |
| `ravn_app/api/routers/queue.py` | Full queue inspection and control (list/active/pending/completed/cancel/pause/resume/clear) |
| `ravn_app/api/routers/history.py` | Paginated download and conversion history with delete/clear |
| `ravn_app/api/routers/settings.py` | Settings read (`GET`), partial update (`PATCH`), reset to defaults (`POST /reset`) |

**Architecture decisions implemented:**
- **HTTP for commands/queries**, **WebSocket exclusively for event streaming** (progress, logs, ETA, queue state changes, notifications).
- `EventBus.broadcast()` pushes structured JSON events `{ "event": "...", "data": {...}, "ts": "..." }` to all connected clients.
- `make_task_callbacks()` bridges synchronous `TaskQueue` callbacks to the async FastAPI event loop via `asyncio.run_coroutine_threadsafe()`.
- Port `7842` by default; overridable via `RAVN_API_PORT` env var. Port announced on stdout (`RAVN_API_PORT=...`) so the Tauri process can discover it at runtime.
- `fastapi>=0.100.0` and `uvicorn[standard]>=0.23.0` added to `requirements.in`.

**Registered endpoints (confirmed via OpenAPI schema):**

```
POST     /api/v1/downloads/info
POST     /api/v1/downloads/start
GET      /api/v1/queue/
GET      /api/v1/queue/active
GET      /api/v1/queue/pending
GET      /api/v1/queue/completed
DELETE   /api/v1/queue/completed
GET      /api/v1/queue/{task_id}
POST     /api/v1/queue/{task_id}/cancel
POST     /api/v1/queue/pause
POST     /api/v1/queue/resume
GET      /api/v1/history/downloads
DELETE   /api/v1/history/downloads
GET      /api/v1/history/conversions
DELETE   /api/v1/history/downloads/{record_id}
GET      /api/v1/settings/
PATCH    /api/v1/settings/
POST     /api/v1/settings/reset
GET      /health
WS       /ws/events
```

- **Test result: 858 passed, 1 skipped (no regressions).**

### Phase 3: Tauri Shell + Vue 3 Frontend — NEXT

Scaffold the `frontend/` workspace with Tauri v2, Vue 3, TypeScript, Vite, Pinia, Vue Router, TanStack Table, and shadcn-vue or PrimeVue. Wire the Tauri sidecar to spawn the Python API on startup.

### Phase 4: Page Migration — PENDING

Rebuild UI screens (Dashboard, Queue, Library, Studio, Settings, Logs) in Vue, consuming the Phase 2 API.

### Phase 5: Tkinter Retirement — PENDING

Delete `ravn_app/ui/`, remove the `core/animation_manager.py` shim, strip `customtkinter`/`tkinterdnd2`/`pystray` from dependencies, update packaging pipeline.

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
