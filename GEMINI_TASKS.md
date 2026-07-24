# RAVN — Task List for Gemini (Antigravity)

## 0. Read this whole section before doing anything

You are working on **RAVN**, a Windows-first Python desktop + CLI media app (repo:
`C:\Users\bugra\DEV\ravn`, GitHub: `waldseelen/ravn`). Another agent (Claude Code) is also
working in this same repository, in parallel, on a different part of the plan. To avoid
conflicts:

- **Only touch the files listed in each task below.** Do not refactor, reformat, or "improve"
  anything outside a task's listed files.
- **Do not run `git commit`, `git push`, or any destructive git command** (`reset --hard`,
  `checkout --`, `clean -f`). Just leave your changes as uncommitted edits. The human will
  review and commit.
- **Do not touch these files/paths — another agent owns them right now:**
  `ravn_app/core/runners/ytdlp.py`, `tests/test_runners.py`,
  `ravn_app/ui/tabs/_download_playlist.py`, `ARCHITECTURE.md`, `PROGRESS.md`.
- Work through the tasks **in order** (TIER 1 first, then TIER 2). Do not skip ahead.
- After **every single task**, run this exact verification block and paste the output in your
  summary. Do not mark a task done if any of these fail:
  ```
  python -m pytest -q
  python -m ruff check ravn_app tests
  python -m mypy ravn_app/core ravn_app/utils
  ```
  All three must be clean (`ruff`: "All checks passed!", `mypy`: "Success: no issues found",
  `pytest`: all passed, same skip count as before you started — currently `756 passed, 1
  skipped`).
- This project has a strict rule: **any new user-facing UI text must be added as a translation
  key in BOTH `ravn_app/translations/en.json` AND `ravn_app/translations/tr.json`.** Never
  hardcode an English or Turkish string directly in UI code. Look at how existing keys are
  named (dot-separated, e.g. `settings.crashReportingEnabled`) and follow the same style.
- If a task says "add a test", put it in a new or existing file under `tests/`, following the
  style of the existing test file you're told to look at (same imports, same mocking patterns,
  same assertion style). Do not invent a new testing style.

## 1. Already done — do NOT redo these

The following work is **already complete and verified** (by both agents, independently). If you
see these files, leave them alone unless a task below explicitly tells you to edit them:

- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` — governance docs, done.
- `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/feature_request.md`,
  `.github/PULL_REQUEST_TEMPLATE.md`, `CODEOWNERS` — done.
- `.github/dependabot.yml` — pip + github-actions dependency updates, done.
- `.github/workflows/security.yml` — `pip-audit` dependency-vulnerability scan + CycloneDX SBOM
  generation (runs in CI on every push), done.
- `CHANGELOG.md` — Keep a Changelog format, done.
- Playlist fetch performance fix (parallel detail resolution, instant size estimates) — done by
  the other agent, do not touch `ytdlp.py` / `test_runners.py`.
- `ravn.spec` already bundles `vcruntime140.dll`/`msvcp140.dll`, already has a PyInstaller
  `Splash` screen wired to `assets/ravnapp.jpeg`, already sets `version='version_info.txt'`,
  already excludes `pytest`/`unittest`/`pdb`, already collects `aria2p` submodules in
  `hiddenimports`. **Do not add a splash screen — it already exists.** (`ravn.py` closes it via
  `pyi_splash.close()` after the main window is constructed.)
- `build.ps1` already does Authenticode code-signing with a timestamp server
  (`Set-AuthenticodeSignature ... -TimestampServer "http://timestamp.digicert.com"`, function
  `Invoke-SignTool`). Timestamping is done. Buying an EV certificate is a business decision, not
  a coding task — **do not attempt this**.

---

## TIER 1 — Remaining governance/CI gaps

### Task 1.1 — Add a CodeQL code-scanning workflow

**Why:** `security.yml` already scans *dependencies* for known CVEs (`pip-audit`). CodeQL is
different: it statically scans RAVN's **own source code** for security bug patterns (e.g. SQL
injection, unsafe deserialization, command injection). This project already fixed a real
command-injection bug in `open_file` in the past (see `PROGRESS.md`) — CodeQL is the automated
guard against that class of bug recurring.

**File to create:** `.github/workflows/codeql.yml` (new file, does not exist yet)

**Exact content to use** (this is GitHub's standard template for a Python-only repo — use it
as-is, do not invent your own structure):

```yaml
name: "CodeQL"

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]
  schedule:
    - cron: '30 1 * * 1'

jobs:
  analyze:
    name: Analyze
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write

    strategy:
      fail-fast: false
      matrix:
        language: ['python']

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}

      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
