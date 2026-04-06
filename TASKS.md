# RAVN — Project Task Board

All development tasks organized by priority and status.

Read `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `README.md`, and `PROGRESS.md` first. Treat them as one unified instruction set and follow all rules, constraints, and context strictly.

Then execute `TASKS.md` as the single source of truth.

- Only complete tasks marked `[ ]`
- Never touch or redo tasks marked `[x]`
- Do not deviate from scope, structure, or intent
- If any conflict occurs, follow the most recent and most specific instruction
- After completing eligible tasks, update docs to match repository reality

---

## Current Product Status

### Completed

- [x] Phase 1 — Main media path stabilization
- [x] Phase 2 — Config relocation, error messages, drag & drop, CLI
- [x] Phase 3 — Platform support expansion, DB migrations, tests, tray
- [x] Phase 4A — Core GUI completeness
- [x] Phase 4B — Design system + interaction improvements
- [x] Phase 4C — Polish / accessibility / shell refinement work
- [x] Phase 4D — Responsive layout, theme parity, settings consolidation, playlist UX
- [x] Phase 6 — Torrent / magnet integration
- [x] Phase 7 — Media-management expansion (library / history / utilities / queue coverage)
- [x] Phase 8 — Workspace shell / navigation overhaul
- [x] YTD-01 through YTD-11 — Intent-driven acquisition-engine upgrade

### Active Main Area

- [ ] **Phase 5 — Release Readiness, Hardening, and Windows Packaging**

### Packaging Scope Decision

For now, packaged deployment targets are:

- **Windows packaged release: in scope**
- **Linux packaged release: out of scope for now**
- **macOS packaged release: out of scope for now**

Linux and macOS source-checkout usage may still work, but Phase 5 packaging work should focus on a polished **Windows-only distributable**.

---

## Phase 5 — Release Readiness, Hardening, and Windows Packaging

This phase is intentionally ordered so that **runtime risks, architecture debt, and user-facing fragility are reduced first**, then the project moves into Windows packaging/release work.

---

## Phase 5A — Runtime Dependency Health / Toolchain UX

Goal: make the app explicit, reliable, and user-readable when required tools are missing or partially available.

### Confirmed Risks

- FFmpeg / FFprobe are core product dependencies for conversion, filters, mixer, subtitle embedding, utilities, and post-download processing.
- yt-dlp is a core dependency for the acquisition stack.
- aria2c is an optional-but-critical dependency for torrent features.
- Missing-tool states are still more fragile/implicit than they should be for a packaged end-user product.

### Tasks

- [x] **[DEP-01]** Add a shared tool-health/status model for:
  - `ffmpeg`
  - `ffprobe`
  - `yt-dlp`
  - optional `aria2c`
- [x] **[DEP-02]** Surface tool-health status in the desktop app (`Home`, `Settings`, or both) with user-readable summaries
- [x] **[DEP-03]** Improve startup/runtime messaging so missing tools clearly explain which features are affected
- [x] **[DEP-04]** Make torrent dependency expectations explicit in UI/CLI when `aria2c` is unavailable
- [x] **[DEP-05]** Clearly document hard vs optional dependencies in user-facing docs and troubleshooting flows
- [x] **[DEP-06]** Ensure missing optional tools degrade by feature area instead of feeling like a whole-app failure

### Acceptance Focus

- Users can immediately understand what is missing
- Users can immediately understand what still works
- Optional-tool failures do not make the whole app feel broken

**Status:** Phase 5A complete.

---

## Phase 5B — Shared-Runner Convergence / Runtime Process Cleanup

Goal: reduce architecture drift by moving runtime-critical external-process paths toward the shared-runner model.

### Confirmed Risks

- The architecture prefers shared execution through `ravn_app/core/runners/`
- Some runtime-adjacent paths still use direct `subprocess` calls outside the preferred shared-runner boundary
- This increases inconsistency in timeout, cancellation, logging, and error shaping behavior

### Tasks

- [x] **[ARC-01]** Audit all direct `subprocess` usage and classify each occurrence as:
  - runner-layer expected
  - runtime media-path debt
  - platform integration helper
  - build/deployment-only helper
- [x] **[ARC-02]** Prioritize runtime media-execution paths that still bypass shared runners and migrate them first
- [x] **[ARC-03]** Consolidate shared concerns where appropriate:
  - timeout handling
  - cancellation
  - logging
  - structured process results
  - user-facing error shaping
- [x] **[ARC-04]** Keep OS-level open-file/open-folder/open-player helpers separate unless a runner abstraction is clearly justified
- [x] **[ARC-05]** Update docs so legitimate runner use of `subprocess` is clearly distinguished from runner-bypass debt

### Acceptance Focus

- Runtime media execution paths prefer shared runners
- Process behavior becomes more uniform across features
- Architecture intent is easier to maintain and reason about

**Status:** Phase 5B complete.

---

## Phase 5C — UX Hardening / Scalability Investigation

Goal: close real user-facing rough edges and verify whether suspected scaling problems are actual bottlenecks before over-engineering.

### Confirmed / Investigate Risks

- Some Download workspace states have already shown UX roughness around content height/scroll behavior and mode toggling
- Large playlist, large library, and many-row torrent states may become scaling risks, but this should be measured rather than assumed
- CustomTkinter list-heavy surfaces may require throttling/chunking if profiling confirms it

### Tasks

- [x] **[UX-REL-01]** Continue polishing Download workspace layout behavior so no mode gives a clipped/broken impression on typical desktop heights
- [x] **[PERF-01]** Add large-playlist stress verification for Download workspace + playlist dialog
- [x] **[PERF-02]** Add large-library stress verification for library browsing/search surfaces
- [x] **[PERF-03]** Add many-row torrent-session stress verification for torrent rows + child-file rendering
- [x] **[PERF-04]** Measure UI update/rerender hotspots before claiming virtualization is required
- [x] **[PERF-05]** If profiling confirms scaling issues, apply the smallest adequate mitigation:
  - throttled updates
  - chunked rendering
  - pagination
  - visible-row virtualization where justified

### Acceptance Focus

- The app feels stable and intentional on realistic desktop sizes
- Performance concerns are evidence-driven
- Optimizations follow measured bottlenecks, not guesswork

**Status:** Phase 5C complete.

---

## Phase 5D — Codebase Cleanup / Wrapper / Extension-Boundary Clarity

Goal: reduce maintenance ambiguity after the workspace-shell migration.

### Confirmed Risks

- Compatibility wrappers from the older UI structure still coexist with the newer `ui/tabs/` organization
- `plugin_system.py` exists as an extension boundary, but it is not central to the active runtime
- These are maintenance/clarity issues more than immediate product-break risks

### Tasks

- [x] **[CLN-01]** Inventory compatibility wrappers still living under `ravn_app/ui/` vs canonical `ravn_app/ui/tabs/` surfaces
- [x] **[CLN-02]** Remove or simplify wrappers that are no longer needed
- [x] **[CLN-03]** Document canonical import and entry surfaces for desktop feature modules
- [x] **[CLN-04]** Decide the current status of `plugin_system.py`:
  - experimental only
  - future extension surface
  - or simplification/removal candidate
- [x] **[CLN-05]** Reflect that extension-boundary decision in docs so the repo does not imply unsupported runtime plugin behavior

### Acceptance Focus

- Fewer misleading parallel surfaces
- Clearer ownership of active runtime paths
- Extension story is explicit rather than implied

**Status:** Phase 5D complete. Phase 5E cleanup/optimization is now complete; continue with Phase 5F Windows packaging next.

---

## Phase 5E — Full Optimization / Clean Code / Dead Code Cleanup

Goal: perform a comprehensive repository-wide optimization pass before packaging so the Windows release is built from a cleaner, leaner, more maintainable codebase.

### Confirmed Risks

- The project has grown substantially across multiple phases and now carries normal accumulation risk around dead code, duplicated logic, compatibility leftovers, and broad-but-inconsistent helper patterns.
- Some optimization opportunities are functional/architectural, not only performance-related:
  - dead code
  - stale helpers
  - overgrown modules
  - repetitive logic
  - inconsistent naming/structure
  - unnecessary compatibility layers
- Releasing before this pass risks locking avoidable maintenance debt into the first packaged Windows release.

### Tasks

Detailed Phase 5E execution has moved to [`OPTIMIZATIONS.md`](OPTIMIZATIONS.md).

Phase 5E closeout delivered:

- MediaLibrary split into clearer row-mapping / stats / export responsibilities via internal helpers
- MediaLibrary auto-add batches now reuse one library session / metadata handler per batch through extracted batch-registration helpers
- Completed-task retention and search-history pruning are bounded
- History/top-N SQLite indexes landed with query-plan regression coverage
- Home/Queue refresh coordination now routes through a snapshot-aware helper instead of repeated fixed redraw work
- Playlist metadata enrichment is now staged: fast flat playlist load first, deferred detail merge second
- Download workspace now uses one smart source bar with contextual media / playlist / batch / torrent routing plus shared `Video` / `Audio` output switching
- Desktop launch centering now uses taskbar-aware usable bounds and prefers the active monitor on Windows
- Large library exports now stream in batches instead of materializing one large result list
- Dead-code / wrapper audit closeout is documented, with remaining import-compatibility surfaces kept explicit
- Repeatable benchmark tooling and recorded evidence now exist under `tools/phase5e_benchmarks.py` and `docs/phase5e_*`

- [x] **[OPT-00]** Complete the active Phase 5E optimization checklist in `OPTIMIZATIONS.md`

### Acceptance Focus

- Codebase is leaner and easier to maintain
- Avoidable duplication and dead code are reduced
- Cleanup stays behavior-safe and architecture-aligned
- Windows packaging begins from a stronger baseline

---

## Phase 5F — Windows Packaging / Release Pipeline

Goal: after runtime/tooling/hardening work is sufficiently stable, produce a trustworthy Windows distributable.

### Confirmed Risks

- The repo already contains packaging scaffolding (`build.ps1`, `ravn.spec`, `app_builder.py`) and now has a Windows-first release pipeline, but one manual clean-machine validation gate remains
- Bundled FFmpeg strategy is now defined around `assets/ffmpeg/win64/`, runtime path auto-detection, and PyInstaller asset bundling
- Clean-machine validation has not yet closed the loop
- Signing strategy is documented, but public release signing still depends on certificate provisioning

### Tasks

- [x] **[BLD-01]** Update `ravn.spec` so Windows packaging has a clear bundled-runtime strategy for FFmpeg / FFprobe and required assets
- [x] **[BLD-02]** Add a bundled FFmpeg asset layout for Windows (for example `assets/ffmpeg/win64/`) and document how packaged builds consume it
- [x] **[BLD-03]** Extend `ravn_app/utils/ffmpeg_checker.py` to detect bundled FFmpeg/FFprobe before falling back to system PATH lookup
- [x] **[BLD-04]** Expand `build.ps1` from a developer helper script into a Windows packaging pipeline
- [x] **[BLD-05]** Add a Windows-focused CI artifact build workflow
- [x] **[BLD-06]** Add automated Windows release publishing workflow for tagged releases
- [ ] **[BLD-07]** Validate packaged behavior on a clean Windows machine / VM:
  - app launch
  - config-dir creation
  - FFmpeg detection
  - URL download
  - conversion
  - queue/history basics
  - library auto-add basics
- [x] **[BLD-08]** Add executable signing strategy for Windows (minimum viable documented signing path)

### Acceptance Focus

- Windows packaged app launches without developer-only assumptions
- Bundled/runtime FFmpeg is discoverable and usable
- Theme/i18n/assets still load correctly
- Download/convert/history/library basics work in the packaged build

**Status:** Phase 5F packaging pipeline implementation is largely complete; clean-machine validation (`BLD-07`) remains the final open release gate.

---

## Priority Order

Execution order should be:

1. **Phase 5A — Runtime dependency health / toolchain UX**
2. **Phase 5B — Shared-runner convergence / runtime process cleanup**
3. **Phase 5C — UX hardening / scalability investigation**
4. **Phase 5D — Codebase cleanup / wrapper / extension-boundary clarity**
5. **Phase 5E — Full optimization / clean code / dead code cleanup**
6. **Phase 5F — Windows packaging / release pipeline**

Do not jump to packaged release work before the earlier runtime-risk tracks are in an acceptable state.

---

## Notes

- Treat packaging/distribution as important, but not as the first remaining step.
- Treat runtime dependency clarity and shared-runner convergence as the most concrete pre-release hardening work.
- Treat performance/virtualization concerns as important but measurement-driven.
- Add a full optimization/cleanup pass before packaging so the first Windows release is not built on avoidable dead code or structural clutter.
- Prefer small, architecture-aligned cleanup steps over parallel systems or large rewrites.
