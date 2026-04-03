# Phase 8 — UX / Information Architecture / Navigation Overhaul

Status: Implemented and validated Phase 8 shell plan
Last updated: 2026-04-01

## Goal

Keep all existing RAVN power features while reducing top-level navigation overload.
The application should feel easier to learn, faster to navigate, and more accessible without removing advanced workflows.

## Current Shell Baseline

Current top-level navigation in `ravn_app/ui/main_window.py` is tab-heavy and exposes feature modules directly:

- Download
- Convert
- Subtitle
- Torrent
- Mixer
- Filters
- Library
- Queue
- History
- Settings

This mirrors implementation boundaries well, but it is no longer the best fit for user intent now that the app has grown into a multi-workflow media tool.

## Approved Target Direction

Adopt **Option A** as the new desktop shell direction:

- Left sidebar for primary workspaces
- Header actions for queue / notifications / quick actions
- Main workspace content area in the center
- Right-side drawers/panels for queue and settings
- Bottom-right circular Settings FAB
- Fewer top-level destinations, with grouped internal subviews

## Target Information Architecture

### 1. Home

Purpose:
- First-run orientation
- Quick entry into common workflows
- Surface recent activity and app status

Planned content:
- Quick-start cards
  - Paste URL
  - Add torrent
  - Convert file
  - Apply filters
  - Scan folder into library
- Recent history snapshot
- Queue snapshot
- Recent library additions
- Optional environment/tool status summary (FFmpeg / aria2 / yt-dlp)

Primary source modules to reuse:
- `ravn_app/core/database.py`
- `ravn_app/ui/queue_panel.py`
- `ravn_app/core/persistence/media_library.py`

### 2. Download Workspace

Purpose:
- Anything that means “I want to acquire media” lives here

Internal subviews:
- URL
- Playlist
- Batch
- Torrent

Current modules to fold in:
- `ravn_app/ui/tabs/download_tab.py`
- `ravn_app/ui/tabs/torrent_tab.py`

Migration notes:
- Preserve current magnet / `.torrent` detection behavior
- Preserve `FULL`, `SEQUENTIAL`, `STREAM` semantics
- Keep batch queue integration
- Keep playlist sort dialog and selected total-size summary
- Prefer one shared top action area and reuse existing specialized sections internally

### 3. Studio Workspace

Purpose:
- Anything that means “I already have media; now I want to process it” lives here

Internal subviews:
- Convert
- Subtitle
- Filters
- Mixer

Current modules to fold in:
- `ravn_app/ui/converter_tab.py`
- `ravn_app/ui/subtitle_tab.py`
- `ravn_app/ui/tabs/filters_tab.py`
- `ravn_app/ui/tabs/mixer_tab.py`

Migration notes:
- Keep existing task-queue wiring
- Preserve `ErrorPanel` usage where already integrated
- Normalize CTA placement and advanced-settings disclosure patterns across all Studio tools
- Avoid duplicating runner logic; this is a shell/layout consolidation task

### 4. Library Workspace

Purpose:
- Everything related to stored outputs, browsing, reviewing, and managing media history lives here

Internal subviews:
- Library
- History
- Collections / Tags
- Recent outputs / management surfaces as needed

Current modules to fold in:
- `ravn_app/ui/tabs/library_tab.py`
- `ravn_app/ui/history_settings_tab.py` (`HistoryTab` only)

Migration notes:
- Preserve queue/history persistence visibility
- Preserve media-library auto-add expectations
- Keep high-contrast list/table behavior
- Keep search/filter flows easy to reach

## Global Shell Elements

### Sidebar

Primary navigation destinations:
- Home
- Download
- Studio
- Library

Rules:
- Icon + label together
- Strong active-state contrast
- Keyboard focus order must match visual order
- Keep widths stable to avoid layout jumping

### Header Actions

Planned global actions:
- Paste URL
- Select File
- Add Torrent
- Scan Folder
- Open Queue
- Notifications entry point (if enabled)

Rules:
- High-frequency actions only
- Do not turn the header into a second crowded toolbar
- Keep button hierarchy visually clear

### Queue Drawer

Target behavior:
- Queue is globally accessible from every workspace
- Opens from header action or keyboard shortcut
- Uses badge counts for pending/running work
- Reuses queue visualization primitives instead of re-implementing queue logic

Current source modules to reuse:
- `ravn_app/ui/queue_panel.py`
- `ravn_app/ui/tabs/queue_tab.py` (migration wrapper; likely removable later)

Must preserve:
- queued / running / completed visibility
- cancel action
- open-folder action
- persistence-backed task visibility

### Settings FAB + Drawer

Target behavior:
- Circular settings button pinned bottom-right
- Opens compact settings drawer or sheet
- Settings content remains single-page and scrollable
- Add keyboard shortcut such as `Ctrl+,`

