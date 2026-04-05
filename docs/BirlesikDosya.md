# Phase 5B — Shared-Runner Convergence / Subprocess Audit

Verified on 2026-04-05.

This document records the repository-wide audit of direct `subprocess` usage for Phase 5B.

## Goal

Distinguish between:

1. **runner-layer expected** usage
2. **runtime media-path debt** that should move into shared runners
3. **platform integration helpers** that should remain separate
4. **build/deployment-only helpers** that should remain separate

Tests are excluded from this audit because they intentionally patch/inspect process execution behavior.

---

## Summary

Phase 5B is complete.

- Active runtime media-execution debt was migrated into the shared runner layer.
- Remaining direct `subprocess` usage is now limited to:
  - runner-layer execution internals
  - platform/open-file/open-player helpers
  - generic tool-health probing
  - packaging/update helpers

---

## Classification Table

| File | Classification | Status | Notes |
|---|---|---:|---|
| `ravn_app/core/runners/base.py` | runner-layer expected | keep | shared process execution base (`Popen`, timeout, cancellation, result normalization) |
| `ravn_app/core/runners/ffmpeg.py` | runner-layer expected | keep | FFmpeg / FFprobe execution, progress parsing, probe helpers |
| `ravn_app/core/runners/ytdlp.py` | runner-layer expected | keep | yt-dlp execution and metadata extraction |
| `ravn_app/core/runners/aria2.py` | runner-layer expected | keep | aria2 torrent execution |
| `ravn_app/core/media_helpers.py` | runtime media-path debt | **migrated** | `detect_silence`, `detect_black_frames`, `generate_scene_previews`, `generate_scene_thumbnails` now use `FFmpegRunner.run_raw()` |
| `ravn_app/utils/ffmpeg_checker.py` | runtime/support helper debt | **migrated** | now uses `FFmpegRunner` / `run_ffprobe_json()` |
| `ravn_app/utils/system_utils.py` | runtime/support helper debt | **migrated** | `get_ffmpeg_version()` now uses `FFmpegRunner.get_version()` |
| `ravn_app/core/tool_health.py` | platform integration helper | keep | generic tool version probing for dependency health, not a media execution path |
| `ravn_app/ui/main_window.py` | platform integration helper | keep | OS-specific open-folder behavior |
| `ravn_app/ui/tabs/library_tab.py` | platform integration helper | keep | OS-specific open-file/open-folder behavior |
| `ravn_app/ui/tabs/torrent_tab.py` | platform integration helper | keep | open target in system default app/player |
| `ravn_app/ui/tabs/download_tab.py` | platform integration helper | keep | open URL/file in system default app/player |
| `ravn_app/core/update_manager.py` | platform integration helper | keep | launch downloaded installer/archive handling |
| `ravn_app/core/app_builder.py` | build/deployment-only helper | keep | PyInstaller/NSIS/build pipeline commands |

---

## Migrated Runtime Media Paths

### 1. `MediaHelpers` smart analysis operations

Previously these operations bypassed shared runners with direct `subprocess.run()` calls:

- `detect_silence()`
- `detect_black_frames()`
- `generate_scene_previews()`
- `generate_scene_thumbnails()`

They now execute through `FFmpegRunner.run_raw()`.

### Why this matters

This aligns them with the shared runner model and gives them the same:

- timeout handling
- cancellation/status model
- structured `RunnerResult`
- normalized process logging
- consistent FFmpeg error shaping

### 2. `FFmpegCodecChecker`

Previously it called FFprobe and FFmpeg directly.

It now uses:

- `FFmpegRunner.run_ffprobe_json()`
- `FFmpegRunner.get_version()`

### 3. `system_utils.get_ffmpeg_version()`

Previously it called `subprocess.run(["ffmpeg", "-version"])` directly.

It now uses `FFmpegRunner.get_version()`.

---

## Consolidated Concerns Now Covered by Shared Runners

The migrated runtime media paths now inherit shared runner behavior for:

- **timeout handling** via `BaseRunner._run_process()`
- **cancellation model** via runner state/process tracking
- **logging** via runner-level command execution logging
- **structured process results** via `RunnerResult`
- **user-facing error shaping** via runner `_parse_error()` implementations

---

## ARC-04 Boundary Decision

OS-level helpers remain intentionally outside the runner layer.

Examples:

- open file in default application
- reveal file in folder
- open folder in Finder/Explorer/xdg-open
- launch downloaded installer

Reason:

