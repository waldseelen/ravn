# Bundled Windows aria2 Runtime

Place the Windows release binary used by packaged RAVN builds in this folder:

- `aria2c.exe`

## Expected layout

```text
assets/
  aria2/
    win64/
      aria2c.exe
      README.md
```

## How packaged builds consume this folder

- `build.ps1 -Action bundle-tools` (or `ci-package`/`package` with `-DownloadBundledFFmpeg`)
  downloads the official aria2 Windows release and extracts `aria2c.exe` here.
- `ravn.spec` bundles the entire top-level `assets/` tree into the PyInstaller output.
- `ravn_app/utils/bundled_tools.py` resolves `assets/aria2/<platform>/` before falling back to `PATH`.
- `ravn_app/core/runners/aria2.py` prefers this binary over a system install, and
  `ravn_app/core/tool_health.py` reports it as available so Settings does not show
  aria2c as missing in a freshly unzipped build.

## Notes

`aria2c` powers torrent and magnet downloads only. It is an *optional* tool: if it is
absent the rest of RAVN still works, and the build warns rather than failing.

The binaries themselves are gitignored (`*.exe`); only this README is tracked, so the
directory exists in a clean checkout.
