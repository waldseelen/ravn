# RAVN

RAVN is a desktop + CLI media application for **acquiring, processing, organizing, and reviewing media**.

- **Desktop runtime:** CustomTkinter
- **CLI runtime:** Click
- **Primary external tools:** FFmpeg / FFprobe, yt-dlp, aria2c
- **Current product state:** Phases 1–4D, Phase 5A, Phase 5B, Phase 5C, Phase 5D, Phase 5E, Phase 6, Phase 7, and Phase 8 are complete
- **Open major area:** Phase 5F build / packaging / distribution follow-up work after the completed Phase 5E optimization closeout

RAVN is no longer just a thin yt-dlp front-end. The project now behaves as a broader **media acquisition + studio + library** system built around shared runners, queue/history persistence, and automatic media-library registration.

## What RAVN Can Do

### 1. Media Acquisition

RAVN can download media from supported online sources through a unified acquisition flow.

Supported acquisition behaviors include:

- a unified smart source bar for URLs, playlists, batches, magnets, and `.torrent` files
- single-URL downloads
- playlist metadata fetch + selective playlist download
- batch downloads from multiline URL lists
- magnet links and `.torrent` files
- torrent download management through aria2
- reusable acquisition presets:
  - `Custom`
  - `Music`
  - `Podcast`
  - `Archive`
  - `Social Clip`

Acquisition features include:

- quality intent selection (`Best`, `1080p`, `720p`, `480p`, audio-only behavior)
- format selection (`MP4`, `WebM`, `MKV`, `MP3`, `M4A`, `AAC`, `FLAC`, `OPUS`, `WAV` depending on flow)
- quality-based size estimation where source metadata allows it
- safe filename templating with tokens such as:
  - `{title}`
  - `{uploader}`
  - `{playlist}`
  - `{upload_date}`
  - `{resolution}`
- naming presets:
  - `standard`
  - `clean`
  - `playlist`
- normalized post-download renaming
- optional auto-sort folder routing by artist/channel metadata
- preferred subtitle language selection
- subtitle fallback language support
- optional auto-generated subtitle fallback
- optional downloader-side subtitle embedding
- post-download automation pipeline:
  - extract audio
  - convert final output
  - embed matching subtitle sidecars
  - preserve original downloaded artifacts
  - hand final outputs to library auto-add
- metadata normalization and enrichment for acquired media
- platform-aware library tags and structured acquisition metadata
- robustness controls:
  - archive-backed duplicate skipping
  - resumable partial downloads
  - fallback format retries
  - optional bandwidth limits
- collapsed advanced acquisition controls:
  - browser-cookie auth handoff
  - `cookies.txt` auth handoff
  - fragment concurrency tuning
  - fragment retry tuning
  - socket timeout tuning

### 2. Playlist Intelligence

Playlist flow is no longer just “download all”. It supports:

- playlist metadata fetch with staged detail enrichment
- sortable review dialog
- checkbox-based partial selection
- range selection
- title filtering
- duration filtering
- popularity-aware filtering when metadata exists
- selected-count and selected-total-size summaries
- quality-aware summary calculations

### 3. Torrent / Magnet Support

Torrent support is a first-class capability.

RAVN supports:

- magnet URI detection
- `.torrent` URL/file detection
- drag-and-drop `.torrent` input when DnD backend is available
- aria2-backed torrent downloading
- torrent queueing from a dedicated UI surface
- torrent modes:
  - `FULL`
  - `SEQUENTIAL`
  - `STREAM`
- pause / resume / complete filtering
- per-session progress and metrics:
  - progress
  - total size
  - downloaded
  - remaining
  - speed
  - ETA
  - peers
  - seeders
- per-file child rows under torrent sessions
- open-in-player behavior with safe fallback to the best available target

### 4. Studio / Processing Tools

RAVN includes a broader FFmpeg-backed studio toolset.

#### Convert

