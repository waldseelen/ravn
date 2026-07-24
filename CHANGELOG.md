# Changelog

All notable changes to the RAVN project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [1.3.0] - 2026-07-24

### Changed
- **RAVN is now maintained as a cross-platform product**, not Windows-first: `.github/workflows/tests.yml` now runs the full test suite on Linux, macOS, and Windows (in addition to the existing Python 3.11/3.12/3.13 matrix) on every push and pull request. Docs (`README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, `AGENTS.md`, `CLAUDE.md`) updated to match. Packaged (downloadable) releases remain Windows-only for now; Linux/macOS packaging is tracked as a follow-up in `TASKS.md`.

### Fixed
- **`yt-dlp` self-update silently produced a broken binary on Linux/macOS**: `YtDlpRunner.update()` always downloaded the Windows `yt-dlp.exe` GitHub release asset regardless of OS, "succeeding" while leaving a non-executable Windows binary in place. Now selects the correct release asset and local filename per platform (`yt-dlp.exe` / `yt-dlp_macos` / extension-less `yt-dlp`) and marks the file executable on POSIX.
- **"Open with player" silently did nothing on macOS**: fell through to `xdg-open`, which doesn't exist there. Now uses `open` on macOS, `xdg-open` on Linux, and `os.startfile` on Windows.
- `ravn.spec`'s hardcoded `C:\Windows\System32` CRT binaries and the Windows-only `version_info.txt` PyInstaller argument are now gated behind `sys.platform == "win32"`, so a non-Windows `pyinstaller ravn.spec` invocation no longer hard-fails on those lines (packaging itself is still Windows-only this release).
- A pytest crash-reporting corruption bug (`NotImplementedError: cannot instantiate 'WindowsPath'`) caused by three `test_config_paths.py` tests reloading the module after patching `sys.platform`; removed the unnecessary `importlib.reload` (fixed in a prior commit this cycle, `a5c3f72`).
- Found and fixed two more pre-existing tests that only ever passed by accident of which OS ran them, surfaced while turning on the new Linux/macOS CI matrix: `test_tool_installer.py`'s Windows-PATH-merge tests patched `os.name` to `"nt"` but not `os.pathsep` (still `:` on POSIX), so they silently misparsed `;`-separated Windows paths — and failing inside that state crashed pytest's own failure-reporting, since `os.pathsep`/`os.name` are real module attributes, not derived dynamically. `test_ffmpeg_checker.py`'s bundled-tool-resolution tests hardcoded a `win64` fixture directory without pinning `ffmpeg_checker._PLATFORM_FFMPEG_DIR` (a module-level constant frozen to the host OS at import time), so they only ever passed on an actual Windows host. Both are now OS-independent.

---

## [1.2.0] - 2026-07-24

### Added
- **Open Source Governance Suite**: Added `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, GitHub Issue Templates (`bug_report.md`, `feature_request.md`), PR Template, and `CODEOWNERS`.
- **Security & Dependency Automation**: Added `dependabot.yml`, a `CodeQL` code-scanning workflow, and automated `pip-audit` + CycloneDX SBOM generation in `.github/workflows/security.yml`. Release builds now also attach a versioned SBOM (`RAVN-windows-x64.sbom.json`) to each GitHub Release.
- **Opt-in local crash reporting**: Unhandled exceptions now write a timestamped, offline-only crash report (`ravn_app/core/crash_reporter.py`) next to the app logs. No network calls, no third-party SDK; can be disabled from Settings.
- **In-app update check**: A "Check for Updates" button in Settings now uses the app's `UpdateManager` to compare against the latest GitHub Release.
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