```

**Acceptance criteria:**
- File exists at `.github/workflows/codeql.yml`.
- Valid YAML — verify with: `python -c "import yaml; yaml.safe_load(open('.github/workflows/codeql.yml'))"`
  (if `pyyaml` is not installed, run `pip install pyyaml` first).
- This workflow only truly "runs" on GitHub's servers after a push — you cannot fully test it
  locally. Just confirm the YAML is syntactically valid and matches the template exactly.

---

### Task 1.2 — Attach the SBOM to actual GitHub Releases

**Why:** Right now the SBOM (Software Bill of Materials) is generated by `security.yml` on every
CI push, but it is **not attached to the actual versioned GitHub Release** that users download.
A release's SBOM should ship *with that specific release* so anyone auditing a downloaded version
of RAVN has a matching bill of materials.

**File to edit:** `.github/workflows/windows-release.yml`

**Current relevant content** (for context — find this exact block):

```yaml
      - name: Build release package
        shell: pwsh
        env:
          SIGN_CERT_BASE64: ${{ secrets.CERTIFICATE_BASE64 }}
          SIGN_CERT_PASSWORD: ${{ secrets.CERTIFICATE_PASSWORD }}
        run: |
          ./build.ps1 -Action ci-package -DownloadBundledFFmpeg

      - name: Publish GitHub release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/RAVN-windows-x64.zip
            dist/RAVN-windows-x64.sha256.txt
          generate_release_notes: true
          draft: false
          prerelease: ${{ contains(github.ref_name, '-') }}
