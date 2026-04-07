# Release Status

Verified on 2026-04-07.

RAVN is an actively maintained **Windows-first desktop + CLI media product**. The core experience is already in place: download, processing, organization, and automation workflows all run through the current shared runtime. The main remaining release work is final packaged-app validation and trust/signing polish for Windows distribution.

## Product snapshot

### Download and acquisition
- Single URL, playlist, batch, magnet, and `.torrent` flows are available.
- Playlist review supports filtering, selection, and range-based download.
- Download profiles, naming presets/templates, subtitle preferences, metadata enrichment, and post-download automation are active.
- Tool-health checks explain which features are affected when dependencies are missing.

### Processing and studio tools
- Conversion, subtitle embed, filters, mixer, and utility workflows are available in the desktop app.
- The CLI exposes matching media-processing surfaces for scripting.
- FFmpeg real-time progress parsing is active.
- Inline error presentation is in place for the most failure-prone studio surfaces.

### Library, history, and queue
- Queue infrastructure is active through `ravn_app/core/task_manager.py`.
- History persists downloads, conversions, and other media operations.
- The local media library supports search, tags, collections, statistics, and export.
- Successful supported outputs can auto-register into the media library.

### Desktop and CLI runtime
- Desktop workspaces are grouped into `Home`, `Download`, `Studio`, and `Library`.
- Queue is exposed as a shared panel instead of a top-level workspace.
- Settings, theme, and language controls are integrated directly into the shell.
- The CLI supports `download`, `convert`, `info`, `subtitle`, `history`, `torrent`, `mixer`, `library`, `filters`, and `utilities`.

### Platform and packaging
- Windows packaged builds are the primary distribution target.
- Packaged Windows builds support bundled FFmpeg/FFprobe lookup.
- GitHub Actions packaging and tagged-release workflows are in place.
- Linux and macOS source usage may work, but packaged releases are not currently maintained for those platforms.

## Quality snapshot

Latest automated verification run:

- `pytest -q`
- `644 passed, 1 skipped`

Observed on 2026-04-07.

## Current release focus

The remaining public release polish is concentrated in a short list:

- validate packaged behavior on a clean Windows machine / VM
- tighten signing and release-trust guidance for Windows distribution
- keep docs, screenshots, and onboarding material aligned with repository reality

## Explicit scope notes

- `ffmpeg`, `ffprobe`, and `yt-dlp` are core dependencies.
- `aria2c` is optional and only required for torrent and magnet workflows.
- `plugin_system.py` is experimental and is not part of the active packaged runtime.
- The `serve` CLI command remains a placeholder, not a public product feature.

## Documentation map

- [README.md](README.md) — product overview and quick start
- [TASKS.md](TASKS.md) — public roadmap and near-term priorities
- [ARCHITECTURE.md](ARCHITECTURE.md) — system structure and runtime boundaries
- [DEPENDENCIES.md](DEPENDENCIES.md) — setup and troubleshooting
- [docs/phase5f_windows_packaging.md](docs/phase5f_windows_packaging.md) — Windows packaging and release guide
