# Optimization Baseline and Landed Changes

Verified on 2026-04-05.

This document records the first landed optimization set summarized in `OPTIMIZATIONS.md`.

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

At the time this first landed slice was recorded, the remaining follow-ups were:
- playlist metadata staging for very large playlists
- broader dead-code audit closeout
- compatibility-wrapper revisit after more cleanup lands
- larger extraction/naming passes beyond the hot paths above

Those later closeout items are now tracked in the companion documents listed at the top of this file.

## Outcome

This landed batch closes the first high-ROI optimization slice summarized in `OPTIMIZATIONS.md` and improves:
- library query efficiency
- batch auto-add efficiency
- retained-state bounds
- Home/Queue refresh behavior
- history query plans
- large-export memory behavior
