# RAVN — Project Task Board

All development tasks organized by priority and status.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Done
- `[!]` — Blocked

---

## Summary

**Completed:** Phase 1 (Stabilization & Core Rewrite), Phase 2 (High Priority Features), Phase 3 (Medium Priority Features), Phase 4A (Core GUI Completeness), and Phase 4B (UI/UX Pro Max Enhancements) — 367 tests passing, 1 skipped.

**Active Backlog:** Phase 5 (Build, Package & Distribution) remains open.

---

## Phase 1 — Stabilization & Core Rewrite ✓ COMPLETE

Core functions reviewed, rewritten, and optimized. All external process execution now uses unified runner wrappers.

- [x] Audit all `subprocess` calls to FFmpeg — replace with `FFmpegRunner`
- [x] Audit all `yt-dlp` calls — replace with `YtDlpRunner`
- [x] Rewrite `converter.py`, `downloader.py`, `audio_normalizer.py`, `subtitle_manager.py`
- [x] Add task manager for long-running operations
- [x] Thread-safe callbacks (no direct UI calls from threads)
- [x] Structured logging system (`~/.config/ravn/logs/ravn.log`)
- [x] Hardened error handling with human-readable messages

**Status:** Main media path fully stabilized. Some auxiliary modules have consolidation opportunities but remain functional.

---

## Phase 2 — High Priority Features ✓ COMPLETE

User-facing improvements with high impact. All completed and tested.

