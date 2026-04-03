# RAVN — Project Task Board

All development tasks organized by priority and status.
﻿Read AGENT.md, CLAUDE.md , ARCHITECTURE.md, README.md and PROGRESS.md first. Treat them as one
unified instruction set and follow all rules, constraints, and context strictly.

Then execute TASKS.md as the single source of truth. Only complete tasks marked \[ ]. Never touch
or redo tasks marked \[x].

Do not deviate from scope, structure, or intent. If any conflict occurs, follow the most recent
and most specific instruction.

After completing all eligible tasks, update AGENT.md, CLAUDE.md, and PROGRESS.md briefly and
accurately based on this session.

## Patch Proposal — Utility Media Helpers / Smart Helpers

This proposal fits the current architecture well and should land as a **core Studio capability**, not as a disconnected side feature. The cleanest direction is to keep it inside the grouped `Studio` workspace and expose it through shared runner-backed utility actions/presets rather than adding more top-level navigation.

### Product Direction

Group the proposal into four implementation buckets:

- **Quick Helpers**
  - remux
  - audio extract
  - mute
  - trim
  - preview clip
  - thumbnail

- **Audio Utility**
  - volume
  - fade
  - bitrate / sample rate
  - mono / stereo
  - silence detect / remove
  - loudnorm

- **Video Utility**
  - scale
  - crop
  - pad
  - rotate
  - fps
  - brightness / contrast / saturation
  - blur / sharpen
  - deinterlace

- **Smart Helpers**
  - blackdetect
  - scene-based preview / thumbnail generation

### Recommended Placement

- Keep these capabilities under **Studio** as utility-oriented tools/presets
- Reuse `FFmpegRunner`, `VideoMixerRunner`, `AudioMixerRunner`, and existing filter/mixer patterns where possible
- Avoid creating new top-level tabs; prefer segmented utility panels, preset cards, or a dedicated Studio subview
- Keep outputs queueable where work is non-trivial and auto-library registration compatible when files are generated

### Proposed Execution Patch

- \[x] **\[UTL-01]** Design the Studio-side information architecture for utility helpers: decide whether these ship as a dedicated `Utilities` Studio subview, grouped preset cards inside existing `Filters` / `Mixer`, or a hybrid utility shell; document the mapping before implementation
- \[x] **\[UTL-02]** Add shared core helper APIs for quick FFmpeg jobs (remux, extract-audio, mute, trim, preview clip, thumbnail) using existing runner abstractions instead of one-off subprocess calls
- \[x] **\[UTL-03]** Add audio utility operations (volume, fade, bitrate/sample-rate conversion, mono/stereo conversion, silence detect/remove, loudnorm) with reusable parameter normalization and result metadata
- \[x] **\[UTL-04]** Add video utility operations (scale, crop, pad, rotate, fps, brightness/contrast/saturation, blur/sharpen, deinterlace) as composable runner-backed operations aligned with current filter/mixer architecture
- \[x] **\[UTL-05]** Add smart helper operations for `blackdetect` and scene-based preview/thumbnail generation, including output file conventions and user-readable summaries
- \[x] **\[UTL-06]** Integrate the new helpers into the desktop **Studio** workspace with compact progressive-disclosure UI, queue support where appropriate, and no new top-level navigation overload
- \[x] **\[UTL-07]** Extend CLI coverage so the same utility helpers are scriptable from `ravn`, with consistent flags, JSON output support where appropriate, and README examples
- \[x] **\[UTL-08]** Support persistence/history/library integration: store generated utility operations in generic `operations` history and auto-register generated outputs into `MediaLibrary` when enabled
- \[x] **\[UTL-09]** Add/update tests for helper argument building, runner integration, CLI behavior, queue/history persistence, and Studio workspace rendering/interaction paths
- \[x] **\[UTL-10]** Update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and translations when implementation begins so utility/smart-helper behavior matches repository reality

### Guardrails

