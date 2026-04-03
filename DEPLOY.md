# DEPLOY

## Status

**Phase 5 build / packaging / distribution is still open.**

This file describes the current packaging reality of the repository and the remaining work to turn RAVN into a clean distributable desktop application.

---

## Current Repository Reality

The repo already contains early build/distribution artifacts:

- `build.ps1`
- `ravn.spec`
- `ravn_app/core/app_builder.py`
- `setup.py`

What these currently mean in practice:

- there is a basic Windows-oriented helper script for environment checks, install/test/run, and cleanup
- there is a PyInstaller spec file
- there is packaging-related helper code in the core layer
- there is an installable Python package entrypoint for `ravn`

What is **not** yet complete:

- finished Windows bundling story for FFmpeg/runtime assets
- Linux packaging pipeline
- macOS packaging pipeline
- artifact publishing pipeline
- clean-installer verification across target platforms
- code-signing/distribution hardening

So: packaging **exists as scaffolding**, but **not yet as a fully validated release pipeline**.

---

## Existing Files

### `build.ps1`

Current behavior:

- environment check
- dependency install helper
- test helper
- local run helper
- cleanup helper

Limitations:

- not a complete production packaging pipeline
- not yet the full Phase 5 Windows release process
- assumes developer/local usage more than release automation

### `ravn.spec`

Current behavior:

- PyInstaller spec exists
- basic hidden imports/data collection are defined
- desktop executable target is configured

Limitations:

- not yet the finished bundled-runtime strategy
- FFmpeg bundling/lookup hardening is still an open task
- signing/distribution concerns are not solved here

### `setup.py`

Current behavior:

- installable package metadata
- console-script entrypoint for `ravn`

Limitations:

- this supports Python-package installation, not full desktop distribution by itself

---

## Phase 5 Checklist

The open distribution/build work currently maps to the following task set.

- [ ] **BLD-01** Update `ravn.spec` (PyInstaller) to include FFmpeg binaries for Windows
- [ ] **BLD-02** Bundle FFmpeg Windows binaries under `assets/ffmpeg/win64/`
- [ ] **BLD-03** Auto-detect bundled FFmpeg in `ravn_app/utils/ffmpeg_checker.py`
- [ ] **BLD-04** Expand `build.ps1` into a fuller Windows build pipeline
- [ ] **BLD-05** Create `build.sh` for Linux build/distribution flow
- [ ] **BLD-06** Add macOS build pipeline for `.app` / `.dmg`
- [ ] **BLD-07** Add GitHub Actions test/build artifact workflow
- [ ] **BLD-08** Add GitHub Actions release publishing workflow
- [ ] **BLD-09** Verify installer behavior on a clean VM / clean environment
- [ ] **BLD-10** Add Windows executable signing strategy (minimum viable signing path)

---

## Recommended Packaging Direction

### Windows

Primary target direction:

- PyInstaller executable/app folder
- bundled FFmpeg/FFprobe where required
- installer layer on top after basic runtime validation

Validation goals:

- app launches without developer environment assumptions
- FFmpeg is found reliably
- config/data directories are created correctly
- tray/theme/language/runtime assets work in packaged form

### Linux

Likely direction:

- PyInstaller build output
- AppImage or `.deb` packaging after runtime validation

Validation goals:

- launcher works on clean environments
- FFmpeg/runtime discovery is clear and documented
- desktop entry/icon integration is sane

### macOS

Likely direction:

- PyInstaller-generated `.app`
- `.dmg` packaging after app validation

Validation goals:

- app bundle launches cleanly
- signing/notarization path is documented when adopted
- runtime tool discovery is stable

---

## Deployment Principles

When Phase 5 work begins or continues, keep these principles intact:

1. **Do not break source-checkout development** while improving packaged delivery.
2. **Prefer OS-aware path helpers** from `config_paths.py`; do not reintroduce hardcoded paths.
3. **Keep external process execution on shared runners**; do not create packaging-only parallel execution paths unless unavoidable.
4. **Validate FFmpeg / yt-dlp / aria2 behavior in real packaged environments**, not only in dev shells.
5. **Document packaged runtime assumptions clearly** in `README.md`, `ARCHITECTURE.md`, and this file.

---

## What To Verify During Packaging Work

### Runtime startup
- logging initializes
- config/data/cache directories are created
- legacy migration does not fail in packaged mode
- translations/theme assets are available

### Tool availability
- FFmpeg/FFprobe discovered correctly
- yt-dlp executable path behavior is clear
- aria2 expectations are explicit for torrent support

### Feature sanity checks
- launch app
- open each workspace
- run at least one download
- run one conversion
- run one utility task
- verify queue/history persistence
- verify media-library auto-add still works

### Platform-specific validation
- file open/folder open helpers
- tray behavior
- path separators / writable directories
- packaging of assets/translations/icons

---

## Developer Commands (Current Reality)

The repo currently supports developer-oriented local flows such as:

```powershell
./build.ps1 check
./build.ps1 test
./build.ps1 run
```

And Python-package installation via:

```bash
pip install -e .
```

These should not be mistaken for the finished cross-platform distribution pipeline.

---

## Summary

RAVN already has the beginnings of a packaging story, but **Phase 5 is still incomplete**.

Use this file as the source of truth for:

- what packaging/distribution artifacts already exist
- what they currently do
- what remains to be built and validated