Current source modules to reuse:
- `ravn_app/ui/history_settings_tab.py` (`SettingsTab`)
- `ravn_app/ui/tabs/settings_tab.py` wrapper

Must preserve:
- compact single-page settings layout
- theme normalization rules
- language switch support
- current config persistence behavior

### Command Palette

Target shortcut:
- `Ctrl+K`

Planned actions:
- Open Home / Download / Studio / Library
- Open Queue
- Open Settings
- Start common actions such as add torrent, convert file, scan library

Rules:
- Fast keyboard-first navigation
- Readable command labels
- Must remain optional; no core flow should depend on it

## Mapping Table

| Current Top-Level Surface | Target Location |
|---|---|
| Download | Download workspace |
| Torrent | Download workspace |
| Convert | Studio workspace |
| Subtitle | Studio workspace |
| Filters | Studio workspace |
| Mixer | Studio workspace |
| Library | Library workspace |
| History | Library workspace |
| Queue | Global queue drawer/panel |
| Settings | Global FAB + settings drawer |

## Shell Composition Strategy

The Phase 8 work should stay modular and reuse existing feature frames where possible.

### Recommended shell split

- `main_window.py`
  - sidebar
  - header actions
  - workspace host area
  - queue drawer host
  - lower-left utility area for theme/language toggles and Settings workspace access
  - command palette trigger wiring
- new workspace containers under `ravn_app/ui/tabs/` or `ravn_app/ui/workspaces/`
  - `home_workspace.py`
  - `download_workspace.py`
  - `studio_workspace.py`
  - `library_workspace.py`
- existing feature frames remain the feature implementation layer

### Migration preference

Prefer:
1. wrap and compose existing feature frames
2. normalize layout/headers/actions at the workspace level
3. only extract shared UI pieces when duplication becomes obvious

Avoid:
- rewriting feature logic just to change navigation
- mixing runner/business logic into the shell
- adding parallel implementations for the same workflow

## Accessibility Requirements

Phase 8 must raise accessibility, not just visual polish.

Minimum requirements:
- 44x44 minimum target size for clickable controls
- visible focus rings on all keyboard-reachable controls
- drawer focus management and predictable escape/close behavior
- icon-only controls require tooltips and accessible labeling
- active state must not rely on color alone
- strong table/list contrast and readable row height
- keyboard traversal order must match visible layout order
- reduced-motion expectations must be respected

## Layout Requirements

- Avoid unnecessary full-width stretching for dense forms
- Use bounded content widths inside wide windows
- Keep drawers stable and non-jumpy while resizing
- Support existing desktop minimum sizes while degrading gracefully
- Avoid reintroducing horizontal scroll in standard workflows

## i18n / Theme / Behavior Guardrails

- New labels, tooltips, empty states, and actions must be translation-key based
- Add keys in both `ravn_app/translations/tr.json` and `ravn_app/translations/en.json`
- Theme IDs remain strict `dark` / `light`
- Legacy theme aliases remain normalization-only, not new themes
- No regression to queue persistence, history persistence, or media-library auto-add behavior

## Implementation Order

1. Build/land this planning spec
2. Refactor shell scaffolding in `main_window.py`
3. Add Home workspace
4. Move Queue to drawer
5. Move Settings to FAB + drawer
6. Merge Download + Torrent into Download workspace
7. Merge Convert + Subtitle + Filters + Mixer into Studio workspace
8. Merge Library + History into Library workspace
9. Add quick actions
10. Add command palette
11. Run accessibility/layout pass
12. Update tests and docs

## Verification Focus For Phase 8

At minimum, verify:
- workspace switching works by mouse and keyboard
- queue drawer remains accessible from every workspace
- settings drawer opens from FAB and shortcut
- merged Download workspace still handles URL / playlist / batch / torrent correctly
- Studio workspace preserves queue-backed operations and error reporting
- Library workspace still exposes history and media management clearly
- no regression in i18n/theme behavior
- no regression in queue/history persistence integration

## Notes For Future Implementation Tasks

- Repository reality now matches the approved shell direction: `main_window.py` exposes sidebar workspaces (`Home`, `Download`, `Studio`, `Library`), header-aligned quick actions, a global queue side panel, an independent lower-left settings entry that opens a dedicated settings workspace, a global `Ctrl+K` command palette, workspace-level collapsed guide panels for progressive disclosure, accessibility-focused shell controls, adaptive shell sizing, full library i18n coverage, and a lower-flicker mounted-workspace shell transition model
- Phase 8 tasks are complete in `TASKS.md`; future work should be treated as follow-up refinement rather than shell migration
- This document remains useful as both the approved design intent and a reference for the implemented shell model