- Do **not** introduce new top-level navigation areas for these helpers
- Do **not** bypass shared runners with new ad-hoc subprocess paths
- Do **not** regress current Studio grouping (`Convert`, `Subtitle`, `Filters`, `Mixer`)
- Do **not** hardcode user-facing labels outside TR/EN translation keys
- Prefer composable helper primitives over a large number of one-off UI screens

## Patch Proposal — yt-dlp Acquisition Engine Upgrade

This proposal is high-value and aligns extremely well with the current architecture. The right direction is **not** to expose more raw `yt-dlp` flags; it is to turn the current downloader into an intent-driven acquisition pipeline that plugs into queue/history/library flows.

### Why This Fits RAVN

- It strengthens an existing core path instead of adding unrelated surface area
- It fits the current `runner + queue + library` architecture naturally
- It increases value without forcing heavy CPU/RAM usage when implemented as smart presets and lightweight metadata/pipeline steps
- It moves RAVN from “downloader UI” toward a real **media acquisition + processing pipeline**

### Recommended Product Shape

Prioritize intent-driven features over raw flag exposure:

- **Smart download intents** instead of codec-first choices
- **Playlist intelligence** instead of only bulk fetch/download
- **Naming + metadata normalization** before/after acquisition
- **Post-process automation** into existing FFmpeg / subtitle / library systems
- **Robustness controls** (retry, archive, duplicate detection, fallback)

### Highest-ROI Scope

- **Smart format selector**
  - Best Quality
  - Small Size
  - Audio Only
  - Balanced

- **Playlist partial download**
  - checkbox selection
  - range selection
  - title / duration / popularity filters

- **Filename templating**
  - `{title}`
  - `{uploader}`
  - `{playlist}`
  - `{upload\_date}`
  - `{resolution}`
  - preset naming schemes

- **Auto post-processing pipeline**
  - extract audio
  - convert
  - subtitle embed
  - rename
  - library add

- **Subtitle automation upgrade**
  - preferred language
  - fallback language behavior
  - auto embed

### Medium-Term Value Additions

- metadata enrichment / normalization
- download profiles
- rate limit / bandwidth control
- retry + failure handling
- cookies / auth support
- archive system
- duplicate detection
- multi-source format fallback

### Controlled Advanced Features

- fragment / chunk tuning
- live stream recording
- scene-aware or metadata-aware acquisition helpers when scope allows

### Existing Baseline (already present / partially implemented)

- Download flow already has quality/format mapping and size estimation (`Best`, `1080p`, `720p`, `480p`, audio-only style behavior)
- Playlist flow already supports fetch, checkbox selection, selection summary, and sortable dialog-based review
- `YtDlpRunner` already has retry behavior and low-level `filename\_template` support
- `YouTubeDownloader` already supports audio extraction, audio metadata embedding, and auto-sort by artist/channel folders
- Download outputs can already auto-register into `MediaLibrary`
- Config/settings already include `auto\_subtitle\_download` and `preferred\_subtitle\_language`, but they are not yet a full downloader-side subtitle automation pipeline

### Proposed Execution Patch

