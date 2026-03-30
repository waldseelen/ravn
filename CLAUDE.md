# CLAUDE.md

## Mission

Work on RAVN as an in-progress desktop media application. Keep implementation and documentation aligned with the current repository state.

## Quick Context

- Entry point: `ravn.py` (calls setup_logging, ensure_directories_exist, migrate_all_legacy_files before app init)
- Main window shell: `ravn_app/ui/main_window.py`
- Download tab logic: `ravn_app/ui/tabs/download_tab.py`
- Reusable UI components: `ravn_app/ui/components/`
- UI Components: `ravn_app/ui/ui_components.py` (Toast, Tooltip, InlineError, EmptyState, LoadingSkeleton)
- Shared runners: `ravn_app/core/runners/` (paket olarak güncellendi)
- Task queue: `ravn_app/core/task_manager.py`
- Error parsing: `ravn_app/core/error_handler.py`
- Logging: `ravn_app/core/logging_config.py`
- Config paths (OS-aware): `ravn_app/core/config_paths.py`
- Download logic: `ravn_app/core/downloader.py`
- Conversion logic: `ravn_app/core/converter.py`
- Persistence: `ravn_app/core/database.py`
- Torrent runner: `ravn_app/core/runners/aria2.py` (Aria2Runner)
- Torrent downloader: `ravn_app/core/torrent_downloader.py` (TorrentDownloader, TorrentDownloadMode)
- Animation: `ravn_app/core/animation_manager.py`
- CLI: `ravn_app/cli.py`

## Current Reality

- Phase 1 (stabilization), Phase 2 (high-priority features), Phase 3 (medium-priority features), Phase 4A (core GUI completeness), Phase 4B (UI/UX enhancements), and Phase 4C (UI Polish & Micro-interactions) are complete.
- Download UI is fully wired in `ravn_app/ui/tabs/download_tab.py` with background threads + `after()` UI callbacks.
- `ravn_app/ui/main_window.py` is now a thin orchestrator that composes tabs and global window behavior.
- Reusable download widgets were extracted to `ravn_app/ui/components/` (`error_panel.py`, `playlist_item.py`, `url_input.py`).
- Config/history now live in OS-specific directories (Windows: `%APPDATA%\ravn\`, Linux: `~/.config/ravn/`).
- CLI available via `ravn download/convert/info/subtitle/history` with `--json` flag.
- Drag & drop works on converter and subtitle tabs (tkinterdnd2, fallback-safe).
- Real-time FFmpeg progress parsing via `-progress pipe:1` is active in `VideoConverter`.
- Queue panel widget shows live tasks (queued/running/completed) with cancel and open-folder buttons.
- Batch download mode supports up to 50 URLs via multi-line text input.
- Design system enhanced: Icons class replaces emojis, extended Colors with WCAG AA contrast, consistent 8px spacing grid.
- All UI tabs use semantic icons, proper visual feedback, and accessibility-compliant color contrast.
- Phase 4C.1–4C.7 complete: brand palette, icon placement, smooth transitions, loading feedback, toasts, validation, reduced-motion, tooltips.
- Phase 6A–6G complete: aria2c/magnet/torrent support, streaming, CLI `ravn torrent` command.
- Aria2Runner in `ravn_app/core/runners/aria2.py` handles magnet/torrent downloads with progress.
- TorrentDownloader wraps Aria2Runner; supports FULL, SEQUENTIAL, STREAM modes with local HTTP server.
- parse_aria2c_error() added to error_handler.py (errorCodes 1,2,3,6,9,13,24).
- Torrent settings (aria2c_path, seed_time, max_connections) in "İndirme" settings tab.
- download_tab.py auto-detects magnet/torrent URLs and routes to TorrentDownloader.
- .torrent drag-drop onto URL entry (tkinterdnd2, fallback-safe).
- Torrent mode selector (Tam İndir / Sıralı / Akışla İzle) appears on magnet/torrent URLs.
- Toast notifications provide success/warning/error feedback on download completion.
- Reduced-motion detection respects system preferences and `RAVN_REDUCED_MOTION` env var.
- URL validation on blur shows success/error indicator.
- Some auxiliary modules still use direct `subprocess` calls.
- Phase 1–4 complete in `TASKS.md`; Phase 5 (build/packaging) remains open.
- Settings tab consolidated from 4 to 3 sub-tabs; "Gelişmiş" merged into "İndirme".
- System tray close behavior is user-configurable via `close_to_tray` config key.
- Responsive layout: tabview max-width ~1200px with dynamic centering on window resize.
- Playlist panel has in-panel "Approve and Download" button; `expand=True` visibility bug fixed.
- File size estimate label shown next to URL input after video info fetch; updates correctly per quality (single-video info now includes `size_by_quality_mb` via `YtDlpRunner.compute_size_by_quality`).
- ID3 auto-tagging: `download(embed_metadata=True)` embeds album art + metadata for MP3/M4A.
- Auto-sort: `download(auto_sort=True)` organises files into `%(uploader,channel,creator)s/` subdirs.
- Both options are checkboxes in the download tab options row and persistent "İndirme" settings.
- All color tokens in `design_tokens.py` have `(light, dark)` tuple variants for full theme parity.
- Converter tab codec/quality/format selectors have educational Tooltip descriptions.
- Last known full-suite baseline (2026-03-30):
  - `417 passed, 1 skipped` (418 collected)
- Latest UI modularization checks:
  - `tests/test_ui_logic.py`: `27 passed`
  - `tests/test_ui_components.py` + `tests/test_app_builder.py`: `37 passed`

## Preferred Approach

1. Verify code before making status claims.
2. Prefer integration work over adding more surface area.
3. Use shared runners for new external process execution.
4. Keep docs synchronized when repository reality changes.
