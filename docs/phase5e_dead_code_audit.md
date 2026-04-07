# Dead Code and Waste Audit

Verified on 2026-04-05.

This document closes the dead-code and compatibility-surface audit summarized in `OPTIMIZATIONS.md`.

## Scope Reviewed

- `ravn_app/ui/`
- `ravn_app/ui/tabs/`
- `ravn_app/core/persistence/`
- `ravn_app/core/task_manager.py`
- queue / Home refresh wiring
- legacy-compatible desktop import surfaces documented in the wrapper-boundary notes

## Confirmed Unbounded / Wasteful Paths

Already addressed earlier in this optimization track:

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

Still retained for release stability and documented import compatibility:

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

Deferred intentionally because ROI/risk did not justify more churn before packaging:

- legacy import modules that still encode the documented compatibility contract
- larger implementation-file moves for converter/subtitle/history/settings bodies
- experimental `plugin_system.py` removal
  - explicitly documented as experimental-only already
  - not a runtime hot path

## Outcome

This closeout now has:

- explicit retained-state bounds
- explicit retained compatibility surfaces
- removal of the remaining obvious no-op method shims discovered in the audit
- no undocumented wrapper/shim ambiguity left in the active desktop path
