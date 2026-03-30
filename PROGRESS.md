# PROGRESS

## Snapshot

Verified on 2026-03-30 (Phase 4D baseline + UI modularization follow-up).

## Confirmed

- Repository structure is complete and stable: app entrypoint, layered core, modular UI, tests, build scripts, and packaging spec are present.
- Main media execution paths are consolidated around `ravn_app/core/runners.py`.
- Queue/callback infrastructure is active in `ravn_app/core/task_manager.py`.
- Structured logging is centralized in `ravn_app/core/logging_config.py`.
- User-facing FFmpeg/yt-dlp error parsing exists in `ravn_app/core/error_handler.py`.
- OS-aware config path resolution and startup migration are active (`ravn_app/core/config_paths.py` + `ravn.py`).
- Download flow is wired end-to-end with background threads and UI-safe `after(...)` callbacks.
- Playlist metadata and selected-quality file size estimation are active.
- CLI is implemented in `ravn_app/cli.py` with `--json` support.
- Drag & drop is implemented for converter/subtitle tabs with fallback behavior.
- Real-time FFmpeg progress parsing via `-progress pipe:1` is implemented in `FFmpegRunner`.
- Queue panel visualizes queued/running/completed tasks and supports cancel/open-folder actions.
- Batch download mode supports multiline URLs (up to 50) and integrates with `TaskQueue`.
- Design system and accessibility improvements from Phase 4B/4C/4D are in place.

## UI Modularization (Latest)

- `ravn_app/ui/main_window.py` refactored into a thin orchestration shell.
- Download-specific logic moved to `ravn_app/ui/tabs/download_tab.py`.
- Reusable UI primitives extracted under `ravn_app/ui/components/`:
  - `error_panel.py`
  - `playlist_item.py`
  - `url_input.py`
- Compatibility wrapper added at `ravn_app/ui/download_tab.py`.
- `ravn_app/ui/tabs/` namespace now hosts tab modules/wrappers for cleaner structure.
- Fetch overlap guards and processing-feedback timer safety were added to avoid UI race conditions.

## Phase Completion

- **Phase 1** — Complete (main media path stabilization).
- **Phase 2** — Complete (config relocation, error messages, drag & drop, CLI).
- **Phase 3** — Complete (platform support expansion, DB migrations, tests, system tray).
- **Phase 4A** — Complete (core GUI completeness).
- **Phase 4B** — Complete (design system + interaction improvements).
- **Phase 4C.1–4C.7** — Complete (brand, iconography, transitions, feedback, polish, accessibility).
- **Phase 4D** — Complete (responsive layout, theme parity, settings consolidation, playlist UX, tooltips, tray behavior toggle).
- **Phase 5** — Open (build/packaging, distribution).
- **Phase 6** — Complete (torrent/magnet entegrasyonu, Aria2Runner, TorrentDownloader, streaming).

## Phase 6 — Torrent / Magnet Akış Entegrasyonu

- **6A** `Aria2Runner` — `ravn_app/core/runners/aria2.py` ✅
- **6B** `TorrentDownloader` — `ravn_app/core/torrent_downloader.py` ✅
- **6C** `parse_aria2c_error` — `ravn_app/core/error_handler.py` ✅
- **6D** URL Router + Drag-Drop — `download_tab.py` ✅
- **6E** Ayarlar (aria2c_path, seed_time, max_connections) ✅
- **6F** CLI `ravn torrent` komutu ✅
- **6G** Stream UI (torrent_mode_selector, Akışla İzle, Oynatıcıda Aç) ✅
- **6H** Dokümantasyon ✅

## Validation Status

- Last known full-suite baseline: `pytest -q` -> `417 passed, 1 skipped` (418 collected).
- Latest refactor-session validation:
  - `pytest -q tests/test_ui_logic.py` -> `27 passed`
  - `pytest -q tests/test_ui_components.py tests/test_app_builder.py` -> `37 passed`

## This Session (Quality Size Fix + ID3 + Auto-sort)

- **Fix:** Single video quality-based size estimate now works — `extract_video_info` calls new `YtDlpRunner.compute_size_by_quality` classmethod, returning `size_by_quality_mb` / `resolution_by_quality` / `format_note_by_quality` maps; size estimate label in download tab updates correctly on quality change.
- **Feature:** ID3 auto-tagging — `download()` accepts `embed_metadata` flag; when True and format is MP3/M4A, passes `--add-metadata --embed-thumbnail --convert-thumbnails jpg` to yt-dlp for full ID3 embedding (album art, artist, title, date).
- **Feature:** Auto-sort by channel — `download()` accepts `auto_sort` flag; when True, uses yt-dlp output template `%(uploader,channel,creator)s/%(title)s.%(ext)s` to group files into artist/channel subdirectories.
- UI: Both options available as checkboxes in download tab (persist to config on toggle) and as persistent settings in the "İndirme" settings sub-tab.

## Previous Session (Documentation Sync)

- Updated architecture and project docs to match the post-modularization UI skeleton.
- Removed stale statements about incomplete download-tab wiring.
- Aligned status language across `ARCHITECTURE.md`, `README.md`, `AGENT.md`, `CLAUDE.md`, and `TASKS.md`.
