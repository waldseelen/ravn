# UX Hardening and Scalability Notes

Verified on 2026-04-05.

This document records the UX hardening and evidence-driven scalability work completed for the current release track.

## Goal

Improve perceived stability on realistic desktop sizes and investigate scaling risks with measurements before applying optimization.

---

## Documented Work

- `UX-REL-01` — Download workspace layout behavior hardened for tighter desktop heights
- `PERF-01` — Large-playlist stress verification added for Download workspace + playlist dialog logic
- `PERF-02` — Large-library stress verification added for library browsing/search rendering
- `PERF-03` — Many-row torrent-session stress verification added for session/filter behavior with child rows
- `PERF-04` — UI render/filter hotspots measured via lightweight runtime perf metrics
- `PERF-05` — Smallest adequate mitigations applied where measurements justified them

---

## UX Hardening Changes

### Download workspace adaptive profile

`ravn_app/ui/tabs/download_workspace.py`

Added a compact-height workspace profile that activates on shorter desktop heights.

Behavior:
- collapses the guide panel automatically on compact heights
- forwards height information to the standard download surface
- keeps workspace switching stable across URL / playlist / batch / torrent modes

### Download tab adaptive controls

`ravn_app/ui/tabs/download_tab.py`

Added `apply_layout_profile()` to adjust:
- playlist panel scroll height
- batch URL textbox height
- column spacing

This reduces the chance that dense download states feel clipped or over-tall on typical desktop heights.

---

## Measured Hotspots

Lightweight perf metrics are now captured in `_perf_metrics` for relevant UI surfaces.

### 1. Download playlist inline rendering

`ravn_app/ui/tabs/_download_playlist.py`

Metric:
- `playlist_inline_render`

Captured data:
- item count
- duration in ms
- whether chunked rendering was used
- batch count

### 2. Playlist dialog filtering and tree refresh

`ravn_app/ui/components/playlist_sort_dialog.py`

Metrics:
- `playlist_filter_rows`
- `playlist_refresh_tree`

Captured data:
- source row count
- visible row count
- duration in ms
- popularity mode for filtered runs

### 3. Library result rendering

`ravn_app/ui/tabs/library_tab.py`

Metric:
- `library_results_render`

Captured data:
- item count
- duration in ms
- whether chunked rendering was used
- batch count

### 4. Torrent session filtering

`ravn_app/ui/tabs/torrent_tab.py`

Metric:
- `torrent_session_filter`

Captured data:
- session count
- file row count
- active filter
- duration in ms

---

## Applied Mitigations

These were chosen as the smallest architecture-aligned changes instead of jumping to virtualization.

### Chunked rendering for large playlist inline lists

Threshold-based chunking now applies when inline playlist rendering is used with large item counts.

Why:
- avoids one large burst of widget creation
- keeps UI more responsive during large playlist population

### Chunked rendering for large library result lists

Library results now render in batches for large result sets.

Why:
- library cards are widget-heavy
- chunking reduces synchronous UI work during large result refreshes

### O(n) torrent child-row filtering

Torrent session filtering now pre-groups child rows by parent session before applying queue-state filters.

Why:
- avoids repeated full scans of file rows per session
- reduces filter work for many-session / many-child-row states

---

## Deliberate Non-Changes

The following were intentionally not added because measurements did not justify them yet:

- full visible-row virtualization
- paging as a mandatory default for standard lists
- shell-wide rewrite for list rendering
- speculative optimizations outside identified hotspots

---

## Verification

Key verification commands used for this work:

- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
- `pytest -q tests/test_utilities_tab.py tests/test_i18n_and_design_tokens.py tests/test_ui_logic.py`
- `pytest -q`

Validated baseline at the time of this document:

- full suite: `614 passed, 1 skipped`

---

## Outcome

This work is complete.

The project now has:
- stronger compact-height behavior in the Download workspace
- explicit stress verification for large playlist/library/torrent states
- built-in hotspot measurements for the riskiest list-heavy UI paths
- measured, minimal mitigations instead of premature over-engineering

Later follow-up work moved into wrapper cleanup, optimization, and packaging polish. See `TASKS.md` for the current roadmap.
