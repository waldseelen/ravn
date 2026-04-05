# PROGRESS

## Snapshot

Verified on 2026-04-03.

This file is the validated implementation snapshot for the current repository state.

---

## Confirmed Repository Reality

### Core platform/runtime

- Repository structure is stable: desktop entrypoint, CLI entrypoint, layered core, modular UI, tests, build script, and PyInstaller spec are present.
- Main external-tool execution paths are consolidated around shared runners in `ravn_app/core/runners/`.
- Structured logging is centralized in `ravn_app/core/logging_config.py`.
- OS-aware config/data/cache path handling and legacy migration are active through `ravn_app/core/config_paths.py` and `ravn.py`.
- Drag-and-drop uses `tkinterdnd2` when available and degrades safely.
- Theme system is strict two-theme (`dark`, `light`) with legacy normalization.
- Localization is active through `ravn_app/core/i18n.py` and `ravn_app/translations/`.

### Desktop shell / UX

- The desktop shell is grouped into workspaces: `Home`, `Download`, `Studio`, `Library`.
- Queue is exposed through a global right-side panel/drawer instead of top-level navigation.
- Desktop startup centering now uses taskbar-aware usable bounds and prefers the active monitor on Windows.
- Settings are exposed as an independent lower-left utility/workspace entry.
- Theme/language toggles live directly in the shell sidebar utility area.
- Shell-level command palette is active via `Ctrl+K`.
- Shell-level settings shortcut is active via `Ctrl+,`.
- Workspace guidance panels use progressive disclosure.
- The shell uses mounted workspace switching to reduce redraw flicker.
- Theme and language changes use lighter in-place refresh behavior than earlier shell rebuild patterns.

### Acquisition / download stack

- Download flow is wired end-to-end with background execution and UI-safe callback scheduling.
- Single URL, playlist, batch (up to 50 URLs), and torrent/magnet flows are active.
- Playlist flow supports title/duration filtering, popularity-aware filtering where metadata exists, visible-row bulk actions, and range-based selection.
- Download naming presets/templates are active through `download_naming.py`.
- Downloader subtitle automation is active through preferred/fallback language selection, optional auto-generated fallback, and optional auto-embed behavior.
- Post-download automation is active through `download_postprocess`.
- Metadata normalization/enrichment is active through `download_metadata.py`.
- Reusable acquisition profiles are active through `download_profiles.py`.
- Robustness controls are active through `download_robustness`.
- Collapsed advanced acquisition settings are active through `download_advanced`.
- CLI download flow now exposes the same intent-driven acquisition concepts instead of raw yt-dlp flag mirroring.

### Queue / history / library

- Queue/callback infrastructure is active in `ravn_app/core/task_manager.py`.
- Queue panel supports queued/running/completed visibility and cancel/open-folder actions.
- History UI aggregates downloads, conversions, and generic Phase 7 operation records.
- `MediaLibrary` and auto-library registration are active.
- Successful supported outputs from download/convert/mixer/filter/utility flows can register into the local media library.

### Studio / media tools

- Conversion flow is active through FFmpeg-backed shared logic.
- Subtitle processing/embed flows are active.
- Filters and mixer feature tabs are active in desktop + CLI form.
- Utilities workflow is active with 24 FFmpeg-backed helper operations across quick/audio/video/smart categories.
- FFmpeg real-time progress parsing is active.
- `ErrorPanel` is integrated into converter and subtitle tabs.

### Torrent stack

- `Aria2Runner` is active.
- `TorrentDownloader` is active.
- Torrent modes remain stable: `FULL`, `SEQUENTIAL`, `STREAM`.
- Torrent UI exposes queueable rows, progress metrics, pause/resume controls, filters, and payload child rows.

---

## Acquisition Engine Status

The yt-dlp acquisition-engine upgrade is fully landed.

Completed tasks:

- `YTD-01` filename templating + naming presets
- `YTD-02` playlist partial selection/filtering/range support
- `YTD-03` subtitle automation upgrade
- `YTD-04` post-download automation pipeline
- `YTD-05` metadata enrichment / normalization
- `YTD-06` reusable download profiles
- `YTD-07` robustness controls
- `YTD-08` collapsed advanced acquisition settings
- `YTD-09` CLI acquisition parity
- `YTD-10` expanded tests for acquisition behavior
- `YTD-11` documentation sync