These are **platform integration behaviors**, not media-processing flows. Wrapping them in media runners would blur responsibilities and weaken the architecture.

---

## Remaining Direct `subprocess` Usage After Phase 5B

After migration, remaining direct `subprocess` usage in runtime code is intentional and falls into one of these buckets:

1. runner-layer expected
2. platform integration helper
3. build/deployment-only helper

No active Phase 5B runtime media-execution debt remains in the main acquisition/studio/utility paths audited here.

---

## Verification

Targeted verification relevant to this phase:

- `pytest -q tests/test_runners.py tests/test_media_helpers.py tests/test_cli.py`
- `pytest -q tests/test_ui_logic.py tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q`

Observed validated baseline after Phase 5B completion:

- targeted Phase 5B sweep: `126 passed`
- full suite: `609 passed, 1 skipped`

---

## Follow-up

At Phase 5B close, the follow-up track was **Phase 5C — UX hardening / scalability investigation**. See `TASKS.md` for the current active phase.


# Phase 5C — UX Hardening / Scalability Investigation

Verified on 2026-04-05.

This document records the Phase 5C UX hardening and evidence-driven scalability work.

## Goal

Improve perceived stability on realistic desktop sizes and investigate scaling risks with measurements before applying optimization.

---

## Completed Tasks

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

Key verification commands used for this phase:

- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
- `pytest -q tests/test_utilities_tab.py tests/test_i18n_and_design_tokens.py tests/test_ui_logic.py`
- `pytest -q`

Validated baseline after Phase 5C completion:

- full suite: `614 passed, 1 skipped`

---

## Outcome

Phase 5C is complete.

The project now has:
- stronger compact-height behavior in the Download workspace
- explicit stress verification for large playlist/library/torrent states
- built-in hotspot measurements for the riskiest list-heavy UI paths
- measured, minimal mitigations instead of premature over-engineering

At Phase 5C close, the follow-up track was **Phase 5D — Codebase cleanup / wrapper / extension-boundary clarity**. See `TASKS.md` for the current active phase.


# Phase 5D — Codebase Cleanup / Wrapper / Extension-Boundary Clarity

Verified on 2026-04-05.

This document records the Phase 5D cleanup work that clarifies the active desktop UI surface and the current status of RAVN's experimental extension scaffolding.

---

## Goal

Reduce maintenance ambiguity after the workspace-shell migration by making the canonical desktop import surfaces explicit and by documenting which older modules are compatibility-only.

---

## Canonical Desktop Feature Imports

For active desktop feature wiring, use the `ravn_app.ui.tabs` namespace.

Canonical surfaces:

- `ravn_app.ui.tabs.download_workspace.DownloadWorkspace`
- `ravn_app.ui.tabs.download_tab.DownloadTab`
- `ravn_app.ui.tabs.torrent_tab.TorrentTab`
- `ravn_app.ui.tabs.converter_tab.ConverterTab`
- `ravn_app.ui.tabs.subtitle_tab.SubtitleTab`
- `ravn_app.ui.tabs.filters_tab.FiltersTab`
- `ravn_app.ui.tabs.mixer_tab.MixerTab`
- `ravn_app.ui.tabs.utilities_tab.UtilitiesTab`
- `ravn_app.ui.tabs.library_tab.LibraryTab`
- `ravn_app.ui.tabs.history_tab.HistoryTab`
- `ravn_app.ui.tabs.settings_tab.SettingsTab`
- `ravn_app.ui.tabs.queue_tab.QueueTab`
- `ravn_app.ui.tabs.home_workspace.HomeWorkspace`
- `ravn_app.ui.tabs.library_workspace.LibraryWorkspace`
- `ravn_app.ui.tabs.studio_workspace.StudioWorkspace`

`ravn_app.ui.main_window.YouTubeDownloaderApp` remains the desktop shell entry surface.

---

## Compatibility Inventory

### Legacy-compatible modules still under `ravn_app/ui/`

These modules remain in the repository so older imports continue to resolve, but they are no longer the preferred import surfaces for active desktop feature work:

- `ravn_app/ui/download_tab.py`
  - legacy alias to `ravn_app.ui.tabs.download_tab.DownloadTab`
- `ravn_app/ui/converter_tab.py`
  - legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.converter_tab`
- `ravn_app/ui/subtitle_tab.py`
  - legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.subtitle_tab`