- video/audio format conversion
- codec + quality mapping
- real-time FFmpeg progress reporting
- queue integration
- history persistence
- optional auto-library registration

#### Subtitle

- subtitle download
- subtitle processing
- subtitle embedding
- inline error display through `ErrorPanel`

#### Filters

- FFmpeg-based filter chains
- queue integration
- history persistence
- library auto-add support

#### Mixer

- audio concatenation and mix-style workflows
- video concatenation / composition workflows
- queue integration
- history persistence
- library auto-add support

#### Utilities

RAVN includes a large utility-media helper set in both desktop UI and CLI.

Current utility groups:

- **Quick helpers**
  - remux
  - extract-audio
  - mute
  - trim
  - preview clip
  - thumbnail
- **Audio utilities**
  - volume
  - fade
  - bitrate
  - channels
  - silence-detect
  - loudnorm
- **Video utilities**
  - scale
  - crop
  - pad
  - rotate
  - fps
  - brightness / contrast / saturation
  - blur / sharpen
  - deinterlace
- **Smart helpers**
  - blackdetect
  - scene-preview
  - scene-thumbnail

### 5. Media Library + History

RAVN includes a local SQLite-backed media-library system.

Capabilities include:

- add media to a local library
- automatic registration of supported outputs from:
  - downloads
  - conversions
  - mixer workflows
  - filter workflows
  - utility workflows where applicable
- tags
- collections
- search filters
- duplicate detection
- bounded recent-search history
- JSON export
- CSV export
- large library exports streamed in batches instead of one large in-memory materialization
- persisted history for:
  - downloads
  - conversions
  - generic Phase 7 operations

### 6. Queue, Shell, and UX

The desktop shell was redesigned in Phase 8 and now provides a grouped workspace model.

Primary desktop workspaces:

- `Home`
- `Download`
- `Studio`
- `Library`

Shell capabilities include:

- global right-side Queue panel
- smart download-source routing with manual override when detection should be forced
- lower-left theme toggle
- lower-left language toggle
- lower-left Settings workspace entry
- shell quick actions
- command palette (`Ctrl+K`)
- settings shortcut (`Ctrl+,`)
- dependency-health summary in `Home` and detailed tool status in `Settings`
- progressive-disclosure guidance panels
- mounted workspace switching for lower flicker
- taskbar-aware, active-monitor-aware startup centering on desktop launch
- lighter in-place language refresh
- in-place theme application without full shell rebuild
- adaptive sizing for compact and wide desktop widths
- task-snapshot-driven Home/Queue refreshes where practical instead of fixed high-frequency polling
- in-place Home summary-card updates

Keyboard shortcuts currently active across feature surfaces and shell-level flows include:

- `Ctrl+Enter`
- `Escape`
- `Ctrl+L`
- `Ctrl+K`
- `Ctrl+,`

### 7. CLI Automation

RAVN exposes a shared-core CLI for scripting and automation.

Current CLI commands:

- `download`
- `convert`
- `info`
- `subtitle`
- `history`
- `torrent`
- `mixer`
- `library`
- `filters`
- `utilities`
- `serve` placeholder

The `download` CLI now mirrors the project’s intent-driven acquisition model instead of exposing a raw yt-dlp passthrough surface.

That includes support for:

- acquisition profiles
- naming presets / filename templates
- subtitle preferences
- post-process automation
- robustness controls
- auth/tuning controls
- JSON output with effective acquisition summaries

## Desktop Information Architecture

### Home

- quick-start cards
- recent activity snapshot
- queue/library context
- orientation surface for the app

### Download

- one shared source area for URLs / playlists / batches / torrents
- auto-detected media / playlist / batch / torrent routing with manual override chips
- `Video` / `Audio` output switching on the shared media surface
- torrent manager surface when torrent input is active
- profile-driven acquisition controls
- compact advanced settings via Settings workspace

### Studio

- Convert
- Subtitle
- Filters
- Mixer
- Utilities

