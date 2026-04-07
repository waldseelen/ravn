# Optimization Notes

This file summarizes the cleanup and optimization work already landed in RAVN. It exists as an engineering reference, not as an active task board.

## What landed

- Media-library internals were split into clearer row-mapping, stats, and export helpers.
- Auto-library registration batches now reuse one library session and one metadata handler per batch.
- Completed-task retention and search-history retention are bounded.
- Secondary SQLite indexes were added for common history and top-N queries.
- Home/Queue refresh coordination now favors snapshot-aware updates over repeated redraw work.
- Playlist metadata enrichment is staged so the first visible UI step is cheaper on large playlists.
- Large library exports now stream in batches instead of materializing one large result set.
- Legacy wrapper/compatibility surfaces were re-audited and documented more explicitly.
- Repeatable benchmark tooling and recorded evidence now exist under `tools/phase5e_benchmarks.py` and `docs/phase5e_*`.

## Evidence and supporting notes

- [docs/phase5e_optimization_baseline.md](docs/phase5e_optimization_baseline.md)
- [docs/phase5e_dead_code_audit.md](docs/phase5e_dead_code_audit.md)
- [docs/phase5e_benchmark_closeout.md](docs/phase5e_benchmark_closeout.md)
- `docs/phase5e_benchmark_results.json`

## Current stance

Optimization work for the current release track is considered complete. Additional performance or cleanup work should remain evidence-driven and tied to measured bottlenecks, not speculative rewrites.