- `ravn_app/ui/history_settings_tab.py`
  - shared legacy-compatible implementation module behind canonical `ravn_app.ui.tabs.history_tab` and `ravn_app.ui.tabs.settings_tab`

### Canonical wrappers retained under `ravn_app/ui/tabs/`

Some canonical `ui/tabs/` modules still forward to older implementation modules. This is intentional for now because it keeps behavior stable while the project finishes Phase 5 hardening/packaging work.

Retained canonical wrappers:

- `ravn_app/ui/tabs/converter_tab.py`
- `ravn_app/ui/tabs/subtitle_tab.py`
- `ravn_app/ui/tabs/history_tab.py`
- `ravn_app/ui/tabs/settings_tab.py`

These wrappers are now explicitly documented as canonical import surfaces rather than ambiguous parallel entry points.

---

## Wrapper Cleanup Outcome

Phase 5D focused on reducing ambiguity, not performing a risky UI-file migration.

Completed cleanup actions:

- standardized wrapper docstrings so canonical vs legacy intent is explicit
- updated tests to use canonical `ravn_app.ui.tabs.*` imports for active feature modules
- added regression coverage for canonical/legacy import equivalence

Deferred intentionally:

- moving all legacy implementation bodies into `ravn_app/ui/tabs/`
- splitting `history_settings_tab.py` into separate implementation files

Those larger file moves are better handled in a later cleanup phase if they provide enough value to justify churn.

---

## `plugin_system.py` Decision

Current decision: **experimental only / future extension surface**.

`ravn_app/core/plugin_system.py` is:

- **not** auto-loaded by the desktop shell
- **not** auto-loaded by the CLI
- **not** part of a supported packaged-plugin runtime story
- retained only as an experimental scaffold for possible future extension work

Additional clarity applied:

- the module now declares explicit status metadata (`experimental`, runtime-integrated = `False`)
- repository docs now describe it as an experimental scaffold rather than an active runtime feature
- `ravn_app/core/database.py` plugin hook placeholders are also treated as internal hooks, not as a public plugin API

---

## Verification

Key verification commands used for this phase:

- `pytest -q tests/test_import_surfaces.py`
- `pytest -q tests/test_ui_logic.py`
- `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
- `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
- `pytest -q`

Validated baseline after Phase 5D completion:

- full suite: `617 passed, 1 skipped`

---

## Outcome

Phase 5D is complete.

The repository now makes these points explicit:

- active desktop feature imports should come from `ravn_app.ui.tabs`
- legacy `ravn_app.ui.*` modules are compatibility surfaces, not equal peers
- `plugin_system.py` does not imply supported runtime plugin loading today

The next active track is **Phase 5E — Full Optimization / Clean Code / Dead Code Cleanup**.


# Phase 5E — Benchmark Closeout

Verified on 2026-04-05.

Repeatable benchmark harness:

- `python tools/phase5e_benchmarks.py`
- optional artifact output: `python tools/phase5e_benchmarks.py --output docs/phase5e_benchmark_results.json`

The harness records:

- SQL statement counts via `sqlite3.set_trace_callback()`
- wall-clock timing via `time.perf_counter()`
- memory peaks via `tracemalloc`
- idle Home/Queue refresh behavior through repeated snapshot-refresh loops

## Recorded Results

Source artifact:

- `docs/phase5e_benchmark_results.json`

### 1. MediaLibrary hot paths

- `list_media(limit=120)`
  - optimized path: `2` SQL statements, `1.407 ms`
  - legacy N+1 simulation: `121` SQL statements, `4.831 ms`
- `search_media(query="Clip", tags=["shared"], format="mp4", limit=80)`
  - `4` SQL statements, `3.501 ms`
- `get_statistics()`
  - `4` SQL statements, `0.361 ms`

Interpretation:

- bulk tag preloading removed the old per-row tag fan-out from list/search-style paths
- cached statistics keep aggregate reads bounded and cheap between invalidations

### 2. Export memory

JSON export comparison on the same synthetic library dataset:

- streamed export peak: `703.806 KiB`
- materialize-then-write simulation peak: `795.273 KiB`

Interpretation:

- the landed exporter keeps the JSON write path below the legacy materialize-then-write memory peak on the measured dataset
- streaming is primarily a safety/scale improvement; raw elapsed time is not the only success criterion here

### 3. Auto-add batch reuse

- batched auto-add:
  - `317.964 ms`
  - peak `228.896 KiB`
  - metadata handlers created: `1`