### Library

- media library browsing and management
- history review
- export/search-oriented workflows

## Current Status

### Complete

- Phase 1
- Phase 2
- Phase 3
- Phase 4A
- Phase 4B
- Phase 4C
- Phase 4D
- Phase 5A — runtime dependency health / toolchain UX
- Phase 5B — shared-runner convergence / runtime process cleanup
- Phase 5C — UX hardening / scalability investigation
- Phase 5D — codebase cleanup / wrapper / extension-boundary clarity
- Phase 5E — optimization / clean code / dead code cleanup
- Phase 6
- Phase 7
- Phase 8
- yt-dlp acquisition-engine upgrade tasks `YTD-01` through `YTD-11`

### Open

- Phase 5F build / packaging / distribution follow-up track

## Technology Stack

### Application

- Python 3.9+
- CustomTkinter
- Click
- SQLite

### External Tools

- FFmpeg / FFprobe
- yt-dlp
- aria2c

### Optional / graceful-degradation pieces

- `tkinterdnd2` for drag-and-drop
- optional metadata-related runtime paths where available

## Repository Layout

```text
ravn.py
setup.py
build.ps1
ravn.spec
ravn_app/
  cli.py
  core/
    runners/
    persistence/
    config_paths.py
    database.py
    downloader.py
    converter.py
    subtitle_manager.py
    torrent_downloader.py
    media_helpers.py
    download_naming.py
    download_profiles.py
    download_metadata.py
    task_manager.py
    i18n.py
    logging_config.py
    theme_catalog.py
    app_builder.py
  ui/
    main_window.py
    converter_tab.py          # legacy-compatible implementation module
    download_tab.py           # legacy-compatible alias to ui/tabs/download_tab.py
    history_settings_tab.py   # shared legacy-compatible implementation module
    subtitle_tab.py           # legacy-compatible implementation module
    queue_panel.py
    components/
    tabs/                     # canonical desktop feature import surfaces
  translations/
    en.json
    tr.json
  utils/
    ffmpeg_checker.py
    metadata_handler.py
    system_utils.py
tests/
docs/
tools/
  phase5e_benchmarks.py
```

Desktop feature note:

- `ravn_app.ui.tabs.*` is the canonical import namespace for active desktop feature modules.
- Legacy `ravn_app.ui.*` feature modules are retained only as compatibility surfaces where noted above.
- `ravn_app.core.plugin_system` is experimental only and is not auto-loaded by the desktop app or CLI.

## Requirements

**For detailed dependency information, installation instructions, and troubleshooting, see [DEPENDENCIES.md](DEPENDENCIES.md).**

### Quick Overview

**Required:**

- Python 3.9+
- FFmpeg and FFprobe (for video/audio processing)
- yt-dlp (for media downloads)
- Python packages from `requirements.txt`

**Optional:**

- aria2c (for torrent/magnet support)
- tkinterdnd2 (for drag-and-drop functionality)

Examples:

```bash
pip install -r requirements.txt
```

Torrent prerequisite examples:

```bash
winget install aria2
brew install aria2
sudo apt install aria2
```

**Tool Health Check:**

RAVN includes built-in dependency checking. After launch, check Settings (Ctrl+,) → "Tool Status and Dependencies" to see which tools are available and which features require missing tools.

## Run

### Desktop

```bash
python ravn.py
```

Alternative module form:

```bash
python -m ravn_app.ui.main_window
```

### Install editable package

```bash
pip install -e .
```

### CLI examples

Acquisition examples:

```bash
python -m ravn_app.cli download "https://example.com/video" --profile archive --subtitle-lang en --postprocess-embed-subtitles --json
python -m ravn_app.cli download "https://example.com/channel/track" --profile music --extract-audio --convert-to m4a --output ./downloads
python -m ravn_app.cli download "https://example.com/video" --profile social-clip --format mp4 --quality 720p
python -m ravn_app.cli download "https://example.com/video" --cookies-from-browser firefox --cookies-profile Default --json
```

