# RAVN — Quality Roadmap (141 → 180+/200)

Living checklist for raising the system score across 20 categories. Each workstream is
scored independently; keep `pytest -q` green (675 passed baseline) after every change.

## Workstream 1 — CI/CD & distribution repair  (+8: CI/CD 5→9, Packaging 7→9, Deps 7→9) — DONE
- [x] Remove broken misplaced `.github/lint.yml` + `.github/tests.yml` (literal `\n`, never run)
- [x] Add `pyproject.toml` with ruff + mypy config
- [x] Add real `.github/workflows/lint.yml` — ruff blocking (0 errors), mypy core informational
- [x] Add Python 3.13 to the test matrix
- [x] Coverage floor gate (`--cov-fail-under=48`, baseline ~50%) in tests workflow
- [x] Lock file: `requirements.in` (source) → `requirements.txt` (pip-compiled pin); dropped unused `aria2p`
- Bonus found+fixed: dead `AdvancedSettingsDialog`/`HistoryViewer` (182 lines, latent `Colors` NameError);
  `Dict[str, any]`→`Any` bug in tool_health; discarded download result in queue worker now logged.

## Workstream 2 — Code health  (+13: Types 6→9, Errors 6→9, Modularity 7→9, Maintainability 7→9, Readability 8→9, Observability 7→9) — IN PROGRESS
- [x] 3 bare `except:` → `except Exception:` + logging (database ×2, subtitle_manager)
- [x] Stray `print()` → logging (advanced_features ×2, database plugin-error); the rest are `__main__` diagnostics
- [x] Exception chaining (`raise ... from e`) in downloader; queue-worker failure now logged
- [x] Readability: dead code removed, ruff import-order/style clean across the tree
- [x] Types → 9: **core + utils mypy 73 → 0** and now a **BLOCKING** CI gate. Real robustness en route:
      `_require_conn()` guard on 30 db call sites, Popen stream narrowing in the ffmpeg/aria2 runners,
      Optional dataclass fields, schema annotations, lastrowid coalescing. (UI mixin typing still deferred.)
- [x] Extraction (safe first cut of the God-file work): pure URL helpers → `core/media_url_utils.py`
      with 36 unit tests; `download_tab` keeps thin static delegators (API preserved). Logic now
      testable in isolation and reusable.
- [ ] Larger God-file splits: `cli.py` (1766), `history_settings_tab.py` (1610), `download_tab.py` — deferred
- Note: the 93 `except Exception: pass` are mostly legitimate best-effort (animation hot-paths, UI teardown);
  worst offenders (bare excepts) already fixed. Blanket-logging them would be noise.

## Workstream 3 — Test & architecture tightening  (+4: Coverage 8→9, Test quality 7→9, Architecture 8→9) — MOSTLY DONE
- [x] Coverage floor gate landed (48%, baseline ~50%). +80 meaningful tests this pass: `media_url_utils` (36),
      `subtitle_manager` pure logic (29), `thumbnail_loader` (12), i18n parity, progressive-fetch wiring.
- [x] Architecture: confirmed production has NO `downloader._runner` leak — UI already goes through the clean
      `downloader.extract_playlist_entries_progressive` / `extract_playlist_entries` public API.
- [ ] Reduce brittle UI monkeypatching in the older tests — deferred

## Workstream 4 — Visual & UX redesign  (+8: Visual 5→9, UX 6→9, Accessibility 8→9) — STARTED
- [x] Thumbnail infrastructure (`thumbnail_loader.py`, 10 tests, in-memory+disk cache, async, ctk/tk kinds)
- [x] Real cover thumbnails in playlist preview — inline `PlaylistItemRow` + Treeview sort dialog (#0 column);
      verified end-to-end with a real network fetch (10/10 rows load covers) + screenshot
- [x] Home editorial pass (round 1): hairline borders on summary/action/recent cards — the BG_SURFACE
      (#EDE8E3) vs BG_PRIMARY (#F5F0EC) gap was ~invisible, so cards read as flat beige blocks; now defined
- [x] New reusable `ClickableCard` (accent icon + bold title + muted detail + hover + keyboard-activatable);
      replaced the flat single-button `"{title}\n{detail}"` pattern in BOTH Home quick actions and the Studio
      launcher (also removed the now-dead `_ActionCard`). Real typographic hierarchy where there was none.
- [x] Library grid now shows cover thumbnails too: `_create_result_item` rebuilt into a horizontal
      [cover | content] card, async-loaded via the shared loader (verified with a construction smoke).
      Thumbnails now consistent across playlist preview AND library.
- [ ] Editorial round 2 (spacing/scale); accessibility audit on new surfaces

## Workstream 5 — Polish: security, docs, performance  (+6: Security 8→9, Docs 8→9, Perf 8→9, i18n 9→10, Cross-platform 6→8) — IN PROGRESS
- [x] Security: closed a real command-injection in `open_file` (`os.system(f'…{path}')` → arg-list
      `subprocess.run`); audited SQL (parameterized, one f-string uses only fixed fragments — documented);
      confirmed no eval/exec/pickle/yaml/shell=True
- [x] i18n → 10: verified 0 missing keys + perfect 886/886 tr↔en parity, and locked both with regression tests
- [x] Docs: synced CLAUDE.md (685→686 tests, quality gates), PROGRESS.md (recent pass), DEPENDENCIES.md (lock)
- [x] Performance: tool-health check moved OFF the UI thread — opening/refreshing Settings previously
      froze ~1-2s (up to each tool's 5s subprocess timeout); now shows "checking…" instantly and renders
      when the background probe returns. Verified with a real-mainloop smoke.
- [x] Cross-platform: verified all `os.startfile` sites are Windows-guarded with `open`/`xdg-open`
      (arg-list subprocess) fallbacks; `winreg`/tray/DnD degrade gracefully. Documented the contract in
      ARCHITECTURE.md §3.6.
