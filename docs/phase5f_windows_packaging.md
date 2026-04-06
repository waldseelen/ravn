# Phase 5F — Windows Packaging / Release Pipeline

## Scope

Phase 5F is Windows-only.

The canonical packaging pipeline is now:

1. populate `assets/ffmpeg/win64/` with `ffmpeg.exe` + `ffprobe.exe`
2. run `build.ps1 -Action package`
3. distribute `dist/RAVN-windows-x64.zip`
4. use the tag-driven GitHub workflow for public release publishing

## Bundled runtime strategy

RAVN now treats bundled FFmpeg as the preferred runtime for packaged Windows builds.

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
- If a user explicitly configures a custom executable path, that explicit path still wins.

## Local Windows packaging

### Prerequisites

- Windows host
- Python available as `python`
- PyInstaller installable from pip
- FFmpeg runtime available either:
  - already placed in `assets/ffmpeg/win64/`
  - or provided through `-FFmpegArchive`
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

Build package with verification:

```powershell
./build.ps1 -Action package
```

CI-style package build with runtime download:

```powershell
./build.ps1 -Action ci-package -DownloadBundledFFmpeg
```

Outputs:

- `dist/RAVN/`
- `dist/RAVN-windows-x64.zip`
- `dist/RAVN-windows-x64.sha256.txt`

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
- uploads zip + checksum to the GitHub Release

## Clean-machine validation checklist

Use a clean Windows VM or disposable test machine and verify:

1. application launches from packaged folder without a Python installation
2. config/data directories are created
3. bundled FFmpeg/FFprobe are detected without PATH edits
4. a basic URL download succeeds
5. a conversion succeeds
6. queue entries appear and finish cleanly
7. history entries are persisted
8. media library auto-add basics work for a supported output

Record results in this document or a release-specific validation note before public distribution.

## Minimum viable signing strategy

RAVN does not require signing to build artifacts, but signed public releases are the target.

Recommended minimum path:

1. store a code-signing certificate in GitHub Actions secrets as base64 (`WINDOWS_SIGNING_CERT_BASE64`)
2. store the certificate password in `WINDOWS_SIGNING_CERT_PASSWORD`
3. import the cert during the release workflow on `windows-latest`
4. sign `dist/RAVN/RAVN.exe` and optionally the generated zip/installer
5. timestamp the signature with a trusted timestamp server

If signing secrets are not present, the release workflow can still publish unsigned artifacts, but public release notes should make that explicit.
