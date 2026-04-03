
















### My Recommendation

If choosing only a first slice, start with:

1. smart format selector
2. playlist partial download improvements
3. filename templates
4. post-download pipeline
5. subtitle automation upgrade

That set has the best product payoff for the least architectural disruption.

**(After GUI is Done) — Build \& Distribution:**

1. PyInstaller spec updates with FFmpeg bundling
2. Windows/Linux/macOS build pipelines
3. GitHub Actions CI/CD setup
4. Installer testing and code signing

## Phase X — Build, Package \& Distribution

Cross-platform binary builds and installers. (After GUI is polished)

- \[ ] **\[BLD-01]** Update `ravn.spec` (PyInstaller) — include FFmpeg binaries for Windows
- \[ ] **\[BLD-02]** Bundle FFmpeg Windows binaries in `assets/ffmpeg/win64/`
- \[ ] **\[BLD-03]** Auto-detect bundled FFmpeg in `ffmpeg\_checker.py`
- \[ ] **\[BLD-04]** Update `build.ps1` — full Windows build pipeline
- \[ ] **\[BLD-05]** Create `build.sh` — Linux build pipeline (PyInstaller → AppImage or .deb)
- \[ ] **\[BLD-06]** macOS build pipeline — PyInstaller → `.app` bundle → `.dmg`
- \[ ] **\[BLD-07]** GitHub Actions `tests.yml` — Windows/Linux/macOS artifact builds on tag
- \[ ] **\[BLD-08]** GitHub Actions `release.yml` — auto-publish on `v\*` tag
- \[ ] **\[BLD-09]** Test installer on clean VM — verify FFmpeg found, app launches, config dir created
- \[ ] **\[BLD-10]** Code-sign Windows executable (minimum: self-signed cert)

**Dependencies:** GUI polish complete (Phase 4).

\---

## General Notes

- All file paths use `pathlib.Path` — no hardcoded separators
- All user-facing strings support TR/EN toggle (i18n-ready structure)
- Minimum Python version: 3.9
- FFmpeg minimum version: 5.0
- yt-dlp must always be latest release (no version pin)

\---
