# Bundled Windows FFmpeg Runtime

Place the Windows release binaries used by packaged RAVN builds in this folder:

- `ffmpeg.exe`
- `ffprobe.exe`

## Expected layout

```text
assets/
  ffmpeg/
    win64/
      ffmpeg.exe
      ffprobe.exe
      README.md
```

## How packaged builds consume this folder

- `ravn.spec` bundles the entire top-level `assets/` tree into the PyInstaller output.
- `ravn_app/utils/ffmpeg_checker.py` looks for `assets/ffmpeg/win64/` in packaged/runtime locations before falling back to `PATH`.
- `ravn.py` and `ravn_app/cli.py` call `configure_ffmpeg_runtime()` so bundled FFmpeg/FFprobe become discoverable automatically.
- `build.ps1` requires this folder to contain both binaries unless `-FFmpegArchive` or `-DownloadBundledFFmpeg` is used.

## Recommended source

Use a trusted Windows x64 FFmpeg build that contains both executables and replace the files in this directory before creating a release package.