Resulting acquisition capabilities now include:

- reusable profiles (`Custom`, `Music`, `Podcast`, `Archive`, `Social Clip`)
- naming presets and token templates
- subtitle preferences + fallback + embed behavior
- post-download automation
- normalized acquisition metadata for library registration
- duplicate skipping via archive tracking
- partial recovery/resume support
- fallback format retries
- optional rate limits
- browser/cookies.txt auth handoff
- fragment/network tuning
- CLI scripting of the same concepts

---

## UX / Settings Consolidation Reality

Recent validated UX/settings realities:

- `main_window.py` is a thin shell orchestrator.
- Download-specific logic lives in `ravn_app/ui/tabs/download_tab.py`.
- Reusable widgets live under `ravn_app/ui/components/`.
- Settings remain compact and scrollable rather than nested across many sub-tabs.
- Download settings now expose:
  - naming presets/templates
  - subtitle preferences
  - post-download automation
  - reliability controls
  - collapsed advanced acquisition controls
- Download workspace exposes a compact profile selector instead of a second downloader screen.
- Playlist sort dialog keeps selected-count/size summaries and visibility-focused table styling.
- `history_settings_tab.py` width/spacing behavior was tightened to avoid layout stretch issues.

---

## Phase Completion Status

- **Phase 1** — Complete
- **Phase 2** — Complete
- **Phase 3** — Complete
- **Phase 4A** — Complete
- **Phase 4B** — Complete
- **Phase 4C** — Complete
- **Phase 4D** — Complete
- **Phase 5** — Open
- **Phase 6** — Complete
- **Phase 7** — Complete
- **Phase 8** — Complete

---

## Validation Status

Verified on 2026-04-03:

- Full suite:
  - `pytest -q`
  - `578 passed, 1 skipped` (`579` collected)
- CLI + acquisition regression sweep:
  - `pytest -q tests/test_cli.py tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_runners.py`
  - `245 passed, 1 skipped`
- Acquisition-engine regression sweep:
  - `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_runners.py`
  - `206 passed, 1 skipped`
- Playlist/download regression sweep:
  - `pytest -q tests/test_ui_logic.py tests/test_runners.py`
  - `147 passed`
- Download/settings regression sweep:
  - `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_database_manager.py`
  - `137 passed, 1 skipped`
- UI/i18n/design-token regression sweep:
  - `pytest -q tests/test_utilities_tab.py tests/test_i18n_and_design_tokens.py tests/test_ui_logic.py tests/test_ui_components.py tests/test_app_builder.py`
  - `108 passed`

---

## Functional Highlights

### Acquisition

- quality-based size estimation
- naming presets/templates with sanitization
- subtitle preference + fallback behavior
- post-download automation pipeline
- metadata normalization + library tags
- reusable acquisition profiles
- robustness controls
- collapsed advanced acquisition controls
- CLI parity for intent-driven acquisition

### Processing / studio

- conversion
- subtitle processing/embed
- filters
- mixer
- utilities helpers
- queue/history integration
- optional library auto-add

### Organization

- local media library
- search/tags/collections/export
- aggregated history for downloads/conversions/operations

### Shell / UX

- grouped workspace shell
- queue drawer
- settings workspace entry
- command palette
- compact utility toggles
- adaptive layout behavior

---

## Open Reality / Remaining Work

The main open project area is still **Phase 5 release readiness and Windows packaging**.

Current build/distribution artifacts exist (`build.ps1`, `ravn.spec`, `app_builder.py`), but the packaged delivery story is not yet finished. The current documented direction is to harden runtime/tooling behavior first, then complete a **Windows-only** packaging/release pipeline.

---

## Documentation Sync State

Repository documentation was refreshed and aligned around the current runtime model:

- `README.md` now acts as the comprehensive user/project overview
- `ARCHITECTURE.md` now focuses on system structure, module boundaries, and runtime flows
- `TASKS.md` now also carries the active hardening + Windows release roadmap
- `CLAUDE.md` remains the compact engineering entrypoint/addendum
