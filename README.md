# RAVN

RAVN is a desktop + CLI media application for **acquiring, processing, organizing, and reviewing media**.

- **Desktop runtime:** CustomTkinter
- **CLI runtime:** Click
- **Primary external tools:** FFmpeg / FFprobe, yt-dlp, aria2c
- **Current product state:** Phases 1–4C, Phase 6, Phase 7, and Phase 8 are complete
- **Open major area:** Phase 5 build / packaging / distribution

RAVN is no longer just a thin yt-dlp front-end. The project now behaves as a broader **media acquisition + studio + library** system built around shared runners, queue/history persistence, and automatic media-library registration.

## What RAVN Can Do

### 1. Media Acquisition

RAVN can download media from supported online sources through a unified acquisition flow.

Supported acquisition behaviors include:

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

- playlist metadata fetch
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
- JSON export
- CSV export
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
- lower-left theme toggle
- lower-left language toggle
- lower-left Settings workspace entry
- shell quick actions
- command palette (`Ctrl+K`)
- settings shortcut (`Ctrl+,`)
- progressive-disclosure guidance panels
- mounted workspace switching for lower flicker
- lighter in-place language refresh
- in-place theme application without full shell rebuild
- adaptive sizing for compact and wide desktop widths

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
- URL / playlist / batch acquisition
- torrent manager surface
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
- Phase 6
- Phase 7
- Phase 8
- yt-dlp acquisition-engine upgrade tasks `YTD-01` through `YTD-11`

### Open
- Phase 5 build / packaging / distribution

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
    history_settings_tab.py
    queue_panel.py
    components/
    tabs/
  translations/
    en.json
    tr.json
  utils/
    ffmpeg_checker.py
    metadata_handler.py
    system_utils.py
tests/
docs/
```

## Requirements

- Python 3.9+
- FFmpeg and FFprobe on `PATH`
- `aria2c` installed separately for torrent/magnet support
- packages from `requirements.txt`

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

Verified on 2026-04-03:

- Full baseline: `pytest -q` -> `578 passed, 1 skipped` (579 collected)
- Targeted CLI + acquisition regression sweep:
  - `pytest -q tests/test_cli.py tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_runners.py`
  - `245 passed, 1 skipped`
- Targeted acquisition-engine regression sweep:
  - `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_runners.py`
  - `206 passed, 1 skipped`
- Targeted playlist/download regression sweep:
  - `pytest -q tests/test_ui_logic.py tests/test_runners.py`
  - `147 passed`
- Targeted download/settings regression sweep:
  - `pytest -q tests/test_core.py tests/test_ui_logic.py tests/test_config_paths.py tests/test_database_manager.py`
  - `137 passed, 1 skipped`
- Targeted UI/i18n/design-token regression sweep:
  - `pytest -q tests/test_utilities_tab.py tests/test_i18n_and_design_tokens.py tests/test_ui_logic.py tests/test_ui_components.py tests/test_app_builder.py`
  - `108 passed`

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

However, Phase 5 remains open. Packaged delivery, bundled runtime validation, and distribution hardening should still be treated as in-progress work.

## Documentation Map

- `AGENTS.md` — canonical shared agent workflow guide
- `CLAUDE.md` — Claude-oriented repo entrypoint and condensed engineering guidance
- `ARCHITECTURE.md` — full system structure, runtime flows, and module map
- `PROGRESS.md` — validated implementation snapshot
- `TASKS.md` — backlog and task status board
- `DEPLOY.md` — current packaging/distribution reality and Phase 5 checklist
- `docs/phase8_ux_navigation_overhaul.md` — historical/approved Phase 8 shell plan

## Current Priorities

1. Finish Phase 5 packaging and distribution work.
2. Validate bundled FFmpeg/runtime behavior in clean installer environments.
3. Continue migrating auxiliary direct `subprocess` usage toward shared runners where practical.
4. Maintain and harden the completed workspace shell, acquisition pipeline, and media-library flows.
