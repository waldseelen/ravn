# PROGRESS

## Snapshot

Verified on 2026-03-30.

## Confirmed

- Repository structure is stable: app entrypoint, layered core, modular UI, tests, build scripts, and packaging spec are present.
- Main media execution paths are consolidated around `ravn_app/core/runners/` (`FFmpegRunner`, `YtDlpRunner`, `Aria2Runner`).
- Queue/callback infrastructure is active in `ravn_app/core/task_manager.py`.
- Structured logging is centralized in `ravn_app/core/logging_config.py`.
- User-facing FFmpeg/yt-dlp/aria2 error parsing exists in `ravn_app/core/error_handler.py`.
- OS-aware config path resolution and startup migration are active (`ravn_app/core/config_paths.py` + `ravn.py`).
- Download flow is wired end-to-end with background threads and UI-safe `after(...)` callbacks.
- Playlist metadata and quality-based size estimation are active.
- CLI is implemented in `ravn_app/cli.py` with `--json` support and `torrent` command.
- Drag-and-drop uses `tkinterdnd2` when available and falls back safely.
- Real-time FFmpeg progress parsing via `-progress pipe:1` is active in runner layer.
- Queue panel visualizes queued/running/completed tasks and supports cancel/open-folder actions.
- Batch download mode supports multiline URLs (up to 50) and integrates with `TaskQueue`.
- Theme system is strict two-theme (`dark`, `light`) with legacy alias normalization.
- Settings UI is compact one-page scroll layout.
- Playlist fetch/sort dialog shows selected item count + selected total size and has high-contrast visibility fixes.

## Recent UX/Settings Consolidation

- `ravn_app/ui/main_window.py` refactored into a thin orchestration shell.
- Download-specific logic moved to `ravn_app/ui/tabs/download_tab.py`.
- Reusable UI primitives extracted under `ravn_app/ui/components/`:
  - `error_panel.py`
  - `playlist_item.py`
  - `url_input.py`
- Compatibility wrapper added at `ravn_app/ui/download_tab.py`.
- `ravn_app/ui/tabs/` namespace now hosts tab modules/wrappers for cleaner structure.
- Fetch overlap guards and processing-feedback timer safety were added to avoid UI race conditions.
- Settings screen remains compact and scrollable without nested settings sub-tabs.
- Playlist sort dialog action bar layout and table header contrast were improved for visibility.

## Phase Completion

- **Phase 1** — Complete (main media path stabilization).
- **Phase 2** — Complete (config relocation, error messages, drag & drop, CLI).
- **Phase 3** — Complete (platform support expansion, DB migrations, tests, system tray).
- **Phase 4A** — Complete (core GUI completeness).
- **Phase 4B** — Complete (design system + interaction improvements).
- **Phase 4C.1–4C.7** — Complete (brand, iconography, transitions, feedback, polish, accessibility).
- **Phase 4D** — Complete (responsive layout, theme parity, settings consolidation, playlist UX, tooltips, tray behavior toggle).
- **Phase 5** — Open (build/packaging, distribution).
- **Phase 6** — Complete (torrent/magnet integration, Aria2Runner, TorrentDownloader, streaming).

## Phase 6 — Torrent / Magnet Integration

- **6A** `Aria2Runner` — `ravn_app/core/runners/aria2.py` ✅
- **6B** `TorrentDownloader` — `ravn_app/core/torrent_downloader.py` ✅
- **6C** `parse_aria2c_error` — `ravn_app/core/error_handler.py` ✅
- **6D** URL Router + Drag-Drop — `download_tab.py` ✅
- **6E** Settings (aria2c_path, seed_time, max_connections) ✅
- **6F** CLI `ravn torrent` komutu ✅
- **6G** Stream UI (`torrent_mode_selector`, stream action, open player) ✅
- **6H** Documentation ✅

## Validation Status

- Last known full-suite baseline: `pytest -q` -> `417 passed, 1 skipped` (418 collected).
- Latest refactor-session validation:
  - `pytest -q tests/test_ui_logic.py` -> `27 passed`
  - `pytest -q tests/test_ui_components.py tests/test_app_builder.py` -> `37 passed`
  - Targeted regression bundle during refactor: `85 passed`

## Functional Highlights

- Single video quality-based size estimation is active; estimates update on quality change.
- ID3 metadata embedding options are supported for MP3/M4A workflows.
- Auto-sort by channel/uploader structure is supported in download output templates.
- Playlist selection/sorting supports clearer metrics and visibility-focused table styling.
- Torrent mode handling remains stable (`FULL`, `SEQUENTIAL`, `STREAM`).

## Documentation Sync

- Architecture and project docs were synchronized with current UI/core structure.
- Stale references to pre-refactor layout and legacy docs were removed.
- Canonical project guidance is now centered in `CLAUDE.md` (with `README.md`, `ARCHITECTURE.md`, and `TASKS.md` kept in sync).
