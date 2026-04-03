# PROGRESS

## Snapshot

Verified on 2026-04-03.

## Confirmed

- Repository structure is stable: app entrypoint, layered core, modular UI, tests, build scripts, and packaging spec are present.
- Main media execution paths are consolidated around `ravn_app/core/runners/` (`FFmpegRunner`, `YtDlpRunner`, `Aria2Runner`).
- Phase 7 core helpers are now present: `AudioMixerRunner`, `VideoMixerRunner`, `MediaLibrary`, and `MetadataHandler`.
- Queue/callback infrastructure is active in `ravn_app/core/task_manager.py`, including callback pumping from `main_window.py` and running-task cancellation hooks.
- Structured logging is centralized in `ravn_app/core/logging_config.py`.
- User-facing FFmpeg/yt-dlp/aria2 error parsing exists in `ravn_app/core/error_handler.py`.
- OS-aware config path resolution and startup migration are active (`ravn_app/core/config_paths.py` + `ravn.py`).
- Download flow is wired end-to-end with background threads and UI-safe `after(...)` callbacks.
- Playlist metadata and quality-based size estimation are active.
- Playlist dialog now supports title/duration filtering, popularity-aware filtering when metadata is available, visible-row bulk actions, and range-based selection before download.
- Downloader subtitle automation is now active through settings-backed preferred/fallback language resolution, optional auto-generated caption fallback, and optional auto-embed behavior for supported video downloads.
- Downloader naming presets/templates are now active through settings-backed config, safe token expansion, and post-download renaming (`standard`, `clean`, `playlist` + custom token templates).
- CLI is implemented in `ravn_app/cli.py` with `--json` support and commands for `torrent`, `mixer`, `library`, and `filters`.
- Drag-and-drop uses `tkinterdnd2` when available and falls back safely.
- Real-time FFmpeg progress parsing via `-progress pipe:1` is active in runner layer.
- Queue panel visualizes queued/running/completed tasks and supports cancel/open-folder actions.
- Batch download mode supports multiline URLs (up to 50) and integrates with `TaskQueue`.
- Theme system is strict two-theme (`dark`, `light`) with legacy alias normalization.
- Settings UI is compact one-page scroll layout.
- Playlist fetch/sort dialog shows selected item count + selected total size and has high-contrast visibility fixes.
- Config defaults now include nested `mixer`, `library`, and `filters` sections, and an OS-aware `media_library.db` path helper exists.

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
- Download settings now expose naming presets and an optional custom filename template field without expanding the default Download workspace surface.
- Subtitle settings now expose fallback-language, auto-generated-caption, and auto-embed controls; `SubtitleTab` also picks up the configured subtitle language defaults.
- Playlist sort dialog action bar layout and table header contrast were improved for visibility.
- Playlist sort dialog now exposes partial-download controls for title/duration/popularity filtering and range selection without adding a second playlist screen.
- `download_tab.py` refactored to use a progressive disclosure linear flow, removing static dual columns.
- `converter_tab.py` refactored to use a progressive disclosure linear flow with collapsible advanced settings.
- `subtitle_tab.py` refactored to use a progressive disclosure segmented button layout, removing static dual columns.
- `history_settings_tab.py` layouts bounded to max widths to prevent horizontal stretching.
- New Phase 7 tab modules added under `ravn_app/ui/tabs/`: `mixer_tab.py`, `filters_tab.py`, and `library_tab.py`.

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
- **Phase 7 (core / CLI + UI + queue/history + utilities)** — Complete (`AudioMixerRunner`, `VideoMixerRunner`, `MediaLibrary`, `MetadataHandler`, CLI integration, dedicated Mixer / Filters / Library tabs, queue/history persistence, and comprehensive utility media helpers are complete).

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

- Current full-suite baseline (2026-04-03): `pytest -q` -> `557 passed, 1 skipped` (subtitle automation follow-up verification).
- Subtitle/download regression sweep (2026-04-03): `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py` -> `115 passed, 1 skipped`.
- Playlist/download regression sweep (2026-04-03): `pytest -q tests/test_ui_logic.py tests/test_runners.py` -> `147 passed`.
- Download/settings regression sweep (2026-04-03): `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_database_manager.py` -> `137 passed, 1 skipped`.
- Phase 7 targeted regression sweep (2026-04-03): Utilities desktop wiring, translation coverage, and UI token validation were rechecked; targeted UI/i18n/design-token sweep passes alongside the full suite.

## Functional Highlights

- Single video quality-based size estimation is active; estimates update on quality change.
- ID3 metadata embedding options are supported for MP3/M4A workflows.
- Auto-sort by channel/uploader structure is supported in download output templates.
- Download output naming now supports preset-driven or custom token-driven post-download renaming with safe sanitization and nested playlist-style folder layouts.
- Playlist selection/sorting supports clearer metrics, title/duration/popularity filtering, range-based partial selection, and visibility-focused table styling.
- Download acquisition can now request the preferred subtitle language first, fall back to a configured alternate language, optionally accept auto-generated captions, and embed downloaded subtitle tracks when supported.
- Torrent mode handling remains stable (`FULL`, `SEQUENTIAL`, `STREAM`).
- Shared `style_combo`/`style_entry` helpers centralized in `ui_components.py`.
- Keyboard shortcuts active: `Ctrl+Enter` (action), `Escape` (cancel), `Ctrl+L` (clear).
- `ErrorPanel` integrated into converter and subtitle tabs for user-friendly error display.
- Focus ring animation active on all input fields.
- `Spacing.*` design tokens applied consistently across UI components.
- Phase 7 CLI can now mix audio, composite video, apply filter chains, manage a local media library, and export library data.
- Dedicated Phase 7 desktop tabs now exist for Mixer, Filters, Library, and Utilities workflows in `ravn_app/ui/tabs/` and are wired into `main_window.py`.
- Phase 7 tabs now submit work through `TaskQueue`, persist generic `operations` history rows, and surface those records in the History UI alongside downloads and conversions.
- Phase 7 task types are active in `TaskType` and no longer placeholder-only.
- **Comprehensive Utility Media Helpers** (Phase 7 / UTL-01 through UTL-10): 24 FFmpeg-backed operations across four categories (quick helpers, audio utilities, video utilities, smart helpers) are now available both in desktop UI (`utilities_tab.py` within Studio workspace) and CLI (`ravn utilities` command). All operations support queue integration, history persistence, and auto-library registration.
- **Phase 1.1 Micro-interactions**: All `CTkButton` widgets have `hover_color` token applied; Treeview rows highlight on mouse motion; progress bars use `Colors.ACCENT` for visual consistency.
- **Shell Smoothness / Theme Polish (POL-UX-01 through POL-UX-06)**: Eliminated theme toggle flash by replacing all transparent container backgrounds with stable semantic colors (`Colors.BG_PRIMARY`, `Colors.BG_SURFACE`). Added pre-transition background stabilization in `_apply_theme_preference()` to prevent white flash during dark ↔ light theme changes. Verified no full-shell rebuild on theme toggle; `refresh_i18n()` already uses in-place text updates without destroying widgets.

## Documentation Sync

- Architecture and project docs were synchronized with current UI/core structure.
- Stale references to pre-refactor layout and legacy docs were removed.
- Canonical project guidance is now centered in `CLAUDE.md` (with `README.md`, `ARCHITECTURE.md`, and `TASKS.md` kept in sync).