- naive per-file registration simulation:
  - `653.903 ms`
  - peak `2685.438 KiB`
  - metadata handlers created: `80`

Interpretation:

- one shared library session + one metadata handler per batch materially reduces both setup churn and peak memory

### 4. Playlist metadata staging

Synthetic 140-entry playlist benchmark:

- initial flat fetch:
  - `1.095 ms`
  - peak `113.512 KiB`
- deferred full-detail fetch:
  - `23.175 ms`
  - peak `408.419 KiB`
- merge step:
  - `0.325 ms`
  - merged entries: `140`

Interpretation:

- the UI can now receive a cheap first-pass playlist payload quickly
- heavier quality/detail enrichment is explicitly staged behind that initial response instead of being part of the first visible step

### 5. Idle Home / Queue refresh behavior

5,000 repeated idle loops with an unchanged task snapshot:

- snapshot-aware path:
  - `0.479 ms`
  - refresh counts: header `0`, home `0`, queue `0`
- legacy always-refresh simulation:
  - `1.041 ms`
  - refresh counts: header `5000`, home `5000`, queue `5000`

Interpretation:

- the closeout confirms that unchanged task state no longer causes repeated Home/Queue refresh work in the measured loop

## Notes On Baselines

The benchmark harness uses small legacy-style simulations for before/after comparison rather than checking out a second git revision.

That means:

- SQL and timing comparisons are still reproducible in one working tree
- the compared baselines stay close to the concrete hot paths that Phase 5E changed
- results should be treated as engineering evidence for packaging readiness, not as marketing-grade performance claims

## Outcome

This closes the remaining benchmark/documentation items in `OPTIMIZATIONS.md` and leaves Phase 5E with:

- repeatable benchmark tooling
- measured SQL counts
- measured timing samples
- measured memory samples
- measured idle-refresh evidence


# Phase 5E — Dead Code / Waste Audit

Verified on 2026-04-05.

This document closes the OPT-01 / OPT-07 audit pass from `OPTIMIZATIONS.md`.

## Scope Reviewed

- `ravn_app/ui/`
- `ravn_app/ui/tabs/`
- `ravn_app/core/persistence/`
- `ravn_app/core/task_manager.py`
- queue / Home refresh wiring
- legacy-compatible desktop import surfaces documented during Phase 5D

## Confirmed Unbounded / Wasteful Paths

Already addressed earlier in Phase 5E:

- completed in-memory task retention in `ravn_app/core/task_manager.py`
- `search_history` retention in `ravn_app/core/persistence/media_library.py`
- no-op `QueuePanel.clear_completed()` path
- repeated library/session recreation in auto-add batch flows
- repeated Home/Queue redraw work under unchanged task state

## Dead / No-ROI Shims Removed In This Closeout

Removed from `ravn_app/ui/tabs/download_tab.py`:

- `_on_mode_changed()`
  - no in-repo callers
  - no-op compatibility stub
- `_is_audio_mode()`
  - no in-repo callers
  - always returned `False`

These were the clearest now-provably-unneeded method-level shims left after the earlier cleanup pass.

## Compatibility Surface Re-Check

Re-reviewed `ravn_app.ui.*` compatibility modules and `ravn_app.ui.tabs.*` wrappers documented in `docs/phase5d_wrapper_boundary_clarity.md`.

### Retained intentionally

Still retained for Phase 5 stability/documented import compatibility:

- `ravn_app/ui/download_tab.py`
- `ravn_app/ui/converter_tab.py`
- `ravn_app/ui/subtitle_tab.py`
- `ravn_app/ui/history_settings_tab.py`
- canonical wrappers under `ravn_app/ui/tabs/` for converter/history/settings/subtitle

### Why retained

- they still define the documented compatibility story for desktop imports during the pre-packaging window
- removing them would create churn beyond the measured optimization targets
- current runtime clarity is already explicit in repo docs, so retention is no longer ambiguous debt

## Safe-Removal Candidates Reviewed But Deferred

Deferred intentionally because ROI/risk did not justify more churn before Phase 5F:

- legacy import modules that still encode the documented compatibility contract
- larger implementation-file moves for converter/subtitle/history/settings bodies
- experimental `plugin_system.py` removal
  - explicitly documented as experimental-only already
  - not a runtime hot path

## Outcome

Phase 5E closeout now has:

- explicit retained-state bounds
- explicit retained compatibility surfaces
- removal of the remaining obvious no-op method shims discovered in the audit
- no undocumented wrapper/shim ambiguity left in the active desktop path


