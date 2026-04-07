# Windows Packaging and Release Guide

## Scope

RAVN's packaged release target is currently **Windows x64**.

The standard packaging flow is:

1. populate `assets/ffmpeg/win64/` with `ffmpeg.exe` and `ffprobe.exe`
2. run `build.ps1 -Action package`
3. distribute `dist/RAVN-windows-x64.zip`
4. publish via the tag-driven GitHub release workflow

## Bundled runtime strategy

Packaged Windows builds prefer a bundled FFmpeg runtime.

Expected layout:

```text
assets/
  ffmpeg/
    win64/
      ffmpeg.exe
      ffprobe.exe
```

How it works:

- `ravn.spec` bundles the top-level `assets/` tree and translations into the PyInstaller output.
- `ravn_app/utils/ffmpeg_checker.py` looks for bundled FFmpeg/FFprobe before falling back to system `PATH`.
- `ravn.py` and `ravn_app/cli.py` call `configure_ffmpeg_runtime()` so the bundled directory is prepended to `PATH` automatically.
- Explicit user-configured tool paths still take priority.

## Local Windows packaging

### Prerequisites

- Windows host
- Python available as `python`
- PyInstaller installable from pip
- FFmpeg runtime available either:
  - already placed in `assets/ffmpeg/win64/`
  - provided through `-FFmpegArchive`
  - or downloaded via `-DownloadBundledFFmpeg`

### Commands

Check environment and bundled-runtime readiness:

```powershell
./build.ps1 -Action check
```

Populate bundled FFmpeg from a local archive:

```powershell
./build.ps1 -Action bundle-ffmpeg -FFmpegArchive C:\temp\ffmpeg-release-essentials.zip
```

Build a local package:

```powershell
./build.ps1 -Action package
```

Run a CI-style package build with automatic runtime download:

```powershell
./build.ps1 -Action ci-package -DownloadBundledFFmpeg
```

Expected outputs:

- `dist/RAVN/`
- `dist/RAVN-windows-x64.zip`
- `dist/RAVN-windows-x64.sha256.txt`

## Smoke validation helper

A Windows validation helper is available at:

- `tools/windows_package_smoke.ps1`

Typical usage after building and copying the package to a clean Windows machine:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows_package_smoke.ps1 -PackageRoot .\dist\RAVN
```

What it checks automatically:

- packaged `RAVN.exe` exists
- bundled `ffmpeg.exe` / `ffprobe.exe` exist in the packaged asset tree
- translation files exist
- the packaged app can launch
- config/data/cache/log directories are created
- a smoke report is written to `windows-package-smoke-report.json`

What still needs manual confirmation:

- complete one URL download
- complete one conversion
- verify queue/history persistence
- verify media-library auto-add basics

## GitHub Actions

### CI artifact build

Workflow:

- `.github/workflows/windows-package.yml`

Behavior:

- runs on `windows-latest`
- downloads bundled FFmpeg during the build
- runs packaging via `build.ps1`
- uploads both the unpacked folder and distributable zip artifact

### Tagged release publishing

Workflow:

- `.github/workflows/windows-release.yml`

Behavior:

- triggers on tags matching `v*`
- builds the Windows package
- uploads the zip and checksum to the GitHub Release
- treats hyphenated version tags such as `v1.1.0-rc1` as prereleases

## Manual release checklist

Use a clean Windows VM or disposable test machine and verify:

1. run `tools/windows_package_smoke.ps1` against the packaged folder
2. application launches without a Python installation
3. config/data directories are created
4. bundled FFmpeg/FFprobe are detected without PATH edits
5. a basic URL download succeeds
6. a conversion succeeds
7. queue entries appear and finish cleanly
8. history entries are persisted
9. media-library auto-add basics work for a supported output

A build should not be presented as fully release-ready until this manual pass is complete.

## Code-signing guidance

RAVN can build unsigned artifacts, but signed public releases are the preferred path.

Recommended minimum setup:

1. store a code-signing certificate in GitHub Actions secrets as base64 (`WINDOWS_SIGNING_CERT_BASE64`)
2. store the certificate password in `WINDOWS_SIGNING_CERT_PASSWORD`
3. import the certificate during the release workflow on `windows-latest`
4. sign `dist/RAVN/RAVN.exe` and optionally the generated zip/installer
5. timestamp the signature with a trusted timestamp server

If signing secrets are not present, the workflow can still publish unsigned artifacts, but release notes should make that explicit.
