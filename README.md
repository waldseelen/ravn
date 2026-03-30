# RAVN

RAVN is a desktop media manager built with CustomTkinter. Core download, convert, and subtitle flows are complete. UI is modularized and production-ready for Phase 5 (build/packaging work).

## Status

- Main entry point: `python ravn.py`
- GUI tabs: download (single/batch), convert, subtitle, history, settings, queue monitoring
- Main media modules use shared runners from `ravn_app/core/runners.py`
- Download tab logic fully wired in `ravn_app/ui/tabs/download_tab.py` with background execution and async UI callbacks
- Reusable UI components extracted under `ravn_app/ui/components/` (error_panel, playlist_item, url_input)
- Main window is thin orchestration shell for tab composition and window lifecycle
- Config and history: OS-aware directories (Windows: `%APPDATA%\ravn\`, Linux: `~/.config/ravn/`)
- Phases 1–4D complete; Phase 5 (build/packaging/distribution) open in `TASKS.md`

## Requirements

- Python 3.9+
- FFmpeg and FFprobe on `PATH`
- Python packages from `requirements.txt`

```bash
pip install -r requirements.txt
```

## Running

```bash
python ravn.py
```

Alternative:

```bash
python -m ravn_app.ui.main_window
```

## Tests

Verified on 2026-03-30:

- Last baseline: `pytest -q` → `417 passed, 1 skipped` (`418` collected)
- UI modularization regression: `27 passed` (test_ui_logic.py), `37 passed` (test_ui_components.py + test_app_builder.py)

Useful commands:

```bash
pytest
pytest -q --tb=no
pytest --collect-only -q
pytest tests/test_converter.py -v
```

## Build

```powershell
./build.ps1 check
./build.ps1 test
./build.ps1 run
```

PyInstaller-related files already exist in `ravn.spec` and `ravn_app/core/app_builder.py`.

## Repository Layout

```text
ravn_app/
  core/    media logic, persistence, plugins, update flow, packaging
  ui/      CustomTkinter application and tabs
  utils/   FFmpeg, file, and system helpers
tests/     unit and integration-style tests
```

## Documentation

- `AGENT.md` - repo instructions for coding agents
- `CLAUDE.md` - Claude-oriented working context
- `ARCHITECTURE.md` - system structure and current design constraints
- `PROGRESS.md` - validated status snapshot
- `TASKS.md` - active backlog by phase
- `CHANGELOG.md` - repository-level change log

## Current Priorities

1. Wire the download UI to the actual downloader flow.
2. Move config and history storage out of the repo root.
3. Extend shared runner usage into remaining auxiliary modules.
4. Execute the open Phase 2 work in `TASKS.md`.