# Phase 5E — Optimization Baseline And Landed Changes

Verified on 2026-04-05.

This document records the first landed Phase 5E optimization set, aligned with the execution order in `OPTIMIZATIONS.md`.

For the final audit/benchmark closeout, also see:

- `docs/phase5e_dead_code_audit.md`
- `docs/phase5e_benchmark_closeout.md`
- `docs/phase5e_benchmark_results.json`

## Landed Focus Areas

### 1. MediaLibrary hot-path cleanup

Files:
- `ravn_app/core/persistence/media_library.py`
- `ravn_app/ui/tabs/library_tab.py`

Changes:
- removed MediaLibrary N+1 tag loading for list/search/collection/duplicate paths by bulk-preloading tags for fetched media IDs
- introduced shared media-row mapping helpers so hot paths reuse one row-to-record flow instead of repeating per-row tag queries
- added cached library statistics with explicit invalidation on media/tag/collection mutations
- stopped recomputing duplicate-heavy library statistics on every library search/reset flow
- added search-history pruning (bounded retention) so `search_history` no longer grows without limit
- changed library export to iterate in batches instead of materializing one very large media-item list in memory

### 2. Auto-add batch reuse

File:
- `ravn_app/core/persistence/library_sync.py`

Changes:
- `MediaLibraryAutoAdder.register_outputs()` now reuses one `MediaLibrary` instance per batch
- the same batch now reuses one metadata handler instead of recreating a library+handler for every file
- shared registration logic was consolidated so single-file and batch flows now go through the same code path
- new-item registration now builds one merged metadata payload up front instead of doing a create-then-read-then-update sequence

### 3. Queue/task retained-state cleanup

Files:
- `ravn_app/core/task_manager.py`
- `ravn_app/ui/queue_panel.py`
- `ravn_app/ui/tabs/queue_tab.py`

Changes:
- added bounded in-memory retention for terminal tasks in `TaskQueue` (default completed-history limit: `200`)
- added a stable task UI snapshot helper for low-cost dirty checks
- wired `QueuePanel.clear_completed()` to the real queue cleanup path
- reduced queue-panel rebuild work by refreshing on snapshot change, with a lower-frequency fallback refresh for non-shell hosts

### 4. Home/queue refresh overhead cleanup

Files:
- `ravn_app/ui/main_window.py`
- `ravn_app/ui/tabs/home_workspace.py`

Changes:
- replaced fixed periodic Home dashboard refreshes with snapshot-driven refreshes when task state actually changes
- queue drawer refresh now follows task snapshot changes instead of relying only on fixed polling
- Home summary cards now update label content in place instead of destroy/recreate refreshes

### 5. History query indexing

File:
- `ravn_app/core/database.py`

Changes:
- schema version advanced to `4`
- added history/top-N indexes for:
  - `downloads(download_date DESC)`
  - `downloads(status, download_date DESC)`
  - `conversions(conversion_date DESC)`
  - `operations(COALESCE(completed_at, started_at) DESC)`
  - `operations(task_type, COALESCE(completed_at, started_at) DESC)`
- added v3→v4 migration recording for index creation

## Verification Evidence

### Regression

Validated after landing this batch:

- `pytest -q`
  - `624 passed, 1 skipped`
- focused optimization sweep:
  - `pytest -q tests/test_media_library.py tests/test_library_sync.py tests/test_task_manager.py tests/test_database_manager.py tests/test_ui_logic.py`
  - `138 passed`

### Query-plan evidence

Query-plan assertions were added in `tests/test_database_manager.py`.

Verified points:
- downloads status/history reads use `idx_downloads_status_download_date`
- operations top-N history reads use `idx_operations_history_sort`
- common operations top-N plan does not fall back to a temp B-tree sort in the covered test case

## Deliberate Non-Changes In This Batch

At the time this first landed slice was recorded, the remaining Phase 5E follow-ups were:
- playlist metadata staging for very large playlists
- broader dead-code audit closeout
- compatibility-wrapper revisit after more cleanup lands
- larger extraction/naming passes beyond the hot paths above

Those later closeout items are now tracked in the companion documents listed at the top of this file.

## Outcome

This landed batch closes the first high-ROI optimization slice from `OPTIMIZATIONS.md` and improves:
- library query efficiency
- batch auto-add efficiency
- retained-state bounds
- Home/Queue refresh behavior
- history query plans
- large-export memory behavior


