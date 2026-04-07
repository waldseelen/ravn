# Benchmark Closeout

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
- the compared baselines stay close to the concrete hot paths changed during the optimization work
- results should be treated as engineering evidence for packaging readiness, not as marketing-grade performance claims

## Outcome

This closes the remaining benchmark/documentation items in `OPTIMIZATIONS.md` and leaves the optimization track with:

- repeatable benchmark tooling
- measured SQL counts
- measured timing samples
- measured memory samples
- measured idle-refresh evidence
