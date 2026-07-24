# Changelog

All notable changes to the RAVN project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Open Source Governance Suite**: Added `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub Issue Templates (`bug_report.md`, `feature_request.md`), PR Template, and `CODEOWNERS`.
- **Security & Dependency Automation**: Added `dependabot.yml` and automated `pip-audit` + CycloneDX SBOM workflow in `.github/workflows/security.yml`.
- **Playlist Fetch Instant Estimates**: Shallow entry list immediately computes duration-based size estimates for all quality labels, ensuring rows never render blank before detail resolution completes.

### Changed
- **Parallel Playlist Entry Resolution**: Reworked progressive detail fetches in `ytdlp.py` from serial loops to a thread-bounded pool (`ThreadPoolExecutor`, default `max_workers=6`) with thread-local `YoutubeDL` clients, achieving significantly faster playlist previews.
- **Coverage Floor**: Raised pytest coverage floor in CI from 48% to 50%.

---

## [1.0.0] - 2026-04-07

### Added
- Multi-workspace desktop interface (Home, Download, Studio, Library).
- Torrent support (`aria2c` integration for `.torrent` files and magnet URIs).
- Audio/Video Mixer tabs with custom parameter presets and stream combining.
- Local SQLite media library with full-text search, custom tags, collections, and JSON export.
- Integrated CLI tool with full feature coverage (`ravn_app.cli`).
- Packaging pipeline with PyInstaller, `wix`/ZIP bundler, and Windows code-signing workflow.
