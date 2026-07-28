"""FFmpeg runtime resolution and codec inspection helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from ravn_app.core.runners.ffmpeg import FFmpegRunner
from ravn_app.utils import bundled_tools

# Re-exported under their historical private names: these were defined here before the
# lookup was generalized in bundled_tools, and other modules/tests still import them.
from ravn_app.utils.bundled_tools import binary_name as _binary_name  # noqa: F401
from ravn_app.utils.bundled_tools import candidate_runtime_roots as _candidate_runtime_roots  # noqa: F401
from ravn_app.utils.bundled_tools import project_root as _project_root  # noqa: F401

# FFmpeg's bundled binaries live under assets/ffmpeg/<platform>/.
_FFMPEG_ASSET_SUBDIR = "ffmpeg"


def iter_bundled_ffmpeg_dirs() -> Iterable[Path]:
    """Yield candidate bundled-runtime directories in lookup order."""
    return bundled_tools.iter_bundled_dirs(_FFMPEG_ASSET_SUBDIR)


def find_bundled_tool(tool_name: str) -> Optional[str]:
    """Return bundled executable path if present."""
    return bundled_tools.find_bundled_binary(tool_name, _FFMPEG_ASSET_SUBDIR)


def resolve_tool_path(requested_path: str, tool_name: str) -> str:
    """Resolve a configured tool path, preferring explicit paths, then bundled runtime, then PATH."""
    return bundled_tools.resolve_binary_path(requested_path, tool_name, _FFMPEG_ASSET_SUBDIR)


def prepend_bundled_ffmpeg_to_path() -> Optional[str]:
    """Ensure bundled FFmpeg directory is visible via PATH for default executable names."""
    return bundled_tools.prepend_bundled_dir_to_path("ffmpeg", _FFMPEG_ASSET_SUBDIR)


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
