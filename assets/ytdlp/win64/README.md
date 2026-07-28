# Bundled Windows yt-dlp Runtime

Place the Windows release binary used by packaged RAVN builds in this folder:

- `yt-dlp.exe`

## Expected layout

```text
assets/
  ytdlp/
    win64/
      yt-dlp.exe
      README.md
```

## How packaged builds consume this folder

- `build.ps1 -Action bundle-tools` (or `ci-package`/`package` with `-DownloadBundledFFmpeg`)
  downloads the latest `yt-dlp.exe` release asset here.
- `ravn.spec` bundles the entire top-level `assets/` tree into the PyInstaller output.
- `ravn_app/utils/bundled_tools.py` resolves `assets/ytdlp/<platform>/` before falling back to `PATH`.
- `ravn_app/core/runners/ytdlp.py` (`get_ytdlp_runner`) prefers this binary so a freshly
  unzipped build can download immediately, with no first-run network fetch.

## Relationship to self-update

`YtDlpRunner.update()` downloads a newer yt-dlp into the per-user data directory
(`%LOCALAPPDATA%\ravn\bin` on Windows). That self-updated copy **outranks** this bundled
one — shipping a binary is what makes a fresh install work offline, but once the user has
updated, the newer binary should win.

Resolution order: explicitly configured path → self-updated binary → this bundled copy → `PATH`.

## Notes

The binaries themselves are gitignored (`*.exe`); only this README is tracked, so the
directory exists in a clean checkout.
