# Shared Runner / Subprocess Audit

Verified on 2026-04-05.

This document records the repository-wide audit of direct `subprocess` usage after the shared-runner cleanup.

## Goal

Distinguish between:

1. **runner-layer expected** usage
2. **runtime media-path debt** that should move into shared runners
3. **platform integration helpers** that should remain separate
4. **build/deployment-only helpers** that should remain separate

Tests are excluded from this audit because they intentionally patch/inspect process execution behavior.

---

## Summary

This audit is complete.

- Active runtime media-execution debt was migrated into the shared runner layer.
- Remaining direct `subprocess` usage is now limited to:
  - runner-layer execution internals
  - platform/open-file/open-player helpers
  - generic tool-health probing
  - packaging/update helpers

---

## Classification Table

| File | Classification | Status | Notes |
|---|---|---:|---|
| `ravn_app/core/runners/base.py` | runner-layer expected | keep | shared process execution base (`Popen`, timeout, cancellation, result normalization) |
| `ravn_app/core/runners/ffmpeg.py` | runner-layer expected | keep | FFmpeg / FFprobe execution, progress parsing, probe helpers |
| `ravn_app/core/runners/ytdlp.py` | runner-layer expected | keep | yt-dlp execution and metadata extraction |
| `ravn_app/core/runners/aria2.py` | runner-layer expected | keep | aria2 torrent execution |
| `ravn_app/core/media_helpers.py` | runtime media-path debt | **migrated** | `detect_silence`, `detect_black_frames`, `generate_scene_previews`, `generate_scene_thumbnails` now use `FFmpegRunner.run_raw()` |
| `ravn_app/utils/ffmpeg_checker.py` | runtime/support helper debt | **migrated** | now uses `FFmpegRunner` / `run_ffprobe_json()` |
| `ravn_app/utils/system_utils.py` | runtime/support helper debt | **migrated** | `get_ffmpeg_version()` now uses `FFmpegRunner.get_version()` |
| `ravn_app/core/tool_health.py` | platform integration helper | keep | generic tool version probing for dependency health, not a media execution path |
| `ravn_app/ui/main_window.py` | platform integration helper | keep | OS-specific open-folder behavior |
| `ravn_app/ui/tabs/library_tab.py` | platform integration helper | keep | OS-specific open-file/open-folder behavior |
| `ravn_app/ui/tabs/torrent_tab.py` | platform integration helper | keep | open target in system default app/player |
| `ravn_app/ui/tabs/download_tab.py` | platform integration helper | keep | open URL/file in system default app/player |
| `ravn_app/core/update_manager.py` | platform integration helper | keep | launch downloaded installer/archive handling |
| `ravn_app/core/app_builder.py` | build/deployment-only helper | keep | PyInstaller/NSIS/build pipeline commands |

---

## Migrated Runtime Media Paths

### 1. `MediaHelpers` smart analysis operations

Previously these operations bypassed shared runners with direct `subprocess.run()` calls:

- `detect_silence()`
- `detect_black_frames()`
- `generate_scene_previews()`
- `generate_scene_thumbnails()`

They now execute through `FFmpegRunner.run_raw()`.

### Why this matters

This aligns them with the shared runner model and gives them the same:

- timeout handling
- cancellation/status model
- structured `RunnerResult`
- normalized process logging
- consistent FFmpeg error shaping

### 2. `FFmpegCodecChecker`

Previously it called FFprobe and FFmpeg directly.

It now uses:

- `FFmpegRunner.run_ffprobe_json()`
- `FFmpegRunner.get_version()`

### 3. `system_utils.get_ffmpeg_version()`

Previously it called `subprocess.run(["ffmpeg", "-version"])` directly.

It now uses `FFmpegRunner.get_version()`.

---

## Consolidated Concerns Now Covered by Shared Runners

The migrated runtime media paths now inherit shared runner behavior for:

- **timeout handling** via `BaseRunner._run_process()`
- **cancellation model** via runner state/process tracking
- **logging** via runner-level command execution logging
- **structured process results** via `RunnerResult`
- **user-facing error shaping** via runner `_parse_error()` implementations

---

## ARC-04 Boundary Decision

OS-level helpers remain intentionally outside the runner layer.

Examples:

- open file in default application
- reveal file in folder
- open folder in Finder/Explorer/xdg-open
- launch downloaded installer

Reason:

These are **platform integration behaviors**, not media-processing flows. Wrapping them in media runners would blur responsibilities and weaken the architecture.

---

## Remaining Direct `subprocess` Usage

After migration, remaining direct `subprocess` usage in runtime code is intentional and falls into one of these buckets:

1. runner-layer expected
2. platform integration helper
3. build/deployment-only helper

No active runtime media-execution debt remains in the main acquisition/studio/utility paths audited here.

---

## Verification

Targeted verification relevant to this phase:

- `pytest -q tests/test_runners.py tests/test_media_helpers.py tests/test_cli.py`
- `pytest -q tests/test_ui_logic.py tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q`

Observed validated baseline at the time of this audit:

- targeted audit sweep: `126 passed`
- full suite: `609 passed, 1 skipped`

---

## Follow-up

Later follow-up work moved into UX hardening, optimization, and packaging polish. See `TASKS.md` for the current roadmap.
