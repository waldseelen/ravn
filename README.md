<p align="center">
  <img src="assets/ravnapp.jpeg" alt="RAVN brand image" width="220">
</p>

<p align="center">
  <img src="assets/ravn-icon-256.png" alt="RAVN icon" width="96" height="96">
</p>

<h1 align="center">RAVN</h1>

<p align="center">
  <strong>RAVN is a cross-platform desktop and CLI app for downloading, processing, organizing, and automating local media workflows.</strong>
</p>

<p align="center">
  <a href="https://github.com/waldseelen/ravn/releases"><img alt="Latest release" src="https://img.shields.io/github/v/release/waldseelen/ravn?display_name=tag&label=release"></a>
  <a href="https://github.com/waldseelen/ravn/releases"><img alt="Downloads" src="https://img.shields.io/github/downloads/waldseelen/ravn/total?label=downloads"></a>
  <a href="https://github.com/waldseelen/ravn/actions/workflows/windows-package.yml"><img alt="Windows package workflow" src="https://img.shields.io/github/actions/workflow/status/waldseelen/ravn/windows-package.yml?branch=main&label=windows%20package"></a>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-0078D6?logo=windows&logoColor=white">
  <img alt="UI" src="https://img.shields.io/badge/UI-CustomTkinter-1F6FEB">
  <img alt="CLI" src="https://img.shields.io/badge/CLI-Click-6C47FF">
</p>

<p align="center">
  <a href="https://github.com/waldseelen/ravn/releases">Download the latest Windows build</a>
</p>

---

- Download videos, audio, playlists, batches, magnets, and `.torrent` files from one interface
- Convert, extract, subtitle, filter, mix, and optimize media with FFmpeg-backed tools
- Keep a local library with history, tags, collections, and export support
- Run the same core workflows from the CLI with script-friendly JSON output
- Get clear tool-health feedback so missing dependencies do not feel like an app-wide failure

> **RAVN is not just a downloader — it is a local media pipeline.**

## Demo

> Demo GIF placeholder: add an end-to-end capture here (`download -> process -> library`) when `docs/demo.gif` is available.

<p align="center">
  <img src="docs/screenshots/home-workspace.png" alt="RAVN Home workspace" width="48%">
  <img src="docs/screenshots/download-workspace.png" alt="RAVN Download workspace" width="48%">
</p>
<p align="center">
  <img src="docs/screenshots/studio-workspace.png" alt="RAVN Studio workspace" width="48%">
  <img src="docs/screenshots/library-workspace.png" alt="RAVN Library workspace" width="48%">
</p>

## Use Cases

- **Download playlists and filter content** before committing to large batch jobs.
- **Extract audio / create karaoke tracks** by combining download, trim, subtitle, mixer, and replace-audio workflows around your own local media assets.
- **Convert and optimize media files** for archive, sharing, editing, or device playback.
- **Manage a local media library** with history, tags, collections, search, and export.
- **Automate workflows via CLI** for repeatable download, processing, and cataloging tasks.

## Features

### Download
- Smart source handling for URLs, playlists, batch links, magnets, and `.torrent` files
- Playlist review with filtering, range selection, and selective download
- Video/audio output switching, quality selection, and reusable acquisition profiles
- Naming presets/templates, subtitle preferences, metadata enrichment, and post-download automation
- Optional torrent support through `aria2c`

### Processing
- Video and audio conversion
- Subtitle embed and subtitle-sidecar workflows
- FFmpeg-based filters and adjustments
- Audio/video mixer operations
- Utility helpers for remux, trim, preview, thumbnail, loudness, scene detection, and more

### Library
- Local media library with metadata-aware registration
- Aggregated history for downloads, conversions, and other media operations
- Tags, collections, search, statistics, and export
- Background queue visibility with task status and quick actions

### Automation
- CLI commands for `download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, and `utilities`
- Shared core logic between desktop and CLI surfaces
- `--json` support for automation-friendly output
- Good fit for repeatable local media workflows and scripting

## Quick Start

### Windows release

1. Download the latest `RAVN-windows-x64.zip` from [GitHub Releases](https://github.com/waldseelen/ravn/releases).
2. Extract the archive.
3. Run `RAVN.exe`.
4. If the app reports missing tools, install the required dependencies from [DEPENDENCIES.md](DEPENDENCIES.md).
5. Paste a URL, playlist, magnet link, or local file into the relevant workspace and start working.

### Run from source

```bash
pip install -r requirements.txt
pip install -e .
python ravn.py
ravn --help
```

If the `ravn` command is not available on your shell yet, use:

```bash
python -m ravn_app.cli --help
```

## CLI Examples

```bash
ravn download "https://example.com/video" --profile archive --format mp4 --quality 1080p
ravn torrent "magnet:?xt=urn:btih:..." --sequential
ravn convert input.mp4 --format mkv --quality high
ravn utilities --operation thumbnail input.mp4 --output thumb.jpg
ravn library search --query tutorial --tags archive --json
```

## Dependencies

### Required
- Python 3.9+ (Not required for Windows packaged release)
- FFmpeg (Bundled in Windows packaged release)
- FFprobe (Bundled in Windows packaged release)
- yt-dlp (Self-managed in Windows packaged release)
- Python packages from `requirements.txt` (Not required for Windows packaged release)

### Optional
- `aria2c` for torrent and magnet workflows
- `tkinterdnd2` for drag-and-drop support

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Full setup and troubleshooting guidance lives in [DEPENDENCIES.md](DEPENDENCIES.md).

## Platform and Release Notes

- RAVN runs on **Windows, Linux, and macOS** — the test suite runs on all three in CI on every push/PR.
- **Windows** is currently the only *packaged* (pre-built, downloadable) release target; Linux and macOS packaged artifacts are a planned follow-up (see [TASKS.md](TASKS.md)). Running from source works on all three today.
- Packaged Windows builds automatically bundle FFmpeg/FFprobe and self-update `yt-dlp`.
- GitHub Releases publish zip artifacts and SHA256 checksum files.
- The `RAVN.exe` executable is signed with an Authenticode certificate. If SmartScreen appears, you can safely click "More info" and then "Run anyway". Over time, SmartScreen trust will build. Always verify the downloaded zip against the published SHA256 checksum.

## Documentation

- [DEPENDENCIES.md](DEPENDENCIES.md) — setup, required tools, and troubleshooting
- [PROGRESS.md](PROGRESS.md) — current release status and verified quality snapshot
- [TASKS.md](TASKS.md) — public roadmap and near-term priorities
- [ARCHITECTURE.md](ARCHITECTURE.md) — system overview, runtime layers, and module boundaries
- [docs/phase5f_windows_packaging.md](docs/phase5f_windows_packaging.md) — Windows packaging and release guide

## Development and Testing

```bash
pytest -q
pytest -q tests/test_ui_logic.py
pytest -q tests/test_ui_components.py tests/test_app_builder.py
pytest -q tests/test_config_paths.py tests/test_database_manager.py
```

## License

[MIT](LICENSE)