Other CLI examples:

```bash
python -m ravn_app.cli convert input.mp4 --format mkv --quality high
python -m ravn_app.cli torrent "magnet:?xt=urn:btih:..." --sequential
ravn mixer audio --input intro.mp3 --input main.mp3 --crossfade 1.5 --output merged.mp3
ravn mixer video clip1.mp4 clip2.mp4 --operation concat --output combined.mp4
ravn library add ./video.mp4 --title "My Video" --tags work,tutorial
ravn library search --query video --format mp4 --tags tutorial --json
ravn filters input.mp4 --brightness 20 --contrast 1.2 --blur 2 --output filtered.mp4
ravn utilities input.mp4 --operation thumbnail --output thumb.jpg
```

## Testing

Verified on 2026-04-05:

- Full baseline:
  - `pytest -q`
  - `633 passed, 1 skipped` (`634` collected)
- Required UI logic sweep:
  - `pytest -q tests/test_ui_logic.py`
  - `87 passed`
- Required UI components + builder sweep:
  - `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
  - `37 passed`
- Required config/database sweep:
  - `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
  - `58 passed`
- Targeted Phase 5E optimization sweep:
  - `pytest -q tests/test_media_library.py tests/test_library_sync.py tests/test_task_manager.py tests/test_database_manager.py tests/test_ui_logic.py`
  - `145 passed`
- Phase 5E benchmark harness:
  - `python tools/phase5e_benchmarks.py --output docs/phase5e_benchmark_results.json`
  - benchmark artifact refreshed successfully

Useful commands:

```bash
pytest
pytest -q --tb=no
pytest --collect-only -q
pytest tests/test_ui_logic.py -q
```

## Build / Packaging Reality

Build/distribution work exists but is **not finished**.

Current repo artifacts include:

- `build.ps1`
- `ravn.spec`
- `ravn_app/core/app_builder.py`

However, Phase 5 remains open. Current packaging work should be treated as a **Windows-first release track** after runtime hardening, dependency UX, and remaining architecture cleanup are in acceptable shape.

## Documentation Map

- `AGENTS.md` — canonical shared agent workflow guide
- `CLAUDE.md` — Claude-oriented repo entrypoint and condensed engineering guidance
- `ARCHITECTURE.md` — full system structure, runtime flows, and module map
- `PROGRESS.md` — validated implementation snapshot
- `TASKS.md` — backlog, hardening roadmap, and Phase 5 Windows release plan
- `OPTIMIZATIONS.md` — completed Phase 5E optimization / cleanup checklist
- `docs/phase5b_subprocess_audit.md` — shared-runner convergence audit and subprocess classification record
- `docs/phase5e_optimization_baseline.md` — first landed Phase 5E optimization slice, evidence, and deliberate non-changes
- `docs/phase5e_dead_code_audit.md` — Phase 5E dead-code / wrapper audit closeout
- `docs/phase5e_benchmark_closeout.md` — repeatable benchmark methodology and measured closeout summary
- `docs/phase5e_benchmark_results.json` — raw Phase 5E benchmark artifact
- `docs/phase5c_ux_scalability.md` — UX hardening, hotspot measurements, and scalability mitigation record
- `docs/phase5d_wrapper_boundary_clarity.md` — canonical desktop import surfaces, wrapper inventory, and experimental plugin-boundary decision

## Current Priorities

1. Complete the remaining Windows-only Phase 5 packaging/release pipeline.
2. Maintain and harden the completed workspace shell, acquisition pipeline, staged playlist metadata flow, media-library flows, dependency-health UX, shared-runner boundaries, canonical desktop import surfaces, and measured list-heavy UI paths.
3. Use the completed Phase 5E docs/benchmarks as the optimization baseline for packaging validation.
4. Avoid reintroducing parallel execution paths or implying unsupported plugin behavior.
