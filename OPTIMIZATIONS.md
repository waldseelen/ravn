# Phase 5E — Optimization Task Board

Read `TASKS.md`, `PROGRESS.md`, `ARCHITECTURE.md`, and `README.md` first.

Use `TASKS.md` for Phase 5 status/ordering.
Use this file for the detailed Phase 5E execution checklist.

Verified audit baseline: 2026-04-05.

Landed optimization evidence for the current slice is recorded in:

- `docs/phase5e_optimization_baseline.md`
- `docs/phase5e_dead_code_audit.md`
- `docs/phase5e_benchmark_closeout.md`
- `docs/phase5e_benchmark_results.json`

## Goal

Complete the highest-ROI optimization, cleanup, and dead-code work before Phase 5F Windows packaging starts.

## Highest-Impact Areas First

- Library/query performance
- History/query indexing
- Batch auto-add efficiency
- Playlist metadata fetch cost
- UI polling/rebuild overhead
- Dead code / stale compatibility cleanup

## Detailed Checklist

- [x] **[OPT-01]** Run a repository-wide dead-code and waste audit
  - [x] Inventory unused functions, no-op helpers, stale branches, and abandoned compatibility code
  - [x] Re-check `ravn_app.ui.*` compatibility surfaces after Phase 5D
  - [x] Identify unbounded retained-state paths such as in-memory completed tasks and persisted search history
  - [x] Record safe-removal candidates vs items that must stay for compatibility

- [x] **[OPT-02]** Remove dead code that is provably safe and cap clearly wasteful retained state
  - [x] Remove or wire the no-op `ravn_app/ui/queue_panel.py::clear_completed()` path
  - [x] Add a retention policy for completed in-memory tasks in `ravn_app/core/task_manager.py`
  - [x] Add a retention/pruning policy for `search_history`
  - [x] Document intentionally retained compatibility surfaces instead of leaving them ambiguous

- [x] **[OPT-03]** Audit duplicated logic across UI/core/CLI paths and consolidate obvious repetitions
  - [x] Remove `MediaLibrary` N+1 tag-loading behavior by introducing bulk tag preload helpers
  - [x] Reuse one `MediaLibrary` instance and one metadata handler per auto-add batch in `ravn_app/core/persistence/library_sync.py`
  - [x] Extract shared library result-mapping/query helpers instead of repeating row-to-record work across hot paths
  - [x] Consolidate repeated batch registration/setup patterns where behavior is meant to stay shared

- [x] **[OPT-04]** Refactor overgrown modules where targeted extraction improves maintainability without changing user-visible behavior
  - [x] Split `ravn_app/core/persistence/media_library.py` into clearer query, row-mapping, export, and stats responsibilities where ROI is proven
  - [x] Extract batch registration helpers from `ravn_app/core/persistence/library_sync.py`
  - [x] Extract dashboard/refresh coordination only where it directly reduces measured UI overhead
  - [x] Avoid broad churn in large modules unless tied to a measured hotspot or dead-code removal

- [x] **[OPT-05]** Normalize naming and organization in recently expanded feature areas where inconsistency increases maintenance friction
  - [x] Align library/search/export helper naming after extraction
  - [x] Keep optimization helpers and cached-stat/query helper names explicit and consistent
  - [x] Revisit mixed implementation files only where naming/ownership confusion blocks optimization work

- [x] **[OPT-06]** Review helper/module boundaries for clean-code quality and remove unnecessary work in hot paths
  - [x] Stop recomputing duplicate-heavy library statistics on every library search/reset flow
  - [x] Add secondary SQLite indexes for `downloads`, `conversions`, and `operations` top-N/history queries
  - [x] Verify history query plans no longer depend on full scans + temp B-tree sorts for common reads
  - [x] Move Home/Queue refresh work toward dirty/event-driven updates instead of fixed polling where practical
  - [x] Update dashboard widgets in place where possible instead of destroy/recreate refreshes
  - [x] Stage playlist metadata enrichment so large playlists do not always pay full upfront detail cost
  - [x] Stream/page large library exports instead of materializing very large result sets in one burst

- [x] **[OPT-07]** Revisit compatibility wrappers and legacy shims again after cleanup
  - [x] Re-evaluate `ravn_app.ui.*` wrappers after Phase 5E cleanup lands
  - [x] Remove any now-provably-unneeded shims
  - [x] Keep retained compatibility surfaces explicit and documented if they still need to exist for Phase 5

- [x] **[OPT-08]** Tighten documentation after optimization so docs reflect cleaned structure instead of historical leftovers
  - [x] Update `TASKS.md` summary when checklist items land
  - [x] Update `PROGRESS.md`, `ARCHITECTURE.md`, and `README.md` together if repository reality changes
  - [x] Record benchmark evidence, chosen optimizations, and deliberate non-changes so packaging starts from a measured baseline

- [x] **[OPT-09]** Run a broad regression sweep and do not accept optimization changes that reduce behavioral confidence
  - [x] Add or script repeatable optimization benchmarks for library, auto-add batch, playlist, and idle-Home flows
  - [x] Measure SQL statement counts with `sqlite3.set_trace_callback()` before/after
  - [x] Measure query plans with `EXPLAIN QUERY PLAN` before/after index work
  - [x] Measure wall-clock timings with `time.perf_counter()` for search/list/stats/export/fetch flows
  - [x] Measure memory during large playlist fetches and exports with `tracemalloc` or RSS snapshots
  - [x] Measure idle CPU/redraw behavior while `Home` is visible
  - [x] Run validation commands:
    - [x] `pytest -q`
    - [x] `pytest -q tests/test_ui_logic.py`
    - [x] `pytest -q tests/test_ui_components.py tests/test_app_builder.py`
    - [x] `pytest -q tests/test_config_paths.py tests/test_database_manager.py`
  - [x] Add targeted sweeps for every touched hotspot module before closing Phase 5E

## Recommended Execution Order

1. `OPT-03` bulk tag loading + batch auto-add reuse
2. `OPT-06` history indexes + library stats recompute cleanup
3. `OPT-06` export paging + playlist metadata staging
4. `OPT-02` retention bounds + dead no-op removal
5. `OPT-04` / `OPT-05` targeted extraction and naming cleanup
6. `OPT-07` wrapper/shim revisit
7. `OPT-08` / `OPT-09` docs + benchmark/regression closeout

## Guardrails

- Keep optimization work evidence-driven; do not over-engineer speculative fixes.
- Preserve correctness and readability over clever micro-optimizations.
- Keep shared runner boundaries intact.
- Do not imply supported runtime plugin behavior.
- Do not start Phase 5F packaging until the highest-ROI Phase 5E items are in acceptable shape.