### 2A — Config File Relocation [x]
- [x] OS-aware config directory detection (Linux/macOS → `~/.config/ravn/`, Windows → `%APPDATA%\ravn\`)
- [x] Migration of `ravn_config.json` and `ravn_history.db` on first run
- [x] Config schema validation with sensible defaults

### 2B — FFmpeg Error Messages [x]
- [x] `FFmpegErrorParser` class for common error patterns
- [x] User-friendly error displays in UI
- [x] "Show technical details" toggle for power users

### 2C — Drag & Drop Support [x]
- [x] `tkinterdnd2` integration
- [x] Drag & drop on Converter tab (video/audio files)
- [x] Drag & drop on Subtitle tab (subtitle + video files)
- [x] Visual drop zone highlight

### 2D — CLI Interface [x]
- [x] `ravn download <url> [--quality] [--format] [--output]`
- [x] `ravn convert <file> [--format] [--quality] [--codec] [--output]`
- [x] `ravn info <file>` — metadata display
- [x] `ravn subtitle <video> --embed <subtitle-file>`
- [x] `ravn history` — recent operations
- [x] `--json` output flag on all commands
- [x] Console script registration in `setup.py`

---

## Phase 3 — Medium Priority Features ✓ COMPLETE

### 3A — New Platform Support [x]

Extend download capabilities to new sources.

- [x] **[PLT-01]** TikTok platform handler in `platform_support.py`
- [x] **[PLT-02]** Instagram platform handler (Reels, posts)
- [x] **[PLT-03]** Twitch platform handler (VODs, clips)
- [x] **[PLT-04]** Twitter/X platform handler
- [x] **[PLT-05]** Generic "any yt-dlp supported URL" fallback
- [x] **[PLT-06]** UI platform badge/icon next to detected URLs

**Dependencies:** None. Can be started immediately.

### 3B — Database Migration [x]

Versioned migration system for schema updates.

- [x] **[DB-01]** Add `schema_version` table to SQLite
- [x] **[DB-02]** Migration runner (applies versioned scripts on startup)
- [x] **[DB-03]** Migration script: v1 → v2 (config dir relocation)
- [x] **[DB-04]** Automatic DB backup on migration

**Dependencies:** None. Can be started immediately.

### 3C — UI Tests [x]

Comprehensive test suite for widget logic and CLI.

- [x] **[TST-01]** Unit tests for all tab widget logic (without rendering)
- [x] **[TST-02]** Tests for `FFmpegRunner` and `YtDlpRunner` (mocked subprocess)
- [x] **[TST-03]** CLI command tests using `click.testing.CliRunner`
- [x] **[TST-04]** Integration tests for full download → convert pipeline
- [x] **[TST-05]** Achieve ≥ 95% code coverage (Phase 3 target modules: 97%)

**Dependencies:** None. Can be started immediately.

### 3D — System Tray [x]

Background operation and desktop notification support.

- [x] **[TRY-01]** Add `pystray` to `requirements.txt`
- [x] **[TRY-02]** System tray icon with right-click menu (Open, Pause Queue, Quit)
- [x] **[TRY-03]** Desktop notifications on download/conversion complete
- [x] **[TRY-04]** Minimize to tray instead of closing

**Dependencies:** None. Can be started immediately.

---

















## Phase 4 — GUI Polish & Full Controllability

Every function accessible and controllable via GUI. Better frontend, full control, no CLI-only features, visual enhancements.

### 4A — Core GUI Completeness [x]

Full UI coverage and queue management.

- [x] **[GUI-01]** Audit all core features — ensure every function has UI control
- [x] **[GUI-02]** Real-time FFmpeg progress bar (parse `-progress pipe:1`)
- [x] **[GUI-03]** Download queue panel — show queued, active, completed jobs
- [x] **[GUI-04]** Per-job cancel button in queue panel
- [x] **[GUI-05]** Batch download — accept multiple URLs
- [x] **[GUI-06]** Batch convert — select multiple files with one profile
- [x] **[GUI-07]** Settings panel for advanced FFmpeg options (CRF, preset, bitrate)
- [x] **[GUI-08]** Output directory selector with "remember last used"
- [x] **[GUI-09]** Keyboard shortcuts (Ctrl+D, Ctrl+O, Ctrl+Q, etc.)
- [x] **[GUI-10]** "Open output folder" button after successful operation

### 4B — UI/UX Pro Max Enhancements [x]

Design system, accessibility, and visual polish.

- [x] **[UX-01]** Visual Design & Theme — consistent corner radius, dark mode colors, semantic palette
- [x] **[UX-02]** Icons — replace emojis with vector icons (Lucide or similar)
- [x] **[UX-03]** Interaction & Feedback — disabled buttons during operations, spinner animations
- [x] **[UX-04]** Drag & Drop Visualization — dashed borders, color changes on hover
- [x] **[UX-05]** Layout & Spacing — standardize padding/margin to 4px or 8px rhythm
- [x] **[UX-06]** Forms & Accessibility — persistent labels (not placeholders), proper labeling
- [x] **[UX-07]** Error Placement — show errors near problematic inputs (not pop-ups)
- [x] **[UX-08]** Typography Hierarchy — consistent sizing and color contrast (≥4.5:1)
- [x] **[UX-09]** Navigation — tab icons + text, clear active state

**Dependencies:** Core GUI completeness (4A).

---

## Phase 5 — Build, Package & Distribution

Cross-platform binary builds and installers. (After GUI is polished)

- [ ] **[BLD-01]** Update `ravn.spec` (PyInstaller) — include FFmpeg binaries for Windows
- [ ] **[BLD-02]** Bundle FFmpeg Windows binaries in `assets/ffmpeg/win64/`
- [ ] **[BLD-03]** Auto-detect bundled FFmpeg in `ffmpeg_checker.py`
- [ ] **[BLD-04]** Update `build.ps1` — full Windows build pipeline
- [ ] **[BLD-05]** Create `build.sh` — Linux build pipeline (PyInstaller → AppImage or .deb)
- [ ] **[BLD-06]** macOS build pipeline — PyInstaller → `.app` bundle → `.dmg`
- [ ] **[BLD-07]** GitHub Actions `tests.yml` — Windows/Linux/macOS artifact builds on tag
- [ ] **[BLD-08]** GitHub Actions `release.yml` — auto-publish on `v*` tag
- [ ] **[BLD-09]** Test installer on clean VM — verify FFmpeg found, app launches, config dir created
- [ ] **[BLD-10]** Code-sign Windows executable (minimum: self-signed cert)

**Dependencies:** GUI polish complete (Phase 4).

---

## General Notes

- All file paths use `pathlib.Path` — no hardcoded separators
- All user-facing strings support TR/EN toggle (i18n-ready structure)
- Minimum Python version: 3.9
- FFmpeg minimum version: 5.0
- yt-dlp must always be latest release (no version pin)

---

## Quick Reference: What's Next?

**Phase 4 (Next Priority) — GUI Polish & Full Controllability:**
1. Audit all core features — every function has UI control
2. Real-time FFmpeg progress bar parsing
3. Download queue panel with job management
4. Batch operations (download/convert)
5. Settings panel for advanced options
6. UI/UX enhancements (icons, themes, accessibility)

**Phase 6 (After GUI is Done) — Build & Distribution:**
1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing
