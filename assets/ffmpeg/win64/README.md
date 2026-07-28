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
- `ravn_app/utils/bundled_tools.py` looks for `assets/ffmpeg/<platform>/` in packaged/runtime locations before falling back to `PATH`. `ravn_app/utils/ffmpeg_checker.py` layers the FFmpeg-specific parts on top of it, and the same lookup serves `assets/aria2/` and `assets/ytdlp/`.
- `ravn.py` and `ravn_app/cli.py` call `configure_bundled_tools_path()` and `configure_ffmpeg_runtime()` so bundled FFmpeg/FFprobe become discoverable automatically — including to child processes, since yt-dlp shells out to ffmpeg for muxing.
- `build.ps1` requires this folder to contain both binaries unless `-FFmpegArchive` or `-DownloadBundledFFmpeg` is used.

## Recommended source

Use a trusted Windows x64 FFmpeg build that contains both executables and replace the files in this directory before creating a release package.
