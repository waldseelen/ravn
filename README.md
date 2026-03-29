# RAVN

RAVN is a desktop media manager built with CustomTkinter. The repository contains working modules for downloading, converting, subtitle handling, packaging, update checks, and persistence, but the product is still under active integration and cleanup.

## Status

- Main entry point: `python ravn.py`
- GUI tabs exist for download, convert, subtitle, history, and settings
- Main media modules now use shared runners from `ravn_app/core/runners.py`
- Some auxiliary modules still use direct `subprocess` calls and remain candidates for consolidation
- The download tab is not fully wired yet; `_download_video()` in `ravn_app/ui/main_window.py` still contains a TODO
- Config and history still default to repo-root files: `ravn_config.json` and `ravn_history.db`
- `TASKS.md` is the canonical backlog; Phase 2 through Phase 6 are still open

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

Verified in this session on 2026-03-29:

- `pytest --collect-only -q` -> `283` collected
- `pytest -q` -> `282 passed, 1 skipped`

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
