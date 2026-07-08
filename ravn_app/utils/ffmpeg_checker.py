"""FFmpeg runtime resolution and codec inspection helpers."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ravn_app.core.runners.ffmpeg import FFmpegRunner

_PLATFORM_FFMPEG_DIR = {
    "win32": "win64",
    "cygwin": "win64",
    "darwin": "macos",
}.get(sys.platform, "linux")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _candidate_runtime_roots() -> List[Path]:
    roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    executable = getattr(sys, "executable", None)
    if executable:
        try:
            roots.append(Path(executable).resolve().parent)
        except Exception:
            pass

    roots.append(_project_root())

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)
    return unique_roots


def _binary_name(tool_name: str) -> str:
    normalized = str(tool_name or "").strip()
    if os.name == "nt" and normalized and not normalized.lower().endswith(".exe"):
        return f"{normalized}.exe"
    return normalized


def iter_bundled_ffmpeg_dirs() -> Iterable[Path]:
    """Yield candidate bundled-runtime directories in lookup order."""
    seen: set[str] = set()
    relative_dirs = (
        Path("assets") / "ffmpeg" / _PLATFORM_FFMPEG_DIR,
        Path("ffmpeg") / _PLATFORM_FFMPEG_DIR,
        Path("assets") / "ffmpeg",
        Path("ffmpeg"),
    )
    for root in _candidate_runtime_roots():
        for relative_dir in relative_dirs:
            candidate = root / relative_dir
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            yield candidate


def find_bundled_tool(tool_name: str) -> Optional[str]:
    """Return bundled executable path if present."""
    binary_name = _binary_name(tool_name)
    for directory in iter_bundled_ffmpeg_dirs():
        candidate = directory / binary_name
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def resolve_tool_path(requested_path: str, tool_name: str) -> str:
    """Resolve a configured tool path, preferring explicit paths, then bundled runtime, then PATH."""
    normalized = str(requested_path or tool_name).strip() or tool_name

    if any(sep in normalized for sep in (os.sep, "/", "\\")):
        expanded = Path(normalized).expanduser()
        if expanded.exists():
            return str(expanded)
        return normalized

    if normalized not in {tool_name, _binary_name(tool_name)}:
        discovered = shutil.which(normalized)
        return discovered or normalized

    bundled = find_bundled_tool(tool_name)
    if bundled:
        return bundled

    discovered = shutil.which(normalized)
    return discovered or normalized


def prepend_bundled_ffmpeg_to_path() -> Optional[str]:
    """Ensure bundled FFmpeg directory is visible via PATH for default executable names."""
    bundled_ffmpeg = find_bundled_tool("ffmpeg")
    if not bundled_ffmpeg:
        return None

    bundled_dir = str(Path(bundled_ffmpeg).parent)
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if bundled_dir not in path_parts:
        os.environ["PATH"] = bundled_dir if not current_path else bundled_dir + os.pathsep + current_path
    return bundled_dir


def configure_ffmpeg_runtime(
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
) -> Tuple[str, str]:
    """Resolve effective FFmpeg/FFprobe paths and expose bundled runtime via PATH when available."""
    prepend_bundled_ffmpeg_to_path()
    return (
        resolve_tool_path(ffmpeg_path, "ffmpeg"),
        resolve_tool_path(ffprobe_path, "ffprobe"),
    )


class FFmpegCodecChecker:
    """Inspect available codecs using the resolved FFmpeg runtime."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.codecs_cache: Optional[List[str]] = None
        self.encoders_cache: Optional[List[str]] = None
        resolved_ffmpeg, resolved_ffprobe = configure_ffmpeg_runtime(ffmpeg_path, ffprobe_path)
        self.runner = FFmpegRunner(ffmpeg_path=resolved_ffmpeg, ffprobe_path=resolved_ffprobe)

    def get_supported_codecs(self) -> List[str]:
        """Return supported codec names."""
        if self.codecs_cache is not None:
            return self.codecs_cache

        data = self.runner.run_ffprobe_json(["-codecs", "-of", "json"], timeout=30)
        if data:
            self.codecs_cache = [codec.get("name") for codec in data.get("codecs", []) if codec.get("name")]
            return self.codecs_cache
        return []

    def is_codec_supported(self, codec_name: str) -> bool:
        return codec_name in self.get_supported_codecs()

    def check_video_codecs(self) -> Dict[str, bool]:
        video_codecs = {
            "h264": "libx264",
            "h265": "libx265",
            "vp8": "libvpx",
            "vp9": "libvpx-vp9",
            "av1": "libaom-av1",
        }
        return {name: self.is_codec_supported(codec) for name, codec in video_codecs.items()}

    def check_audio_codecs(self) -> Dict[str, bool]:
        audio_codecs = {
            "aac": "aac",
            "mp3": "libmp3lame",
            "opus": "libopus",
            "vorbis": "libvorbis",
            "flac": "flac",
        }
        return {name: self.is_codec_supported(codec) for name, codec in audio_codecs.items()}

    def get_ffmpeg_info(self) -> Dict:
        version_line = self.runner.get_version()
        if version_line:
            return {
                "version": version_line,
                "available": True,
                "video_codecs": self.check_video_codecs(),
                "audio_codecs": self.check_audio_codecs(),
            }
        return {"available": False}


if __name__ == "__main__":
    checker = FFmpegCodecChecker()
    info = checker.get_ffmpeg_info()
    print("FFmpeg Bilgisi:")
    print(json.dumps(info, indent=2, ensure_ascii=False))