- [ ] **[YTD-01]** Add filename templating + naming presets that build on the current fixed `%(title)s.%(ext)s` baseline and existing auto-sort support; include safe token expansion, sanitization, and preset examples such as standard, clean, and playlist-structured naming
- [ ] **[YTD-02]** Extend playlist workflow with partial-download intelligence beyond the current checkbox/sort baseline: add range download plus title/duration filtering and optional popularity-based filtering where source metadata allows it
- [ ] **[YTD-03]** Upgrade downloader-side subtitle automation using the existing config baseline: preferred-language selection, fallback logic, optional auto-download, and optional auto-embed behavior coordinated with `SubtitleTab` and existing settings
- [ ] **[YTD-04]** Add a post-download automation pipeline that chains into existing capabilities (audio extract, convert, subtitle embed, rename, library add) using current runners/task/history infrastructure instead of separate ad-hoc flows
- [ ] **[YTD-05]** Add metadata enrichment/normalization for acquired media on top of the current metadata embedding helpers: title cleanup, uploader normalization, extra tags, and persisted structured metadata suitable for `MediaLibrary`
- [ ] **[YTD-06]** Add reusable download profiles (for example music, podcast, archive, social clip) that bundle format intent, naming, output path, post-process, and subtitle behavior into one-click presets
- [ ] **[YTD-07]** Improve robustness controls beyond the current retry baseline: fallback format selection, partial recovery behavior, archive tracking, duplicate detection, and optional bandwidth/rate-limit controls appropriate for queue-based desktop use
- [ ] **[YTD-08]** Add advanced-but-collapsed acquisition settings for cookies/auth, fragment tuning, and similar power-user controls without regressing the simplified default Download UX
- [ ] **[YTD-09]** Extend CLI support so the same acquisition concepts are scriptable from `ravn` with consistent flags/presets and JSON output where appropriate, rather than merely mirroring raw `yt-dlp` flags one-to-one
- [ ] **[YTD-10]** Add/update tests for filename templating, playlist filtering/range behavior, subtitle automation, post-process chaining, retry/archive/duplicate handling, metadata persistence, and Download workspace interactions
- [ ] **[YTD-11]** When implementation begins, update `README.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and translations so the downloader is documented as an intent-driven acquisition pipeline rather than only a thin `yt-dlp` front-end

### Guardrails

- Do **not** turn the default Download UI into a raw `yt-dlp` flag dump
- Do **not** regress current URL / Playlist / Batch / Torrent grouping in the Download workspace
- Do **not** bypass shared runners/task/history/library integration for post-processing behavior
- Do **not** over-allocate CPU/RAM with unnecessary prefetch/analysis steps for ordinary downloads
- Prefer presets, templates, and automation over exposing every upstream flag directly

### Implementation Notes (keep the first slice easy)

- Start with a **thin intent-to-options mapper** in core download code instead of spreading logic across UI callbacks.
- Add a small typed config/preset shape first, for example:
  - `download\_intent`
  - `naming\_preset`
  - `postprocess\_profile`
  - `subtitle\_profile`

- Keep UI labels simple and map them internally to `yt-dlp` format strings / options.
- Reuse the existing playlist dialog instead of building a second playlist screen.
- Implement filename templates as a small helper module with:
  - token expansion
  - filename sanitization
  - preset definitions

- Model post-download automation as an ordered pipeline of small steps rather than one giant conditional block.
- Prefer extending `YtDlpRunner` and `downloader.py` with composable option builders rather than adding new downloader classes immediately.
- Persist new behavior through existing config/history/media-library paths before adding new storage surfaces.
- Keep advanced options behind collapse/disclosure UI and expose only the intent presets by default.
- Land in slices:
  1. preset mapping
  2. filename templates
  3. playlist partial selection/filtering
  4. post-process chaining
  5. retry/archive/duplicate logic

### Suggested Code Placement

- `ravn\_app/core/downloader.py`
  - intent mapping
  - preset resolution
  - orchestration of post-download pipeline

- `ravn\_app/core/runners/ytdlp.py`
  - low-level option/command construction
  - retry/archive/cookies/rate-limit argument support

- `ravn\_app/ui/tabs/download\_tab.py`
  - simple preset-driven controls
  - collapsed advanced options

- `ravn\_app/ui/tabs/download\_workspace.py`
  - keep mode routing only; avoid pushing heavy business logic here

- `ravn\_app/core/database.py`
  - persist generic operation/download metadata only if needed

- `ravn\_app/core/persistence/library\_sync.py`
  - reuse for auto-add after post-processing

- `ravn\_app/translations/tr.json` + `ravn\_app/translations/en.json`
  - new labels, preset names, and helper descriptions

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