```

**What to do:**
1. Insert a new step **between** `Build release package` and `Publish GitHub release` that:
   - Installs the SBOM tool: `pip install cyclonedx-bom`
   - Generates the SBOM from `requirements.txt` into the `dist/` folder, named to match the
     existing artifact naming convention: `dist/RAVN-windows-x64.sbom.json`
   - Example step (adapt the exact CLI invocation if `cyclonedx-py` needs different flags — check
     `cyclonedx-py --help` and `cyclonedx-py requirements --help` if the flags below don't work
     exactly as shown, since CLI flags can change between `cyclonedx-bom` versions):
     ```yaml
     - name: Generate SBOM
       shell: pwsh
       run: |
         pip install cyclonedx-bom
         cyclonedx-py requirements -o dist/RAVN-windows-x64.sbom.json
     ```
2. Add `dist/RAVN-windows-x64.sbom.json` to the `files:` list in the `Publish GitHub release`
   step, alongside the existing zip and sha256 files.

**Constraints:**
- Do NOT remove or modify the existing `SIGN_CERT_BASE64`/`SIGN_CERT_PASSWORD` signing logic.
- Do NOT change `build.ps1`.
- Do NOT modify `security.yml` (the CI-side SBOM check stays as-is — this task is additive, for
  the release pipeline specifically).

**Acceptance criteria:**
- `windows-release.yml` is still valid YAML (check with the same `python -c "import yaml..."`
  trick as Task 1.1).
- The new step appears before the release-publish step, and the SBOM file is in the `files:`
  list.
- This is a `windows-latest` runner workflow (uses PowerShell/`build.ps1`) — you cannot fully
  execute it locally on a non-Windows-runner CI. Just confirm YAML validity and that the logic
  reads correctly; note in your summary that it needs a real tag push to fully verify.

---

### Task 1.3 — Fix the coverage floor safety margin

**Why:** The pytest coverage floor in CI is currently set to exactly `50` (in
`.github/workflows/tests.yml`), but the actual measured coverage is `50.05%` — essentially zero
buffer. Coverage percentage can shift by a few tenths of a point across the 3 Python versions in
the CI matrix (3.11, 3.12, 3.13) due to version-conditional code paths, which could make CI
randomly fail with **no real regression**. We need a small safety buffer.

**Files to edit (all three, keep them consistent with each other):**
1. `.github/workflows/tests.yml` — find the line:
   `run: pytest -q --cov=ravn_app --cov-report=term-missing --cov-fail-under=50`
   Change `--cov-fail-under=50` to `--cov-fail-under=49`.
2. `CONTRIBUTING.md` — find the line mentioning
   `` `--cov-fail-under=50` `` and change it to `` `--cov-fail-under=49` ``.
3. `.github/PULL_REQUEST_TEMPLATE.md` — find the checklist line mentioning
   `` `--cov-fail-under=50` `` and change it to `` `--cov-fail-under=49` ``.

**How to find all occurrences precisely:** run
`grep -rn "cov-fail-under" .github CONTRIBUTING.md` (or on Windows,
`Select-String -Path .github\workflows\*.yml,CONTRIBUTING.md,.github\PULL_REQUEST_TEMPLATE.md -Pattern "cov-fail-under"`)
and change every `50` you find to `49`. Do not change any other number in these files.

**Acceptance criteria:**
- Re-running the grep/Select-String above shows `49` everywhere, no `50` left.
- `python -m pytest -q --cov=ravn_app --cov-report=term-missing --cov-fail-under=49` passes.

---

## TIER 2 — New capabilities (bigger tasks, do these after ALL of Tier 1 is done)

### Task 2.1 — Opt-in local crash reporting

**Why:** Right now, if RAVN crashes with an unhandled exception, the only trace is whatever
happened to be in the rotating log file. There's no dedicated, easy-to-find crash report a user
could attach to a bug report. This task adds **local-only** crash capture — no network calls, no
third-party SDK (like Sentry). Just: catch unhandled exceptions, write a clear crash report file,
and let the user turn this off if they don't want crash files written at all.

**Explicitly OUT of scope — do not do this:**
- Do NOT add any network upload / telemetry-sending code. This is 100% local file writing only.
- Do NOT add a third-party crash-reporting SDK/dependency (no Sentry, no Bugsnag, etc.). Use only
  Python's standard library (`sys`, `traceback`, `platform`, `datetime`, `pathlib`).

**New file:** `ravn_app/core/crash_reporter.py`

**What it must contain:**
1. A function `install_crash_handler() -> None` that sets `sys.excepthook` to a custom handler.
2. The custom handler, when an unhandled exception occurs, must:
   - First check whether crash reporting is enabled via the existing app config system: look at
     `ravn_app/core/database.py` around line 856-863 for the pattern — there is a `ConfigManager`
     (or similarly named class) with `.get(key, default)` and `.set(key, value)` methods backed by
     a JSON config file. Use `config_manager.get("crash_reporting_enabled", True)` to check
     whether it's on (default: **on**, since this never leaves the machine).
   - If disabled, just call the original exception hook (`sys.__excepthook__`) and return — do
     nothing else.
   - If enabled: log the full traceback through the existing logger (see
     `ravn_app/core/logging_config.py`, function `get_log_directory()` — reuse this function so
     crash reports live in a predictable place near the regular logs, e.g.
     `get_log_directory().parent / "crashes" / f"crash_{timestamp}.txt"` where `timestamp` is
     `datetime.now().strftime("%Y%m%d_%H%M%S")`).
   - The crash report file must contain, in plain text: the timestamp, the RAVN version (import
     `__version__` from `ravn_app/__init__.py`), the OS info (`platform.platform()`), and the full
     formatted traceback (`traceback.format_exception(exc_type, exc_value, exc_tb)`).
   - After writing the file, still call the original `sys.__excepthook__(exc_type, exc_value,
     exc_tb)` so the normal error behavior (console output, existing logging) still happens —
     this handler *adds* a crash file, it does not *replace* existing error handling.
3. Wrap all of the above file-writing logic in its own `try/except Exception` — a crash handler
   that itself crashes while handling a crash is a real bug, not a hypothetical.

**File to edit:** `ravn.py`
- In the `main()` function, call `install_crash_handler()` right after `setup_logging()` (so
  crashes are caught even during early startup, before the UI exists). Import it from
  `ravn_app.core.crash_reporter`.

**File to edit:** `ravn_app/ui/history_settings_tab.py` (this is the Settings tab)
- Add a checkbox/toggle bound to the `crash_reporting_enabled` config key. Before adding it, read
  through this file first to find how an existing similar boolean setting (e.g. a theme or
  notification toggle) is built and wired to the config — copy that exact pattern, don't invent a
  new one.
- Label text must be a translation key, not a hardcoded string — add
  `"settings.crashReportingEnabled"` (or a name consistent with nearby keys in that file) to
  BOTH `ravn_app/translations/en.json` and `ravn_app/translations/tr.json`. Suggested English
  text: "Save local crash reports" with a short help/description string explaining it's local-only
  (no data leaves the machine).

**New test file:** `tests/test_crash_reporter.py`
- First read `tests/test_error_handler.py` to copy its style (imports, mocking patterns,
  assertions).
- Test at minimum:
  1. `install_crash_handler()` actually replaces `sys.excepthook` with a different callable.
  2. Calling the installed handler with a sample exception (e.g. `raise ValueError("test")`
     caught and its `(type, value, traceback)` passed manually) writes a crash file, and that
     file's content includes the exception message.
  3. When `crash_reporting_enabled` is `False` (mock the config to return `False`), calling the
     handler does NOT write any crash file.
- Use `tmp_path` (pytest's built-in fixture) or mock `get_log_directory()` so tests never write
  into the real `%LOCALAPPDATA%` — look at how `tests/test_logging_config.py` handles this exact
  problem (it tests the same `get_log_directory()` function) and reuse that approach.

**Acceptance criteria:** the full verification block from Section 0 passes, plus
`python -m pytest -q tests/test_crash_reporter.py -v` shows all new tests passing.

---

### Task 2.2 — Wire up the existing (but currently unused) auto-update manager

**Important — read this first:** `ravn_app/core/update_manager.py` **already exists**, fully
implemented, with passing tests in `tests/test_update_manager.py`. It checks GitHub Releases for
newer versions and can download/verify updates. **The problem is that nothing in the app ever
uses it** — search the codebase yourself with
`grep -rn "UpdateManager(" ravn_app` and you'll see it's only referenced inside its own file. Your
job is to **wire it up**, not build a new one. Do not create a second update-checking system.

**Bug to fix first, in `ravn_app/core/update_manager.py`:**
- `UpdateManager.__init__` has `github_owner: str = "ravn-project"` as a default parameter. This
  is **wrong** — the real GitHub org/repo for this project is `waldseelen/ravn` (confirm yourself
  with `git remote -v`). Fix this default (or better: don't rely on the default at all — pass
  `github_owner="waldseelen"` and `github_repo="ravn"` explicitly at every call site you add).

**Also important — a real version-string bug you must account for:**
- `ravn_app/__init__.py` currently has `__version__ = "1.0.0"`, and `setup.py` /
  `version_info.txt` also say `1.0.0` — but the actual latest published git tag is `v1.1.0`. These
  version strings are stale. This means: if you wire up the update checker using the current
  `__version__` value as-is, a fully up-to-date v1.1.0 installation would incorrectly report
  "update available" (comparing stale "1.0.0" against the real latest release "1.1.0").
  **You do not need to fix the stale version files yourself** (that's a separate release-process
  concern outside this task) — but you MUST use `ravn_app.__version__` as the single source of
  truth for "current version" in your wiring (don't hardcode a version number anywhere), so that
  once a maintainer bumps `__version__` correctly on the next release, the update checker works
  correctly without further code changes. Just be aware of this when testing manually, and
  mention this stale-version-string discrepancy explicitly in your summary so the human knows
  about it.

**File to edit:** `ravn_app/ui/history_settings_tab.py` (Settings tab)
1. Add a "Check for Updates" button.
2. On click, construct `UpdateManager(current_version=__version__, github_owner="waldseelen",
   github_repo="ravn")` (import `__version__` from `ravn_app`) and call its
   `check_for_updates()` method.
3. Show the result using whatever notification/toast/label pattern this file already uses for
   other async operations (read the file first — do not invent a new UI pattern). Show one of:
   "You're up to date (vX.Y.Z)", or "Update available: vX.Y.Z — [link to the GitHub release
   page]".
4. Since `check_for_updates()` likely does a network call, run it the same way other
   network-touching actions in this codebase avoid freezing the UI — check
   `ravn_app/ui/tabs/_download_playlist.py`'s use of `threading.Thread(..., daemon=True).start()`
   plus `self.after(0, ...)` to bridge results back to the UI thread, and follow the same pattern
   here. (Read-only reference — do not edit that file.)
5. All button text and result strings must be i18n translation keys added to BOTH
   `ravn_app/translations/en.json` and `ravn_app/translations/tr.json`.

**Tests:** Only add new tests if you introduce new non-trivial logic beyond simple UI wiring
(e.g. a small helper function that formats the "update available" message). Do not modify the
existing tests in `tests/test_update_manager.py` unless the `github_owner` default-value fix
above requires updating a test that specifically asserted the old wrong default.

**Acceptance criteria:** the full verification block from Section 0 passes, plus manually confirm
`grep -rn "UpdateManager(" ravn_app` now shows a real call site inside `ravn_app/ui/`.

---

### Task 2.3 — Windows MSI installer (first pass — this is the biggest task)

**Why:** RAVN currently only ships as a `.zip` file (see `dist/RAVN-windows-x64.zip` in
`windows-release.yml`). A proper Windows installer (`.msi`) gives users Start Menu shortcuts, a
normal uninstall entry in "Add or Remove Programs", and is what's expected of a mature Windows
app. Use the **WiX Toolset** (free, open-source, the standard tool for this — do NOT use a paid
tool like Advanced Installer or InstallShield).

**This is additive, not a replacement.** The existing zip-based release must keep working exactly
as it does now. The MSI is a new, additional download option.

**New file:** `packaging/ravn.wxs` (create the `packaging/` directory)
- This is a WiX v4 source file (XML). It must define:
  1. A `Package` pointing at the app name "RAVN", using the version from `version_info.txt` (or
     hardcode `1.0.0` for now and note in your summary that this needs to be kept in sync with
     releases — do not spend time building a templating system for this).
  2. An install directory under `ProgramFiles64Folder` (e.g. `RAVN`).
  3. A `Directory`/`Component` structure that harvests all files from the `dist/RAVN/` folder
     (the output of the existing `build.ps1 -Action ci-package` step) into the install directory.
     WiX v4 has a `heat.exe`-equivalent harvesting approach or you can use the `Files` element
     with a wildcard glob — look up current WiX v4 documentation syntax for "harvest a folder of
     files" since this differs from WiX v3's `heat.exe` workflow.
  4. A Start Menu shortcut pointing at `RAVN.exe`.
  5. Standard uninstall support (WiX v4's `Package` element handles this by default when you
     define an `Upgrade`/`MajorUpgrade` element — include one so re-installing a newer MSI cleanly
     replaces the old one instead of erroring).
  6. An `Icon` referencing `assets/ravn.ico` if useful for the Add/Remove Programs entry.

**File to edit:** `build.ps1`
- Add a new action value (e.g. `-Action ci-msi`) alongside the existing actions (look at how
  `-Action ci-package` is currently structured/dispatched in this file, and follow the same
  pattern for consistency). This new action must:
  1. Assume `dist/RAVN/` already exists (i.e., assume `ci-package` already ran — do not
     re-invoke the packaging step yourself, just consume its output).
  2. Run `wix build packaging/ravn.wxs -out dist/RAVN-windows-x64.msi` (WiX v4's CLI is a
     `dotnet` global tool named `wix`, not the old `candle.exe`/`light.exe` from WiX v3 — do not
     write WiX v3-style build commands).
  3. Do NOT modify or remove the existing `ci-package` action or the `Invoke-SignTool` signing
     logic — this is a new, separate action.

**File to edit:** `.github/workflows/windows-release.yml`
1. Add a step to install the WiX v4 CLI before building the MSI:
   ```yaml
   - name: Install WiX Toolset
     shell: pwsh
     run: dotnet tool install --global wix
   ```
2. Add a step that runs `./build.ps1 -Action ci-msi` after the existing
   `Build release package` step.
3. Add `dist/RAVN-windows-x64.msi` to the `files:` list in the `Publish GitHub release` step
   (alongside the zip, sha256, and SBOM from Task 1.2).

**Constraints:**
- Do not touch `ravn.spec` (that produces the `dist/RAVN` folder the MSI packages — it's correct
  as-is and out of scope here).
- Do not remove the existing zip-based release artifacts.

**Acceptance criteria (this task cannot be fully verified without a real Windows GitHub Actions
runner):**
- `packaging/ravn.wxs` is well-formed XML — verify with:
  `python -c "import xml.dom.minidom; xml.dom.minidom.parse('packaging/ravn.wxs')"`
- `windows-release.yml` is still valid YAML (same check as Task 1.1/1.2).
- `build.ps1`'s new action does not break the file's PowerShell syntax — verify with:
  `powershell -NoProfile -Command "$null = [System.Management.Automation.PSParser]::Tokenize((Get-Content build.ps1 -Raw), [ref]$null)"`
  (this should produce no error output; if it errors, there's a syntax mistake in your edit).
- **Explicitly state in your summary that this task has NOT been end-to-end tested on a real
  Windows runner**, and that a maintainer needs to either push a test tag or use
  `workflow_dispatch` to fully validate the MSI actually installs/uninstalls correctly before
  relying on it for a real release. This is expected and fine — just be honest about it, don't
  claim it's fully verified when it can't be from this environment.

---

## 2. When you're done with everything

Write a short summary (in English) covering, for EACH of the 6 tasks above:
- Task number and one-line status (done / partially done / blocked, and why if not fully done).
- The exact verification commands you ran and their pass/fail result.
- Any assumption you made that the human should double-check (e.g. exact CLI flags for
  `cyclonedx-py` if they differed from what's shown above, or WiX v4 syntax specifics you had to
  look up).

Do not commit anything. Leave all changes as uncommitted working-tree edits for human review.
