# RAVN — Project Task Board

All development tasks organized by priority and status.

﻿Read AGENT.md, CLAUDE.md , ARCHITECTURE.md, README.md and PROGRESS.md first. Treat them as one
unified instruction set and follow all rules, constraints, and context strictly.

Then execute TASKS.md as the single source of truth. Only complete tasks marked [ ]. Never touch
or redo tasks marked [x].

Do not deviate from scope, structure, or intent. If any conflict occurs, follow the most recent
and most specific instruction.

After completing all eligible tasks, update AGENT.md, CLAUDE.md, and PROGRESS.md briefly and
accurately based on this session.

---

## Status Legend

- `[ ]` — Not started
- `[~]` — In progress
- `[x]` — Done
- `[!]` — Blocked

---

---


**(After GUI is Done) — Build & Distribution:**

1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing

## Phase X — Build, Package & Distribution

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
