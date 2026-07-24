# Changelog

All notable changes to the RAVN project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.2.0] - 2026-07-24

### Added
- **Open Source Governance Suite**: Added `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub Issue Templates (`bug_report.md`, `feature_request.md`), PR Template, and `CODEOWNERS`.
- **Security & Dependency Automation**: Added `dependabot.yml`, a `CodeQL` code-scanning workflow, and automated `pip-audit` + CycloneDX SBOM generation in `.github/workflows/security.yml`. Release builds now also attach a versioned SBOM (`RAVN-windows-x64.sbom.json`) to each GitHub Release.
- **Opt-in local crash reporting**: Unhandled exceptions now write a timestamped, offline-only crash report (`ravn_app/core/crash_reporter.py`) next to the app logs. No network calls, no third-party SDK; can be disabled from Settings.
- **In-app update check**: A "Check for Updates" button in Settings now uses the app's `UpdateManager` to compare against the latest GitHub Release.
- **Windows MSI installer (first pass)**: Added a WiX v4 package (`packaging/ravn.wxs`) and a `build.ps1 -Action ci-msi` step, shipped alongside the existing zip release. Not yet end-to-end verified on a real Windows runner.
- **Playlist Fetch Instant Estimates**: Shallow entry list immediately computes duration-based size estimates for all quality labels, ensuring rows never render blank before detail resolution completes.

### Changed
- **Parallel Playlist Entry Resolution**: Reworked progressive detail fetches in `ytdlp.py` from serial loops to a thread-bounded pool (`ThreadPoolExecutor`, default `max_workers=6`) with thread-local `YoutubeDL` clients, achieving significantly faster playlist previews.
- **Coverage Floor**: Raised pytest coverage floor in CI from 48% to 49% (measured baseline ~50.7%, kept a real safety margin below it instead of setting the floor flush against the measurement).
- **Test coverage**: `ravn_app/utils/` raised from 57-80% to 99% across `metadata_handler.py`, `ffmpeg_checker.py`, `system_utils.py`, and `file_utils.py`.

### Fixed
- **Update check always reported failure**: `UpdateManager.check_for_updates()` returns a `bool`, but the Settings-tab wiring checked `if result is not None`, which is always true for a bool — so the feature silently misreported every outcome as "check failed". Fixed to read the actual release info correctly.
- The bundled `UpdateManager` defaulted to the wrong GitHub owner (`ravn-project` instead of `waldseelen`).

---

## [1.0.0] - 2026-04-07

### Added
- Multi-workspace desktop interface (Home, Download, Studio, Library).
- Torrent support (`aria2c` integration for `.torrent` files and magnet URIs).
- Audio/Video Mixer tabs with custom parameter presets and stream combining.
- Local SQLite media library with full-text search, custom tags, collections, and JSON export.
- Integrated CLI tool with full feature coverage (`ravn_app.cli`).
- Packaging pipeline with PyInstaller, `wix`/ZIP bundler, and Windows code-signing workflow.
