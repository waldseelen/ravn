"""
Metadata extraction and lightweight tag manipulation helpers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from ravn_app.core.runners.ffmpeg import FFmpegRunner


logger = logging.getLogger(__name__)

try:
    from mutagen import File as MutagenFile
except ImportError:  # pragma: no cover - optional dependency
    MutagenFile = None


class MetadataHandler:
    """Read, write, and enrich media metadata using FFprobe/FFmpeg."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> None:
        self._runner = FFmpegRunner(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)

    def extract_metadata(self, file_path: str) -> dict[str, Any]:
        """Extract normalized metadata for a media file."""
        path = Path(file_path)
        if not path.exists():
            return {}

        probe_data = self._runner.probe(str(path)) or {}
        if not probe_data:
            return {}

        format_info = probe_data.get("format", {})
        streams = probe_data.get("streams", [])
        video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
        audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
        fps = self._parse_fps(video_stream.get("r_frame_rate", "0/1"))
        tags = format_info.get("tags", {}) or {}

        return {
            "file_path": str(path),
            "title": tags.get("title") or path.stem,
            "format": path.suffix.lstrip(".").lower(),
            "container": path.suffix.lstrip(".").lower(),
            "duration": self._to_float(format_info.get("duration")),
            "size": self._to_int(format_info.get("size"), default=path.stat().st_size),
            "bitrate": self._to_int(format_info.get("bit_rate")),
            "width": self._to_int(video_stream.get("width")),
            "height": self._to_int(video_stream.get("height")),
            "fps": fps,
            "video_codec": video_stream.get("codec_name", ""),
            "audio_codec": audio_stream.get("codec_name", ""),
            "codec": audio_stream.get("codec_name") or video_stream.get("codec_name") or "",
            "sample_rate": self._to_int(audio_stream.get("sample_rate")),
            "channels": self._to_int(audio_stream.get("channels")),
            "tags": tags,
            "streams": streams,
            "probe_data": probe_data,
        }

    def read_tags(self, file_path: str) -> dict[str, Any]:
        """Read simple tags using mutagen when available."""
        if MutagenFile is None:
            return {}

        try:
            media = MutagenFile(file_path, easy=True)
        except Exception as exc:  # pragma: no cover - defensive optional path
            logger.debug("mutagen could not read tags for %s: %s", file_path, exc)
            return {}

        if not media or not getattr(media, "tags", None):
            return {}

        tags: dict[str, Any] = {}
        for key, value in media.tags.items():
            if isinstance(value, list) and len(value) == 1:
                tags[key] = value[0]
            else:
                tags[key] = value
        return tags

    def write_tags(self, file_path: str, tags: dict[str, Any]) -> bool:
        """Write tags using mutagen when possible, otherwise remux with FFmpeg metadata."""
        if not tags:
            return True

        path = Path(file_path)
        if not path.exists():
            return False

        if MutagenFile is not None and path.suffix.lower() in {".mp3", ".m4a", ".mp4", ".aac", ".flac"}:
            try:
                media = MutagenFile(str(path), easy=True)
                if media is not None:
                    for key, value in tags.items():
                        if value is None:
                            continue
                        media[key] = [str(value)]
                    media.save()
                    return True
            except Exception as exc:  # pragma: no cover - fallback path covers runtime
                logger.debug("mutagen tag write failed for %s: %s", file_path, exc)

        temp_output = path.with_name(f"{path.stem}.ravn_meta{path.suffix}")
        args = ["-i", str(path), "-map", "0", "-c", "copy"]
        for key, value in tags.items():
            if value is None:
                continue
            args.extend(["-metadata", f"{key}={value}"])
        args.extend(["-y", str(temp_output)])

        result = self._runner.run_raw(args)
        if not result.success:
            temp_output.unlink(missing_ok=True)
            return False

        path.unlink(missing_ok=True)
        temp_output.replace(path)
        return True

    def generate_thumbnail(
        self,
        input_file: str,
        output_file: str,
        timestamp: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
    ) -> bool:
        """Generate a thumbnail image from a video frame."""
        if not Path(input_file).exists():
            return False

        if timestamp is None:
            duration = self._runner.get_duration(input_file) or 0.0
            timestamp = max(duration * 0.1, 0.0)

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        args = ["-ss", str(timestamp), "-i", input_file]
        if width or height:
            args.extend(["-vf", f"scale={width or -1}:{height or -1}"])
        args.extend(["-frames:v", "1", "-y", output_file])
        return self._runner.run_raw(args).success

    def extract_cover_art(self, input_file: str, output_file: str) -> bool:
        """Extract embedded cover art or the first video stream frame."""
        if not Path(input_file).exists():
            return False

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        result = self._runner.run_raw(
            ["-i", input_file, "-map", "0:v:0", "-frames:v", "1", "-y", output_file]
        )
        return result.success

    def export_metadata(self, file_path: str, output_file: str) -> bool:
        """Write extracted metadata to a JSON file."""
        metadata = self.extract_metadata(file_path)
        if not metadata:
            return False

        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=False, default=str)
        return True

    @staticmethod
    def _parse_fps(raw_value: str) -> float:
        if not raw_value:
            return 0.0
        if "/" in raw_value:
            try:
                numerator, denominator = raw_value.split("/", 1)
                denominator_float = float(denominator)
                return float(numerator) / denominator_float if denominator_float else 0.0
            except (TypeError, ValueError):
                return 0.0
        return MetadataHandler._to_float(raw_value)

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default
